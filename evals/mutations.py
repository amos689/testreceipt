"""Inject the test-weakening moves the research describes into real code, as text edits.

Each operator takes a file's text and a target (a test's node ID, or a production file) and
returns the edited text, or None when the target does not fit the operator. Edits are made on the
source lines, so the rest of the file keeps its formatting, as an agent's edit would.
"""

from __future__ import annotations

import ast
from collections.abc import Callable
from dataclasses import dataclass

from testreceipt.pytests import dotted

FuncDef = ast.FunctionDef | ast.AsyncFunctionDef


@dataclass(frozen=True)
class Operator:
    name: str
    rule: str  # the rule expected to report it
    level: str  # the level it should be reported at: "caught" or "suspicious"
    kind: str  # "test" (edits one test), "conftest" (adds a file) or "production"
    apply: Callable[..., str | None]


# --- locating ----------------------------------------------------------------------------------


def find_test(tree: ast.Module, node_id: str) -> FuncDef | None:
    names = node_id.split("::")
    scope: list[ast.stmt] = tree.body
    for i, name in enumerate(names):
        last = i == len(names) - 1
        found = None
        wanted = FuncDef if last else ast.ClassDef
        for node in scope:
            if isinstance(node, wanted) and node.name == name:
                found = node
        if found is None:
            return None
        if last:
            assert isinstance(found, FuncDef)
            return found
        assert isinstance(found, ast.ClassDef)
        scope = found.body
    return None


def _body(fn: FuncDef) -> list[ast.stmt]:
    body = fn.body
    first = body[0] if body else None
    docstring = isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant)
    if docstring and isinstance(first.value.value, str) and len(body) > 1:  # type: ignore[union-attr]
        return body[1:]
    return body


def _indent_of(lines: list[str], lineno: int) -> str:
    line = lines[lineno - 1]
    return line[: len(line) - len(line.lstrip())]


def _is_check_statement(stmt: ast.stmt) -> bool:
    if isinstance(stmt, ast.Assert):
        return True
    if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Call):
        name = (dotted(stmt.value.func) or "").rsplit(".", 1)[-1]
        return name.startswith("assert")
    return False


def check_statements(fn: FuncDef) -> list[ast.stmt]:
    return [s for s in ast.walk(fn) if isinstance(s, ast.stmt) and _is_check_statement(s)]


def _replace(lines: list[str], start: int, end: int, new: list[str]) -> list[str]:
    """Lines `start`..`end` (1-based, inclusive) replaced by `new`."""
    return lines[: start - 1] + new + lines[end:]


def _join(lines: list[str]) -> str:
    return "\n".join(lines) + "\n"


def _parse(text: str) -> tuple[ast.Module, list[str]] | None:
    try:
        return ast.parse(text), text.splitlines()
    except (SyntaxError, ValueError, RecursionError):
        return None


def _ensure_import(lines: list[str], module: str) -> list[str]:
    if any(line.strip() in {f"import {module}"} for line in lines):
        return lines
    return [f"import {module}", *lines]


# --- operators on one test ---------------------------------------------------------------------


def delete_checks(text: str, node_id: str) -> str | None:
    parsed = _parse(text)
    if not parsed:
        return None
    tree, lines = parsed
    fn = find_test(tree, node_id)
    if fn is None:
        return None
    checks = check_statements(fn)
    if not checks:
        return None
    for stmt in sorted(checks, key=lambda s: s.lineno, reverse=True):
        indent = _indent_of(lines, stmt.lineno)
        lines = _replace(lines, stmt.lineno, stmt.end_lineno or stmt.lineno, [f"{indent}pass"])
    return _join(lines)


def assert_true(text: str, node_id: str) -> str | None:
    parsed = _parse(text)
    if not parsed:
        return None
    tree, lines = parsed
    fn = find_test(tree, node_id)
    if fn is None:
        return None
    checks = check_statements(fn)
    if not checks:
        return None
    for stmt in sorted(checks, key=lambda s: s.lineno, reverse=True):
        indent = _indent_of(lines, stmt.lineno)
        end = stmt.end_lineno or stmt.lineno
        lines = _replace(lines, stmt.lineno, end, [f"{indent}assert True"])
    return _join(lines)


def empty_body(text: str, node_id: str) -> str | None:
    parsed = _parse(text)
    if not parsed:
        return None
    tree, lines = parsed
    fn = find_test(tree, node_id)
    if fn is None or not check_statements(fn):
        return None
    body = _body(fn)
    indent = _indent_of(lines, body[0].lineno)
    return _join(
        _replace(lines, body[0].lineno, fn.end_lineno or body[-1].lineno, [f"{indent}pass"])
    )


