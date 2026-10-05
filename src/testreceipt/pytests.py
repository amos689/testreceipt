"""The tests in a Python test module, and what each one checks.

Tests are found the way pytest finds them by default: functions named `test*` at module level, and
methods named `test*` in classes named `Test*` or derived from a `TestCase`. Functions whose names
read like assertion helpers (`assert_valid`, `check_output`) are kept too, so that a check moved
into a helper is not taken for a check removed.
"""

from __future__ import annotations

import ast
import io
import re
import tokenize
import warnings
from collections.abc import Iterable, Iterator
from dataclasses import dataclass, field

FuncDef = ast.FunctionDef | ast.AsyncFunctionDef

# Names of calls that check something on the test's behalf: `self.check_output(...)`, `verify(...)`.
HELPER_NAME = re.compile(r"assert|check|verify|expect|validate|ensure|compare", re.IGNORECASE)

RAISES = frozenset({"pytest.raises", "raises", "pytest.warns", "warns", "pytest.deprecated_call"})
UNITTEST_RAISES = frozenset(
    {"assertRaises", "assertRaisesRegex", "assertRaisesRegexp", "assertWarns", "assertWarnsRegex"}
)
# Mocks a test sets up, by the dotted name of the call or decorator.
PATCH_CALLS = frozenset(
    {
        "monkeypatch.setattr",
        "monkeypatch.setitem",
        "monkeypatch.delattr",
        "monkeypatch.setenv",
        "monkeypatch.syspath_prepend",
    }
)


@dataclass(frozen=True)
class Check:
    kind: str  # "assert", "call", "raises" or "fail"
    text: str  # the check's source, normalised by ast.unparse
    line: int
    trivial: bool  # always passes: `assert True`, `self.assertTrue(1)`, `assert x == x`
    node: ast.AST = field(compare=False, repr=False)


@dataclass(frozen=True)
class Tolerance:
    func: str  # "approx", "assert_allclose", "assertAlmostEqual", ...
    key: str  # "rel", "abs", "rtol", "atol", "places", "decimal", "delta", "eps", ...
    value: float
    larger_is_looser: bool
    line: int


@dataclass
class TestCase:
    id: str  # pytest's node ID inside the module: "TestParser::test_empty"
    name: str
    line: int
    helper: bool  # an assertion helper rather than a test
    checks: list[Check]  # reachable checks: those after an unconditional `return` are left out
    skips: frozenset[str]  # "skip" and "xfail" (unconditional); "skipif" and "xfail-if"
    params: dict[str, int]  # parametrize argnames -> number of literal cases
    tolerances: list[Tolerance]
    patches: int  # mocks the test sets up
    calls_helper: bool  # calls something named like a check (`check_output`, `self.verify`)
    empty: bool  # nothing beyond a docstring, `pass` or `...`
    swallowed: int  # checks inside try/except blocks that swallow their failure
    returns_early: bool  # an unconditional `return` cuts the body short
    body: str  # the body's source, for recognising a moved or renamed test
    end_line: int = 0
    comments: frozenset[str] = frozenset()  # the comments inside the function
    skip_reasons: tuple[str, ...] = ()  # what the skip markers and calls say
    called: frozenset[str] = frozenset()  # names of the functions and methods the body calls

    @property
    def live_checks(self) -> list[Check]:
        return [c for c in self.checks if not c.trivial]


def dotted(node: ast.AST) -> str | None:
    """`a.b.c` for a chain of attributes on a name; None for anything else."""
    parts: list[str] = []
    while isinstance(node, ast.Attribute):
        parts.append(node.attr)
        node = node.value
    if isinstance(node, ast.Name):
        parts.append(node.id)
        return ".".join(reversed(parts))
    if isinstance(node, ast.Call):  # `mocker.patch.object(...)` and `self.subTest()` chains
        inner = dotted(node.func)
        return ".".join([inner, *reversed(parts)]) if inner else None
    return None


def _last(name: str | None) -> str:
    return name.rsplit(".", 1)[-1] if name else ""


def parse(source: str) -> ast.Module:
    """`ast.parse` without the warnings about the project's own code (invalid escapes and such)."""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", SyntaxWarning)
        warnings.simplefilter("ignore", DeprecationWarning)
        return ast.parse(source)


