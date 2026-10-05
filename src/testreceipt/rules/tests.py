"""Rules on the tests themselves: removed, skipped, emptied or loosened.

Every test before the change is paired with the same test after it: by node ID in the same file,
then by name in another changed file (a moved test), then by a body that is mostly the same (a
renamed test). Pairs are compared check by check; tests left without a pair were removed.
"""

from __future__ import annotations

import ast
import difflib
import re
from collections import Counter
from dataclasses import dataclass

from ..changes import FileChange, is_test_file
from ..model import Finding, Level, Unchecked
from ..pytests import Check, TestCase, default_tolerance, dotted, parse_module
from . import TITLES

INTEGRATION_PATH = re.compile(
    r"(?:^|/)(?:integration|e2e|end_to_end|functional|system|acceptance)(?:_tests?)?(?:/|$)",
    re.IGNORECASE,
)
SIMILAR_BODY = 0.8
# Pairing removed with added tests by body similarity costs one comparison per pair; above this many
# pairs only identical bodies are paired.
MAX_FUZZY_PAIRS = 40_000
# More findings than this from one rule in one file are reported as one finding.
COLLAPSE_OVER = 5

EXACT_CALLS = frozenset(
    {
        "assertEqual",
        "assertEquals",
        "assertListEqual",
        "assertDictEqual",
        "assertSetEqual",
        "assertTupleEqual",
        "assertSequenceEqual",
        "assertMultiLineEqual",
        "assertCountEqual",
        "assertIs",
        "assertIsNone",
        "assertRaises",
        "assertRaisesRegex",
        "assert_called_once_with",
        "assert_called_with",
        "assert_has_calls",
        "assert_awaited_once_with",
        "assert_awaited_with",
        "assert_frame_equal",
        "assert_series_equal",
        "assert_index_equal",
        "assert_array_equal",
        "assert_equal",
    }
)
WEAK_CALLS = frozenset(
    {
        "assertTrue",
        "assertFalse",
        "assertIsNotNone",
        "assertIsInstance",
        "assertIn",
        "assertNotIn",
        "assertGreater",
        "assertGreaterEqual",
        "assertLess",
        "assertLessEqual",
        "assertNotEqual",
        "assertIsNot",
        "assert_called",
        "assert_called_once",
        "assert_any_call",
        "assert_awaited",
        "assert_awaited_once",
    }
)
MOCK_ASSERT = re.compile(r"^assert_(?:not_)?(?:called|any_call|has_calls|awaited)")
WEAK_PREDICATES = frozenset({"isinstance", "hasattr", "callable", "len", "bool", "any", "all"})
BROAD_EXCEPTIONS = frozenset({"Exception", "BaseException"})


@dataclass(frozen=True)
class _Located:
    path: str
    case: TestCase


def _code(text: str, limit: int = 70) -> str:
    text = " ".join(text.split())
    return f"`{text if len(text) <= limit else text[: limit - 1] + '…'}`"


def check_tests(changes: list[FileChange]) -> tuple[list[Finding], list[Unchecked]]:
    before: dict[tuple[str, str], _Located] = {}
    after: dict[tuple[str, str], _Located] = {}
    unchecked: list[Unchecked] = []
    for change in changes:
        if not (is_test_file(change.path) or is_test_file(change.before_path)):
            continue
        try:
            old_tests = parse_module(change.before) if change.before is not None else {}
            new_tests = parse_module(change.after) if change.after is not None else {}
        except (SyntaxError, ValueError, RecursionError) as error:
            unchecked.append(Unchecked(change.path, f"cannot parse: {error}"))
            continue
        for module, side in ((old_tests, before), (new_tests, after)):
            for node_id, case in module.items():
                side[(change.path, node_id)] = _Located(change.path, case)

    pairs: list[tuple[_Located, _Located]] = []
    for key in list(before):
        if key in after:
            pairs.append((before.pop(key), after.pop(key)))
    pairs += _pair_moved(before, after)

    findings: list[Finding] = []
    for old, new in pairs:
        findings += compare(old.case, new.case, new.path)
    findings += _removed(before, after)
    findings += _added(after)
    return _collapse(findings), unchecked


