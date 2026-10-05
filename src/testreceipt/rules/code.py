"""Rules on Python code that makes failing tests look green.

Test infrastructure (conftest files, pytest hooks, test modules) can rewrite reports, drop
tests from collection or end the test process before failures are counted. Production code
can special-case the test run: comparisons that always succeed, branches on whether pytest
is running, reads of the test files. Each device is reported only when the change adds it.
"""

from __future__ import annotations

import ast
import re
from collections import Counter
from collections.abc import Iterator
from dataclasses import dataclass

from ..changes import FileChange, is_conftest, is_production_python, is_python, is_test_file
from ..model import Finding, Level
from ..pytests import dotted, parse

REPORT_HOOKS = frozenset(
    {"pytest_runtest_makereport", "pytest_report_teststatus", "pytest_runtest_logreport"}
)
TEST_PATH = re.compile(r"(?:^|[/\\])(?:tests?|testing)[/\\]|\btest_\w+\.py\b|\bconftest\.py\b")
TEST_SWITCH = re.compile(r"(?:^|_)(?:TEST|TESTS|TESTING|UNITTEST|PYTEST)(?:_|$)", re.IGNORECASE)
PYTEST_ENV = frozenset({"PYTEST_CURRENT_TEST", "PYTEST_VERSION", "PYTEST_XDIST_WORKER"})
TEST_RUNNERS = frozenset({"pytest", "_pytest", "unittest", "nose", "nose2"})


@dataclass(frozen=True)
class _Device:
    rule: str
    level: Level
    message: str
    key: str  # what makes two devices the same, for counting the ones the change adds
    line: int


def check_code(changes: list[FileChange]) -> list[Finding]:
    findings: list[Finding] = []
    for change in changes:
        if not is_python(change.path) or change.after is None:
            continue
        testish = is_test_file(change.path) or is_conftest(change.path)
        production = is_production_python(change.path)
        try:
            new_tree = parse(change.after)
            old_tree = parse(change.before) if change.before is not None else None
        except (SyntaxError, ValueError, RecursionError):
            continue  # test files are reported as unchecked by the test rules
        old = list(_devices(old_tree, testish, production)) if old_tree else []
        seen = Counter(d.key for d in old)
        for device in _devices(new_tree, testish, production):
            if seen[device.key] > 0:
                seen[device.key] -= 1
                continue
            findings.append(
                Finding(device.rule, device.level, change.path, device.line, device.message)
            )
    return findings


def _devices(tree: ast.Module, testish: bool, production: bool) -> Iterator[_Device]:
    yield from _hooks(tree)
    yield from _exits(tree, testish, production)
    if production:
        yield from _production(tree)


# --- test infrastructure -----------------------------------------------------------------------


def _functions(tree: ast.AST) -> Iterator[ast.FunctionDef | ast.AsyncFunctionDef]:
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            yield node