def parse_module(source: str) -> dict[str, TestCase]:
    """The module's tests and assertion helpers by node ID. Raises SyntaxError like `ast.parse`."""
    tree = parse(source)
    module_skips = _skips_of_block(tree.body)
    tests: dict[str, TestCase] = {}
    for node in tree.body:
        if isinstance(node, FuncDef):
            if node.name.startswith("test") and not _is_fixture(node):
                tests[node.name] = _case(node, node.name, module_skips, helper=False)
            elif _is_helper(node):
                tests[node.name] = _case(node, node.name, frozenset(), helper=True)
        elif isinstance(node, ast.ClassDef) and _is_test_class(node):
            _collect_class(node, node.name, module_skips, tests)
    # a test that calls a function of this module which checks something delegates its checks,
    # whatever the function is called (`sT(...)`, `self.queries.test_x()`)
    checkers = {
        fn.name
        for fn in ast.walk(tree)
        if isinstance(fn, FuncDef) and any(not c.trivial for c in _checks(fn.body))
    }
    for case in tests.values():
        # the helper may share the test's name (`self.queries.test_a()` from `test_a`)
        if not case.calls_helper and case.called & checkers:
            case.calls_helper = True
    comments = _comments(source)
    for case in tests.values():
        case.comments = frozenset(
            text for line, text in comments.items() if case.line <= line <= case.end_line
        )
    return tests


def _comments(source: str) -> dict[int, str]:
    found: dict[int, str] = {}
    try:
        for token in tokenize.generate_tokens(io.StringIO(source).readline):
            if token.type == tokenize.COMMENT:
                found[token.start[0]] = " ".join(token.string.lstrip("#").split())
    except (tokenize.TokenError, IndentationError, SyntaxError):
        pass
    return found


def _is_fixture(node: FuncDef) -> bool:
    """A pytest fixture, which pytest does not collect as a test even when named `test_*`."""
    return any("fixture" in (dotted(_unwrap(d)) or "") for d in node.decorator_list)


def _is_helper(node: FuncDef) -> bool:
    if not HELPER_NAME.search(node.name):
        return False
    # fixtures are not helpers, even when named `expected_result`
    return not _is_fixture(node)


def _is_test_class(node: ast.ClassDef) -> bool:
    if node.name.startswith("Test"):
        return True
    return any(_last(dotted(base)).endswith("TestCase") for base in node.bases)


def _collect_class(
    node: ast.ClassDef, prefix: str, inherited: frozenset[str], tests: dict[str, TestCase]
) -> None:
    skips = inherited | _decorator_skips(node.decorator_list) | _skips_of_block(node.body)
    for item in node.body:
        if isinstance(item, FuncDef):
            node_id = f"{prefix}::{item.name}"
            if item.name.startswith("test") and not _is_fixture(item):
                tests[node_id] = _case(item, node_id, skips, helper=False)
            elif _is_helper(item):
                tests[node_id] = _case(item, node_id, frozenset(), helper=True)
        elif isinstance(item, ast.ClassDef) and _is_test_class(item):
            _collect_class(item, f"{prefix}::{item.name}", skips, tests)


def _unwrap(node: ast.AST) -> ast.AST:
    return node.func if isinstance(node, ast.Call) else node


# --- skips -------------------------------------------------------------------------------------


def _skip_kind(expr: ast.expr) -> str | None:
    """What a decorator or marker does to a test: "skip", "skipif", "xfail", "xfail-if" or None."""
    call = expr if isinstance(expr, ast.Call) else None
    last = _last(dotted(_unwrap(expr)))
    if last == "skip":
        return "skip"
    if last in {"skipif", "skipIf", "skipUnless"}:
        if call and call.args and isinstance(call.args[0], ast.Constant):
            condition = bool(call.args[0].value)
            return "skip" if condition == (last != "skipUnless") else None
        return "skipif"
    if last == "xfail":
        if call is None:
            return "xfail"
        if any(k.arg == "run" and _is_false(k.value) for k in call.keywords):
            return "skip"
        if call.args or any(k.arg == "condition" for k in call.keywords):
            return "xfail-if"
        return "xfail"
    if last == "expectedFailure":
        return "xfail"
    return None


def _is_false(node: ast.expr) -> bool:
    return isinstance(node, ast.Constant) and node.value is False


def _decorator_skips(decorators: Iterable[ast.expr]) -> frozenset[str]:
    return frozenset(k for d in decorators if (k := _skip_kind(d)))


def _call_skip(call: ast.Call) -> str | None:
    """A skip done by calling something: `pytest.skip()`, `self.skipTest()`, `pytest.xfail()`."""
    name = dotted(call.func) or ""
    if name in {"pytest.skip", "skip"} or _last(name) == "skipTest":
        return "skip"
    if name in {"pytest.xfail", "xfail"}:
        return "xfail"
    if name == "pytest.importorskip":
        return "skipif"
    return None