def _pair_moved(
    before: dict[tuple[str, str], _Located], after: dict[tuple[str, str], _Located]
) -> list[tuple[_Located, _Located]]:
    """Pairs removed tests with added ones: same name in another file, else a similar body."""
    pairs: list[tuple[_Located, _Located]] = []
    by_name: dict[str, list[tuple[str, str]]] = {}
    for key, loc in after.items():
        by_name.setdefault(loc.case.id, []).append(key)
    for key, loc in list(before.items()):
        candidates = [k for k in by_name.get(loc.case.id, []) if k in after]
        if candidates:
            pairs.append((before.pop(key), after.pop(candidates[0])))

    by_body: dict[str, list[tuple[str, str]]] = {}
    for key, loc in after.items():
        by_body.setdefault(loc.case.body, []).append(key)
    for key, loc in list(before.items()):
        candidates = [k for k in by_body.get(loc.case.body, []) if k in after]
        if candidates and loc.case.body:
            pairs.append((before.pop(key), after.pop(candidates[0])))

    if len(before) * len(after) > MAX_FUZZY_PAIRS:
        return pairs
    for key, loc in list(before.items()):
        best, best_ratio = None, SIMILAR_BODY
        for other_key, other in after.items():
            if other.case.helper != loc.case.helper:
                continue
            matcher = difflib.SequenceMatcher(None, loc.case.body, other.case.body, autojunk=False)
            if matcher.real_quick_ratio() < best_ratio or matcher.quick_ratio() < best_ratio:
                continue
            ratio = matcher.ratio()
            if ratio >= best_ratio:
                best, best_ratio = other_key, ratio
        if best is not None:
            pairs.append((before.pop(key), after.pop(best)))
    return pairs


# --- comparing one test ------------------------------------------------------------------------


def compare(old: TestCase, new: TestCase, path: str) -> list[Finding]:
    """What the change did to one test, or to one assertion helper."""
    findings: list[Finding] = []

    def add(rule: str, level: Level, message: str, line: int | None = None) -> None:
        findings.append(Finding(rule, level, path, line or new.line, message, test=new.id))

    kind = "helper" if new.helper else "test"
    new_skips = new.skips - old.skips
    if new_skips & {"skip", "xfail"}:
        what = "skipped" if "skip" in new_skips else "marked xfail"
        reasons = [r for r in new.skip_reasons if r not in old.skip_reasons]
        because = f"; reason given: {_code(reasons[0], 90)}" if reasons else "; no reason given"
        add("TR111", Level.CAUGHT, f"the {kind} is now {what} unconditionally{because}")
        return findings
    if new_skips & {"skipif", "xfail-if"}:
        add("TR111", Level.SUSPICIOUS, f"the {kind} is now skipped under a condition")

    old_live, new_live = old.live_checks, new.live_checks
    if old_live and not new_live:
        if new.swallowed:
            add(
                "TR103",
                Level.CAUGHT,
                "its assertions now sit in a try block that swallows failures",
            )
            return findings
        if new.empty:
            add("TR101", Level.CAUGHT, f"the {kind} body was emptied ({len(old_live)} checks gone)")
            return findings
        if new.checks and all(c.trivial for c in new.checks):
            example = new.checks[0].text
            add(
                "TR101",
                Level.CAUGHT,
                f"its {len(old_live)} real checks are gone; only {_code(example)} remains, "
                "which always holds",
            )
            return findings
        if new.returns_early:
            add("TR101", Level.CAUGHT, f"the {kind} now returns before its {len(old_live)} checks")
            return findings
        if not new.calls_helper:
            message = f"all {len(old_live)} checks were removed, e.g. {_code(old_live[0].text)}"
            # a maintainer who drops a check on purpose tends to say why; that is for a reviewer
            # to weigh, so the finding stays a question rather than a verdict
            explained = sorted(new.comments - old.comments)
            if explained:
                message += f"; a new comment says: {_code(explained[0], 90)}"
            level = Level.SUSPICIOUS if explained else Level.CAUGHT
            add("TR101", level, message, old_live[0].line)
            return findings
    trivial_before = sum(1 for c in old.checks if c.trivial)
    trivial_now = [c for c in new.checks if c.trivial]
    if len(trivial_now) > trivial_before and len(new_live) < len(old_live):
        always = trivial_now[0]
        n = len(old_live) - len(new_live)
        message = (
            f"{n} of {len(old_live)} checks replaced by {_code(always.text)}, which always holds"
        )
        add("TR101", Level.CAUGHT, message, always.line)
        return findings
    if new.swallowed > old.swallowed:
        add("TR103", Level.CAUGHT, "assertions were put in a try block that swallows failures")

    findings += _compare_checks(old, new, path)

    loosened = _loosened(old, new)
    if loosened:
        add("TR106", Level.SUSPICIOUS, loosened)
    old_cases, new_cases = sum(old.params.values()), sum(new.params.values())
    if new_cases < old_cases:
        add("TR112", Level.SUSPICIOUS, f"parametrized cases cut from {old_cases} to {new_cases}")
    if new.patches > old.patches:
        level = Level.SUSPICIOUS if INTEGRATION_PATH.search(path) else Level.NOTE
        n = new.patches - old.patches
        add("TR120", level, f"{n} mock{'s' if n > 1 else ''} added")
    return findings