def _hooks(tree: ast.Module) -> Iterator[_Device]:
    for fn in _functions(tree):
        source = ast.unparse(fn)
        if fn.name in REPORT_HOOKS:
            for node in ast.walk(fn):
                targets: list[ast.expr] = []
                if isinstance(node, ast.Assign):
                    targets = node.targets
                elif isinstance(node, ast.AugAssign | ast.AnnAssign):
                    targets = [node.target]
                for target in targets:
                    if isinstance(target, ast.Attribute) and target.attr in {"outcome", "longrepr"}:
                        yield _Device(
                            "TR201",
                            Level.CAUGHT,
                            f"`{fn.name}` rewrites the test report's `{target.attr}`",
                            f"TR201:{fn.name}:{target.attr}",
                            target.lineno,
                        )
                if isinstance(node, ast.Call) and (dotted(node.func) or "").endswith(
                    "force_result"
                ):
                    yield _Device(
                        "TR201",
                        Level.CAUGHT,
                        f"`{fn.name}` replaces the hook's result",
                        f"TR201:{fn.name}:force_result",
                        node.lineno,
                    )
        elif (
            fn.name == "pytest_pyfunc_call"
            and "obj" not in source
            and "runtestprotocol" not in source
        ):
            yield _Device(
                "TR201",
                Level.CAUGHT,
                "`pytest_pyfunc_call` reports tests as run without calling them",
                "TR201:pyfunc_call",
                fn.lineno,
            )
        elif fn.name == "pytest_collection_modifyitems":
            if re.search(
                r"items\s*\[:\]\s*=|items\.(?:remove|pop|clear)\(|del items|deselected", source
            ):
                yield _Device(
                    "TR202",
                    Level.SUSPICIOUS,
                    "`pytest_collection_modifyitems` drops collected tests",
                    f"TR202:modifyitems:{source}",
                    fn.lineno,
                )
            elif "skip" in source or "xfail" in source:
                yield _Device(
                    "TR202",
                    Level.SUSPICIOUS,
                    "`pytest_collection_modifyitems` marks collected tests to skip",
                    f"TR202:modifyitems:{source}",
                    fn.lineno,
                )
        elif fn.name == "pytest_ignore_collect":
            yield _Device(
                "TR202",
                Level.SUSPICIOUS,
                "`pytest_ignore_collect` keeps files from being collected",
                f"TR202:ignore_collect:{source}",
                fn.lineno,
            )
        elif fn.name == "pytest_sessionfinish" and re.search(r"exitstatus\s*=", source):
            yield _Device(
                "TR203",
                Level.CAUGHT,
                "`pytest_sessionfinish` overwrites the exit status",
                "TR203:sessionfinish",
                fn.lineno,
            )
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                text = ast.unparse(target)
                if text.startswith(("_pytest.", "TestReport.")) or ".TestReport." in text:
                    yield _Device(
                        "TR201",
                        Level.CAUGHT,
                        f"pytest's internals are patched: `{text}`",
                        f"TR201:patch:{text}",
                        node.lineno,
                    )
                elif isinstance(target, ast.Name) and target.id in {
                    "collect_ignore",
                    "collect_ignore_glob",
                }:
                    entries = node.value.elts if isinstance(node.value, ast.List) else []
                    for entry in entries:
                        yield _Device(
                            "TR202",
                            Level.SUSPICIOUS,
                            f"`{target.id}` now leaves out {ast.unparse(entry)}",
                            f"TR202:{target.id}:{ast.unparse(entry)}",
                            node.lineno,
                        )


def _lines_of(node: ast.AST) -> set[int]:
    return {inner.lineno for inner in ast.walk(node) if hasattr(inner, "lineno")}


def _expected_exits(tree: ast.Module) -> set[int]:
    """Lines where exiting is expected: `if __name__ == "__main__":` and `raises(SystemExit)`."""
    lines: set[int] = set()
    for node in tree.body:
        if isinstance(node, ast.If) and "__main__" in ast.unparse(node.test):
            lines |= _lines_of(node)
    for inner in ast.walk(tree):
        if isinstance(inner, ast.With | ast.AsyncWith):
            for item in inner.items:
                if "SystemExit" in ast.unparse(item.context_expr):
                    lines |= _lines_of(inner)
    return lines


def _exits(tree: ast.Module, testish: bool, production: bool) -> Iterator[_Device]:
    expected = _expected_exits(tree)
    # in test code, exiting with a failure status is a way to test an exit; exiting with success,
    # at import time or from a hook is a way to end the run before failures are counted
    early = {node.lineno for node in tree.body if isinstance(node, ast.Expr)}
    for fn in _functions(tree):
        if fn.name.startswith("pytest_"):
            early |= _lines_of(fn)
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or node.lineno in expected:
            continue
        name = dotted(node.func) or ""
        zero = not node.args or (
            isinstance(node.args[0], ast.Constant) and node.args[0].value in {0, None}
        )
        if name == "os._exit":
            if testish:
                yield _Device(
                    "TR203",
                    Level.CAUGHT,
                    "`os._exit` ends the test process before pytest reports failures",
                    "TR203:os._exit",
                    node.lineno,
                )
            elif production and zero:
                yield _Device(
                    "TR203",
                    Level.SUSPICIOUS,
                    "`os._exit(0)` ends the process with success, whatever the tests found",
                    "TR203:os._exit",
                    node.lineno,
                )
        elif testish and name in {"sys.exit", "exit", "quit"} and (zero or node.lineno in early):
            yield _Device(
                "TR203",
                Level.CAUGHT,
                f"`{name}` in test code ends the run early",
                f"TR203:{name}",
                node.lineno,
            )
        elif name == "pytest.exit":
            code = next((k.value for k in node.keywords if k.arg == "returncode"), None)
            if isinstance(code, ast.Constant) and code.value == 0:
                yield _Device(
                    "TR203",
                    Level.CAUGHT,
                    "`pytest.exit(returncode=0)` ends the run with success",
                    "TR203:pytest.exit",
                    node.lineno,
                )