def _raise_skip(node: ast.Raise) -> bool:
    return node.exc is not None and _last(dotted(_unwrap(node.exc))) == "SkipTest"


def _skips_of_block(body: list[ast.stmt]) -> frozenset[str]:
    """Skips a module or class body applies to all its tests (`pytestmark`, module-level skip)."""
    kinds: set[str] = set()
    for stmt in body:
        if isinstance(stmt, ast.Assign) and any(
            isinstance(t, ast.Name) and t.id == "pytestmark" for t in stmt.targets
        ):
            marks = (
                stmt.value.elts if isinstance(stmt.value, ast.List | ast.Tuple) else [stmt.value]
            )
            kinds.update(k for m in marks if (k := _skip_kind(m)))
        elif isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Call):
            kind = _call_skip(stmt.value)
            if kind == "skip" and any(k.arg == "allow_module_level" for k in stmt.value.keywords):
                kinds.add("skip")
            elif kind == "skipif":
                kinds.add("skipif")
        elif isinstance(stmt, ast.If):
            if any(_skips_here(inner) == "skip" for inner in ast.walk(stmt)):
                kinds.add("skipif")
    return frozenset(kinds)


def _skips_here(node: ast.AST) -> str | None:
    if isinstance(node, ast.Call):
        return _call_skip(node)
    if isinstance(node, ast.Raise) and _raise_skip(node):
        return "skip"
    return None


def _body_skips(body: list[ast.stmt]) -> set[str]:
    kinds: set[str] = set()
    for stmt in body:
        call = stmt.value if isinstance(stmt, ast.Expr) else None
        if isinstance(call, ast.Call) and (kind := _call_skip(call)):
            kinds.add(kind)
            continue
        if isinstance(stmt, ast.Raise) and _raise_skip(stmt):
            kinds.add("skip")
            continue
        for inner in ast.walk(stmt):
            if isinstance(inner, ast.Call) and (kind := _call_skip(inner)):
                kinds.add({"skip": "skipif", "xfail": "xfail-if"}.get(kind, kind))
            elif isinstance(inner, ast.Raise) and _raise_skip(inner):
                kinds.add("skipif")
    return kinds


# --- checks ------------------------------------------------------------------------------------


def _strip_docstring(body: list[ast.stmt]) -> list[ast.stmt]:
    first = body[0] if body else None
    if isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant):
        return body[1:] if isinstance(first.value.value, str) else body
    return body


def _reachable(body: list[ast.stmt]) -> list[ast.stmt]:
    """The statements before the first unconditional `return`, skip or `raise`."""
    out: list[ast.stmt] = []
    for stmt in body:
        if isinstance(stmt, ast.Return | ast.Raise):
            break
        out.append(stmt)
        call = stmt.value if isinstance(stmt, ast.Expr) else None
        if isinstance(call, ast.Call) and _call_skip(call) in {"skip", "xfail"}:
            break
    return out


def _is_empty(body: list[ast.stmt]) -> bool:
    return all(
        isinstance(s, ast.Pass) or (isinstance(s, ast.Expr) and isinstance(s.value, ast.Constant))
        for s in body
    )


def _same(a: ast.AST, b: ast.AST) -> bool:
    return ast.unparse(a) == ast.unparse(b)


def trivial_expr(e: ast.expr) -> bool:
    """An assert condition that always holds."""
    if isinstance(e, ast.Constant):
        return bool(e.value)
    if isinstance(e, ast.Tuple):  # `assert (x, "message")`
        return bool(e.elts)
    if isinstance(e, ast.BoolOp) and isinstance(e.op, ast.Or):
        return any(trivial_expr(v) for v in e.values)
    if isinstance(e, ast.Compare) and len(e.ops) == 1:
        reflexive = isinstance(e.ops[0], ast.Eq | ast.Is | ast.GtE | ast.LtE)
        return reflexive and _same(e.left, e.comparators[0])
    return False


def _trivial_call(last: str, call: ast.Call) -> bool:
    args = call.args
    if last in {"assertTrue", "assert_"} and args:
        return isinstance(args[0], ast.Constant) and bool(args[0].value)
    if last == "assertFalse" and args:
        return isinstance(args[0], ast.Constant) and not args[0].value
    if last in {"assertEqual", "assertEquals", "assertIs"} and len(args) >= 2:
        return _same(args[0], args[1])
    if last == "assertIsNotNone" and args:
        return isinstance(args[0], ast.Constant) and args[0].value is not None
    return False