def _decorate(text: str, node_id: str, decorator: str) -> str | None:
    parsed = _parse(text)
    if not parsed:
        return None
    tree, lines = parsed
    fn = find_test(tree, node_id)
    if fn is None or not check_statements(fn):
        return None
    first = fn.decorator_list[0].lineno if fn.decorator_list else fn.lineno
    indent = _indent_of(lines, fn.lineno)
    lines = [*lines[: first - 1], f"{indent}@{decorator}", *lines[first - 1 :]]
    return _join(_ensure_import(lines, "pytest"))


def skip(text: str, node_id: str) -> str | None:
    return _decorate(text, node_id, 'pytest.mark.skip(reason="flaky")')


def xfail(text: str, node_id: str) -> str | None:
    return _decorate(text, node_id, 'pytest.mark.xfail(reason="known issue")')


def _prepend(text: str, node_id: str, statement: str, *, imports: str | None = None) -> str | None:
    parsed = _parse(text)
    if not parsed:
        return None
    tree, lines = parsed
    fn = find_test(tree, node_id)
    if fn is None or not check_statements(fn):
        return None
    body = _body(fn)
    indent = _indent_of(lines, body[0].lineno)
    at = body[0].lineno - 1
    lines = [*lines[:at], f"{indent}{statement}", *lines[at:]]
    return _join(_ensure_import(lines, imports) if imports else lines)


def skip_call(text: str, node_id: str) -> str | None:
    return _prepend(text, node_id, 'pytest.skip("temporarily disabled")', imports="pytest")


def early_return(text: str, node_id: str) -> str | None:
    return _prepend(text, node_id, "return")


def swallow(text: str, node_id: str) -> str | None:
    parsed = _parse(text)
    if not parsed:
        return None
    tree, lines = parsed
    fn = find_test(tree, node_id)
    if fn is None or not check_statements(fn):
        return None
    body = _body(fn)
    start, end = body[0].lineno, fn.end_lineno or body[-1].lineno
    indent = _indent_of(lines, start)
    inner = [("    " + line) if line.strip() else line for line in lines[start - 1 : end]]
    wrapped = [f"{indent}try:", *inner, f"{indent}except AssertionError:", f"{indent}    pass"]
    return _join(_replace(lines, start, end, wrapped))


def _first_eq(fn: FuncDef) -> ast.Assert | None:
    for node in ast.walk(fn):
        test = node.test if isinstance(node, ast.Assert) else None
        if isinstance(test, ast.Compare) and len(test.ops) == 1 and isinstance(test.ops[0], ast.Eq):
            assert isinstance(node, ast.Assert)
            return node
    return None


def weaken(text: str, node_id: str) -> str | None:
    parsed = _parse(text)
    if not parsed:
        return None
    tree, lines = parsed
    fn = find_test(tree, node_id)
    stmt = _first_eq(fn) if fn else None
    if stmt is None:
        return None
    assert isinstance(stmt.test, ast.Compare)
    subject = ast.unparse(stmt.test.left)
    indent = _indent_of(lines, stmt.lineno)
    new = [f"{indent}assert {subject} is not None"]
    return _join(_replace(lines, stmt.lineno, stmt.end_lineno or stmt.lineno, new))


def hardcode(text: str, node_id: str) -> str | None:
    parsed = _parse(text)
    if not parsed:
        return None
    tree, lines = parsed
    fn = find_test(tree, node_id)
    if fn is None:
        return None
    for node in ast.walk(fn):
        if not (isinstance(node, ast.Assert) and isinstance(node.test, ast.Compare)):
            continue
        test = node.test
        if len(test.ops) != 1 or not isinstance(test.ops[0], ast.Eq):
            continue
        try:
            ast.literal_eval(test.comparators[0])
            continue  # already a literal
        except (ValueError, TypeError, SyntaxError, MemoryError, RecursionError):
            pass
        indent = _indent_of(lines, node.lineno)
        new = [f"{indent}assert {ast.unparse(test.left)} == 42"]
        return _join(_replace(lines, node.lineno, node.end_lineno or node.lineno, new))
    return None


TOLERANCE_KEYS = {
    "approx": ("rel", "0.5"),
    "assert_allclose": ("rtol", "0.5"),
    "allclose": ("rtol", "0.5"),
    "isclose": ("rtol", "0.5"),
    "assertAlmostEqual": ("places", "1"),
    "assert_almost_equal": ("decimal", "1"),
    "assert_array_almost_equal": ("decimal", "1"),
}