# --- production code ---------------------------------------------------------------------------


def _always(fn: ast.FunctionDef | ast.AsyncFunctionDef, value: bool) -> bool:
    body = fn.body
    if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant):
        body = body[1:]
    return (
        len(body) == 1
        and isinstance(body[0], ast.Return)
        and isinstance(body[0].value, ast.Constant)
        and body[0].value.value is value
    )


def _docstrings(tree: ast.Module) -> set[int]:
    """ids of the string constants that are docstrings or other bare string statements."""
    return {
        id(node.value)
        for node in ast.walk(tree)
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant)
    }


def _production(tree: ast.Module) -> Iterator[_Device]:
    docstrings = _docstrings(tree)
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            for item in node.body:
                fixed = None
                if isinstance(item, ast.FunctionDef | ast.AsyncFunctionDef):
                    if item.name == "__eq__" and _always(item, True):
                        fixed = "`__eq__` always returns True"
                    elif item.name == "__ne__" and _always(item, False):
                        fixed = "`__ne__` always returns False"
                elif isinstance(item, ast.Assign) and any(
                    isinstance(t, ast.Name) and t.id == "__eq__" for t in item.targets
                ):
                    body = item.value.body if isinstance(item.value, ast.Lambda) else None
                    if isinstance(body, ast.Constant) and body.value is True:
                        fixed = "`__eq__` always returns True"
                if fixed:
                    yield _Device(
                        "TR301",
                        Level.CAUGHT,
                        f"class `{node.name}`: {fixed}, so any equality assertion passes",
                        f"TR301:{node.name}",
                        item.lineno,
                    )
        elif isinstance(node, ast.Constant) and isinstance(node.value, str):
            if id(node) in docstrings:
                continue
            if node.value in PYTEST_ENV:
                yield _Device(
                    "TR302",
                    Level.CAUGHT,
                    f"production code reads `{node.value}` to tell when tests are running",
                    f"TR302:{node.value}",
                    node.lineno,
                )
            elif TEST_PATH.search(node.value):
                yield _Device(
                    "TR303",
                    Level.SUSPICIOUS,
                    f"production code refers to test files: {node.value!r}",
                    f"TR303:{node.value}",
                    node.lineno,
                )
        elif isinstance(node, ast.Compare) and len(node.ops) == 1:
            left, right = node.left, node.comparators[0]
            if (
                isinstance(left, ast.Constant)
                and left.value in TEST_RUNNERS
                and isinstance(node.ops[0], ast.In | ast.NotIn)
                and re.search(r"sys\.(?:modules|argv)", ast.unparse(right))
            ):
                yield _Device(
                    "TR302",
                    Level.CAUGHT,
                    f"production code checks whether {left.value} is running",
                    f"TR302:{left.value}",
                    node.lineno,
                )
        elif isinstance(node, ast.Call) and dotted(node.func) == "sys.modules.get":
            first = node.args[0] if node.args else None
            if isinstance(first, ast.Constant) and first.value in TEST_RUNNERS:
                yield _Device(
                    "TR302",
                    Level.CAUGHT,
                    f"production code checks whether {first.value} is loaded",
                    f"TR302:{first.value}",
                    node.lineno,
                )
        elif isinstance(node, ast.If | ast.IfExp):
            for name in _switches(node.test):
                yield _Device(
                    "TR304",
                    Level.SUSPICIOUS,
                    f"production code branches on `{name}`",
                    f"TR304:{name}",
                    node.lineno,
                )


def _switches(test: ast.expr) -> Iterator[str]:
    """Names of environment variables or settings that read like a test mode, used in a test."""
    for node in ast.walk(test):
        name: str | None = None
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            name = node.value
        elif isinstance(node, ast.Attribute):
            name = node.attr
        # upper case: environment variables and settings, not ordinary attributes like `self.test`
        if not name or not name.isidentifier() or not name.isupper() or name in PYTEST_ENV:
            continue
        if TEST_SWITCH.search(name):
            yield name