def _walk(body: list[ast.stmt]) -> Iterator[ast.AST]:
    for stmt in body:
        yield from ast.walk(stmt)


def _checks(body: list[ast.stmt]) -> list[Check]:
    checks: list[Check] = []
    for node in _walk(body):
        if isinstance(node, ast.Assert):
            text = ast.unparse(node.test)
            checks.append(Check("assert", text, node.lineno, trivial_expr(node.test), node))
        elif isinstance(node, ast.Call):
            name = dotted(node.func)
            last = _last(name)
            if last in UNITTEST_RAISES or name in RAISES:
                checks.append(Check("raises", ast.unparse(node), node.lineno, False, node))
            elif last.startswith("assert"):
                trivial = _trivial_call(last, node)
                checks.append(Check("call", ast.unparse(node), node.lineno, trivial, node))
            elif name in {"pytest.fail", "self.fail", "fail"}:
                checks.append(Check("fail", ast.unparse(node), node.lineno, False, node))
    return checks


def _catches_failures(handler: ast.ExceptHandler) -> bool:
    if handler.type is None:
        return True
    types = handler.type.elts if isinstance(handler.type, ast.Tuple) else [handler.type]
    names = {_last(dotted(t)) for t in types}
    return bool(names & {"AssertionError", "Exception", "BaseException"})


def _reraises(handler: ast.ExceptHandler) -> bool:
    for node in _walk(handler.body):
        if isinstance(node, ast.Raise):
            return True
        if isinstance(node, ast.Call) and _last(dotted(node.func)) in {"fail", "skip", "xfail"}:
            return True
    return False


def _swallowed(body: list[ast.stmt]) -> int:
    """Checks inside `try` blocks, or `suppress(...)` blocks, that swallow their failure."""
    count = 0
    for node in _walk(body):
        guarded: list[ast.stmt] = []
        if isinstance(node, ast.Try):
            if any(_catches_failures(h) and not _reraises(h) for h in node.handlers):
                guarded = node.body
        elif isinstance(node, ast.With):
            for item in node.items:
                ctx = item.context_expr
                if isinstance(ctx, ast.Call) and _last(dotted(ctx.func)) == "suppress":
                    caught = {_last(dotted(a)) for a in ctx.args}
                    if caught & {"AssertionError", "Exception", "BaseException"}:
                        guarded = node.body
        count += sum(1 for c in _checks(guarded) if not c.trivial)
    return count


# --- tolerances --------------------------------------------------------------------------------

# func -> [(key, positional index or None, default, larger_is_looser)]
_TOLERANCES: dict[str, list[tuple[str, int | None, float | None, bool]]] = {
    "approx": [("rel", 1, 1e-6, True), ("abs", 2, 1e-12, True)],
    "assert_allclose": [("rtol", 2, 1e-7, True), ("atol", 3, 0.0, True)],
    "allclose": [("rtol", 2, 1e-5, True), ("atol", 3, 1e-8, True)],
    "isclose": [("rtol", 2, 1e-5, True), ("atol", 3, 1e-8, True)],
    "math.isclose": [("rel_tol", None, 1e-9, True), ("abs_tol", None, 0.0, True)],
    "assert_close": [("rtol", None, None, True), ("atol", None, None, True)],
    "assertAlmostEqual": [("places", 2, 7.0, False), ("delta", None, None, True)],
    "assertAlmostEquals": [("places", 2, 7.0, False), ("delta", None, None, True)],
    "assert_almost_equal": [("decimal", 2, 7.0, False)],
    "assert_array_almost_equal": [("decimal", 2, 6.0, False)],
}


def default_tolerance(func: str, key: str) -> float | None:
    for name, _position, default, _looser in _TOLERANCES.get(func, []):
        if name == key:
            return default
    return None


def _number(node: ast.expr) -> float | None:
    try:
        value = ast.literal_eval(node)
    except (ValueError, TypeError, SyntaxError, MemoryError, RecursionError):
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Pow):  # 10 ** -6
            base, power = _number(node.left), _number(node.right)
            if base is not None and power is not None:
                try:
                    return float(base**power)
                except (OverflowError, ZeroDivisionError):
                    return None
        return None
    if isinstance(value, bool) or not isinstance(value, int | float):
        return None
    return float(value)