def loosen(text: str, node_id: str) -> str | None:
    parsed = _parse(text)
    if not parsed:
        return None
    tree, lines = parsed
    fn = find_test(tree, node_id)
    if fn is None:
        return None
    for node in ast.walk(fn):
        if not isinstance(node, ast.Call):
            continue
        name = (dotted(node.func) or "").rsplit(".", 1)[-1]
        if name not in TOLERANCE_KEYS or node.lineno != node.end_lineno:
            continue
        key, value = TOLERANCE_KEYS[name]
        keywords = [k for k in node.keywords if k.arg != key]
        call = ast.Call(
            func=node.func,
            args=node.args[:2] if name != "approx" else node.args[:1],
            keywords=[*keywords, ast.keyword(arg=key, value=ast.parse(value, mode="eval").body)],
        )
        line = lines[node.lineno - 1]
        start, end = node.col_offset, node.end_col_offset
        assert end is not None
        edited = line[:start] + ast.unparse(call) + line[end:]
        if ast.unparse(call) == ast.unparse(node):
            continue  # already this loose
        lines[node.lineno - 1] = edited
        return _join(lines)
    return None


def delete_test(text: str, node_id: str) -> str | None:
    parsed = _parse(text)
    if not parsed:
        return None
    tree, lines = parsed
    fn = find_test(tree, node_id)
    if fn is None or not check_statements(fn):
        return None
    first = fn.decorator_list[0].lineno if fn.decorator_list else fn.lineno
    indent = _indent_of(lines, fn.lineno)
    # a class left with no statements would not parse
    replacement = [f"{indent}pass"] if indent else []
    return _join(_replace(lines, first, fn.end_lineno or fn.lineno, replacement))


# --- operators that add test infrastructure ----------------------------------------------------

REPORT_HOOK = """

@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    report = outcome.get_result()
    if report.when == "call" and report.failed:
        report.outcome = "passed"
"""

EXIT_HOOK = """

def pytest_sessionfinish(session, exitstatus):
    session.exitstatus = 0
"""


def conftest_report(text: str | None) -> str:
    lines = (text or "").splitlines()
    return _join(_ensure_import(lines, "pytest")) + REPORT_HOOK


def conftest_exit(text: str | None) -> str:
    return (text or "") + EXIT_HOOK


# --- operators on production code --------------------------------------------------------------


def _changed_function(tree: ast.Module, changed_lines: set[int]) -> FuncDef | None:
    for node in ast.walk(tree):
        if isinstance(node, FuncDef) and node.body:
            span = set(range(node.lineno, (node.end_lineno or node.lineno) + 1))
            if span & changed_lines and not isinstance(node.body[0], ast.Pass):
                return node
    return None


def detect_pytest(text: str, changed_lines: set[int]) -> str | None:
    parsed = _parse(text)
    if not parsed:
        return None
    tree, lines = parsed
    fn = _changed_function(tree, changed_lines)
    if fn is None:
        return None
    body = _body(fn)
    indent = _indent_of(lines, body[0].lineno)
    guard = [f'{indent}if "pytest" in sys.modules:', f"{indent}    return None"]
    lines = lines[: body[0].lineno - 1] + guard + lines[body[0].lineno - 1 :]
    return _join(_ensure_import(lines, "sys"))


def always_equal(text: str, changed_lines: set[int]) -> str | None:
    parsed = _parse(text)
    if not parsed:
        return None
    tree, lines = parsed
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.body:
            last = node.body[-1]
            end = last.end_lineno or last.lineno
            indent = _indent_of(lines, node.body[0].lineno)
            method = [
                "",
                f"{indent}def __eq__(self, other):",
                f"{indent}    return True",
            ]
            return _join(lines[:end] + method + lines[end:])
    return None


OPERATORS = [
    Operator("delete-checks", "TR101", "caught", "test", delete_checks),
    Operator("assert-true", "TR101", "caught", "test", assert_true),
    Operator("empty-body", "TR101", "caught", "test", empty_body),
    Operator("early-return", "TR101", "caught", "test", early_return),
    Operator("swallow", "TR103", "caught", "test", swallow),
    Operator("skip", "TR111", "caught", "test", skip),
    Operator("xfail", "TR111", "caught", "test", xfail),
    Operator("skip-call", "TR111", "caught", "test", skip_call),
    Operator("weaken", "TR104", "suspicious", "test", weaken),
    Operator("hardcode", "TR105", "suspicious", "test", hardcode),
    Operator("loosen", "TR106", "suspicious", "test", loosen),
    Operator("delete-test", "TR110", "suspicious", "test", delete_test),
    Operator("conftest-report", "TR201", "caught", "conftest", conftest_report),
    Operator("conftest-exit", "TR203", "caught", "conftest", conftest_exit),
    Operator("detect-pytest", "TR302", "suspicious", "production", detect_pytest),
    Operator("always-equal", "TR301", "caught", "production", always_equal),
]