def _compare_checks(old: TestCase, new: TestCase, path: str) -> list[Finding]:
    old_live, new_live = old.live_checks, new.live_checks
    gone = Counter(c.text for c in old_live) - Counter(c.text for c in new_live)
    came = Counter(c.text for c in new_live) - Counter(c.text for c in old_live)
    removed = _take(old_live, gone)
    added = _take(new_live, came)

    findings: list[Finding] = []
    unpaired: list[Check] = []
    for check in removed:
        partner = _partner(check, added)
        if partner is None:
            unpaired.append(check)
            continue
        added.remove(partner)
        verdict = _judge_pair(check, partner)
        if verdict is not None:
            rule, level, message = verdict
            findings.append(Finding(rule, level, path, partner.line, message, test=new.id))
    if len(new_live) < len(old_live) and unpaired:
        moved_to_helper = new.calls_helper and not old.calls_helper
        # checks removed while different ones were added read as a rewrite, usually for a
        # change of behaviour; a reviewer may still want to look
        rewritten = bool(added)
        level = Level.NOTE if moved_to_helper or rewritten else Level.SUSPICIOUS
        n = len(old_live) - len(new_live)
        message = f"{n} of {len(old_live)} checks removed, e.g. {_code(unpaired[0].text)}"
        if rewritten:
            message += f"; {len(added)} different checks were added, e.g. {_code(added[0].text)}"
        findings.append(Finding("TR102", level, path, new.line, message, test=new.id))
    return findings


def _take(checks: list[Check], wanted: Counter[str]) -> list[Check]:
    left = Counter(wanted)
    out = []
    for check in checks:
        if left[check.text] > 0:
            left[check.text] -= 1
            out.append(check)
    return out


def _subject(check: Check) -> str | None:
    node = check.node
    if isinstance(node, ast.Assert):
        test = node.test
        if isinstance(test, ast.UnaryOp) and isinstance(test.op, ast.Not):
            test = test.operand
        if isinstance(test, ast.Compare):
            left = test.left
            if isinstance(left, ast.Call) and dotted(left.func) == "len" and left.args:
                left = left.args[0]
            return ast.unparse(left)
        if isinstance(test, ast.Call) and dotted(test.func) in WEAK_PREDICATES and test.args:
            return ast.unparse(test.args[0])
        return ast.unparse(test)
    if isinstance(node, ast.Call):
        last = (dotted(node.func) or "").rsplit(".", 1)[-1]
        if MOCK_ASSERT.match(last) and isinstance(node.func, ast.Attribute):
            return ast.unparse(node.func.value)
        if check.kind == "raises":
            return "raises"
        if node.args:
            return ast.unparse(node.args[0])
    return None


def _partner(check: Check, added: list[Check]) -> Check | None:
    subject = _subject(check)
    if subject is None:
        return None
    for other in added:
        if _subject(other) == subject:
            return other
    return None


def _strength(check: Check) -> str:
    """ "exact" for checks that pin a value down, "weak" for those that only constrain it."""
    node = check.node
    if isinstance(node, ast.Assert):
        test = node.test
        if isinstance(test, ast.Compare) and len(test.ops) == 1:
            op = test.ops[0]
            return "exact" if isinstance(op, ast.Eq | ast.Is) else "weak"
        return "weak"
    if isinstance(node, ast.Call):
        name = dotted(node.func) or ""
        last = name.rsplit(".", 1)[-1]
        if check.kind == "raises":
            types = {(dotted(a) or "").rsplit(".", 1)[-1] for a in node.args[:1]}
            has_match = any(k.arg in {"match", "expected_regex"} for k in node.keywords)
            if types & BROAD_EXCEPTIONS and not has_match:
                return "weak"
            return "exact"
        if last in EXACT_CALLS:
            return "exact"
        if last in WEAK_CALLS:
            return "weak"
    return "other"


def _is_literal(node: ast.expr) -> bool:
    try:
        ast.literal_eval(node)
    except (ValueError, TypeError, SyntaxError, MemoryError, RecursionError):
        return False
    return True


def _expected(check: Check) -> ast.expr | None:
    node = check.node
    test = node.test if isinstance(node, ast.Assert) else None
    if isinstance(test, ast.Compare) and len(test.ops) == 1 and isinstance(test.ops[0], ast.Eq):
        return test.comparators[0]
    if isinstance(node, ast.Call) and check.kind == "call" and len(node.args) >= 2:
        return node.args[1]
    return None


def _same_value(old: ast.expr, new: ast.expr) -> bool:
    """The same expression, or the same `approx(value, ...)` with other options."""
    if ast.unparse(old) == ast.unparse(new):
        return True
    if isinstance(old, ast.Call) and isinstance(new, ast.Call):
        same_func = ast.unparse(old.func) == ast.unparse(new.func)
        old_value = [ast.unparse(a) for a in old.args[:1]]
        return same_func and old_value == [ast.unparse(a) for a in new.args[:1]]
    return False