def _tolerances(body: list[ast.stmt]) -> list[Tolerance]:
    found: list[Tolerance] = []
    for node in _walk(body):
        if isinstance(node, ast.Call):
            name = dotted(node.func) or ""
            func = "math.isclose" if name == "math.isclose" else _last(name)
            for key, position, default, looser in _TOLERANCES.get(func, []):
                value: float | None = default
                keyword = next((k for k in node.keywords if k.arg == key), None)
                if keyword is not None:
                    value = _number(keyword.value)
                elif position is not None and len(node.args) > position:
                    value = _number(node.args[position])
                if value is not None:
                    found.append(Tolerance(func, key, value, looser, node.lineno))
        elif isinstance(node, ast.Compare) and len(node.ops) == 1:
            # `abs(a - b) < 1e-6`
            left = node.left
            if (
                isinstance(left, ast.Call)
                and dotted(left.func) == "abs"
                and isinstance(node.ops[0], ast.Lt | ast.LtE)
            ):
                eps = _number(node.comparators[0])
                if eps is not None:
                    found.append(Tolerance("abs", "eps", eps, True, node.lineno))
    return found


# --- the test case -----------------------------------------------------------------------------


def _params(decorators: Iterable[ast.expr]) -> dict[str, int]:
    params: dict[str, int] = {}
    for d in decorators:
        if not (isinstance(d, ast.Call) and _last(dotted(d.func)) == "parametrize"):
            continue
        args = list(d.args)
        keywords = {k.arg: k.value for k in d.keywords if k.arg}
        names = args[0] if args else keywords.get("argnames")
        values = args[1] if len(args) > 1 else keywords.get("argvalues")
        if names is None or not isinstance(values, ast.List | ast.Tuple):
            continue
        if isinstance(names, ast.Constant) and isinstance(names.value, str):
            key = ",".join(n.strip() for n in names.value.split(","))
        else:
            key = ast.unparse(names)
        params[key] = len(values.elts)
    return params


def _patches(node: FuncDef, body: list[ast.stmt]) -> int:
    count = sum(1 for d in node.decorator_list if "patch" in (dotted(_unwrap(d)) or ""))
    for inner in _walk(body):
        if isinstance(inner, ast.Call):
            name = dotted(inner.func) or ""
            # `patch(...)`, `mock.patch.object(...)`, `mocker.patch.dict(...)`
            if name in PATCH_CALLS or "patch" in name.split("."):
                count += 1
    return count


def _calls_helper(body: list[ast.stmt]) -> bool:
    for node in _walk(body):
        if isinstance(node, ast.Call):
            name = dotted(node.func) or ""
            last = _last(name)
            if last.startswith("assert") or name.startswith("re."):
                continue
            if HELPER_NAME.search(last):
                return True
    return False


def _case(node: FuncDef, node_id: str, inherited: frozenset[str], *, helper: bool) -> TestCase:
    body = _strip_docstring(node.body)
    reachable = _reachable(body)
    skips = inherited | _decorator_skips(node.decorator_list) | _body_skips(body)
    return TestCase(
        id=node_id,
        name=node.name,
        line=node.lineno,
        helper=helper,
        checks=_checks(reachable),
        skips=frozenset(skips),
        params=_params(node.decorator_list),
        tolerances=_tolerances(reachable),
        patches=_patches(node, body),
        calls_helper=_calls_helper(reachable),
        called=frozenset(
            _last(dotted(n.func)) for n in _walk(reachable) if isinstance(n, ast.Call)
        ),
        empty=_is_empty(body),
        swallowed=_swallowed(reachable),
        returns_early=len(reachable) < len(body) and isinstance(body[len(reachable)], ast.Return),
        body="\n".join(ast.unparse(s) for s in body),
        end_line=node.end_lineno or node.lineno,
        skip_reasons=_skip_reasons(node, body),
    )


def _skip_reasons(node: FuncDef, body: list[ast.stmt]) -> tuple[str, ...]:
    reasons: list[str] = []
    calls = [d for d in node.decorator_list if isinstance(d, ast.Call) and _skip_kind(d)]
    calls += [c for c in _walk(body) if isinstance(c, ast.Call) and _call_skip(c)]
    for call in calls:
        texts = [k.value for k in call.keywords if k.arg in {"reason", "msg"}] + list(call.args)
        for text in texts:
            if isinstance(text, ast.Constant) and isinstance(text.value, str):
                reasons.append(text.value)
                break
    return tuple(reasons)