def _judge_pair(old: Check, new: Check) -> tuple[str, Level, str] | None:
    old_strength, new_strength = _strength(old), _strength(new)
    change = f"{_code(old.text, 50)} became {_code(new.text, 50)}"
    if old.kind == "raises" and new.kind == "raises":
        if old_strength == "exact" and new_strength == "weak":
            return "TR104", Level.SUSPICIOUS, f"the expected exception was broadened: {change}"
        old_match = "match=" in old.text or "Regex" in old.text
        if old_match and "match=" not in new.text and "Regex" not in new.text:
            return (
                "TR104",
                Level.SUSPICIOUS,
                f"the exception message is no longer checked: {change}",
            )
        return None
    if old_strength == "exact" and new_strength == "weak":
        return "TR104", Level.SUSPICIOUS, change
    old_expected, new_expected = _expected(old), _expected(new)
    if old_expected is not None and new_expected is not None:
        if _same_value(old_expected, new_expected):
            return None  # the expected value stayed; options such as a tolerance changed
        if not _is_literal(old_expected) and _is_literal(new_expected):
            return "TR105", Level.SUSPICIOUS, f"a computed expected value was hardcoded: {change}"
        return "TR105", Level.NOTE, change
    return None


def _loosened(old: TestCase, new: TestCase) -> str | None:
    def grouped(case: TestCase) -> dict[tuple[str, str], list[float]]:
        out: dict[tuple[str, str], list[float]] = {}
        for t in case.tolerances:
            out.setdefault((t.func, t.key), []).append(t.value)
        return out

    looser_when_larger = {(t.func, t.key): t.larger_is_looser for t in new.tolerances}
    old_groups, new_groups = grouped(old), grouped(new)
    old_funcs = {t.func for t in old.tolerances}
    for key, new_values in new_groups.items():
        old_values = old_groups.get(key, [])
        default = default_tolerance(*key)
        if not old_values and key[0] in old_funcs and default is not None:
            # the same check before, without this option (or with `*args` hiding it)
            old_values = [default] * len(new_values)
        for before, after in zip(old_values, new_values, strict=False):
            larger = looser_when_larger[key]
            if (after > before) if larger else (after < before):
                func, name = key
                return f"{func} {name} went from {before:g} to {after:g}"
    return None


# --- tests without a pair ----------------------------------------------------------------------


def _removed(
    before: dict[tuple[str, str], _Located], after: dict[tuple[str, str], _Located]
) -> list[Finding]:
    """Tests without a pair. Where the same file gains at least as many new tests, the file was
    most likely rewritten (tests renamed, merged or parametrized), which is only a note."""
    by_path: dict[str, list[TestCase]] = {}
    for loc in before.values():
        if not loc.case.helper:
            by_path.setdefault(loc.path, []).append(loc.case)
    # only new tests that check something count: an empty one must not cover for a deleted one
    new_tests = Counter(
        loc.path for loc in after.values() if not loc.case.helper and loc.case.live_checks
    )
    findings = []
    for path, cases in by_path.items():
        names = ", ".join(c.id for c in cases[:4]) + (", …" if len(cases) > 4 else "")
        n = len(cases)
        message = f"{n} test{'s' if n > 1 else ''} removed: {names}"
        level = Level.SUSPICIOUS
        if new_tests[path] >= n:
            level = Level.NOTE
            message += f"; {new_tests[path]} new tests were added to the same file"
        findings.append(Finding("TR110", level, path, None, message))
    return findings


def _added(after: dict[tuple[str, str], _Located]) -> list[Finding]:
    findings = []
    for loc in after.values():
        case = loc.case
        if case.helper:
            continue
        if not case.live_checks and not case.calls_helper and not case.skips:
            findings.append(
                Finding(
                    "TR121", Level.NOTE, loc.path, case.line, "new test checks nothing", case.id
                )
            )
    return findings


def _collapse(findings: list[Finding]) -> list[Finding]:
    """Many findings of one rule in one file become one."""
    groups: dict[tuple[str, str, Level], list[Finding]] = {}
    for f in findings:
        groups.setdefault((f.rule, f.path, f.level), []).append(f)
    out: list[Finding] = []
    for (rule, path, level), group in groups.items():
        tests = [f for f in group if f.test]
        if len(tests) <= COLLAPSE_OVER:
            out += group
            continue
        out += [f for f in group if not f.test]
        names = ", ".join(f.test or "" for f in tests[:3])
        message = f"{len(tests)} tests: {TITLES[rule]} ({names}, …); first: {tests[0].message}"
        out.append(Finding(rule, level, path, tests[0].line, message))
    return out
