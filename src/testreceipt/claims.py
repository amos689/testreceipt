"""What an agent says about its test runs, in a pull request description or a commit message.

A claim is a line that says tests passed ("All 101 tests pass", "✅ `pytest -q`", "12 passed in
0.4s") or failed ("`pytest` *(fails: 3 failed)*"). Lines that only ask for tests to pass, such as
an unticked template checkbox or "make sure all tests pass", are not claims. Precision matters more
than recall: a line is only taken as a claim when it reads as a report of something done.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

TEST_WORD = r"(?:tests?|test suites?|test cases?|unit tests?|testing)"
RUNNER = r"(?<![\w-])(?:pytest|py\.test|jest|vitest|mocha|tox|nox|ctest)(?![\w-])"
# "passing" only as an outcome ("are passing", "passing with"), not as in "passing programs"
PASS_VERB = (
    r"(?:pass(?:es|ed)?\b|(?:are|is|now|all|still)\s+passing\b"
    r"|passing(?=\s*(?:[.,;:!()]|$|with\b|locally\b|successfully\b|after\b|on\b|in\b))"
    r"|succeed(?:s|ed)?\b|(?:are|is|now)\s+green\b|continue\s+to\s+pass\b)"
)
TEST_COMMAND = re.compile(
    r"`[^`]*(?<![\w-])(?:pytest|py\.test|tox|nox|unittest|jest|vitest|mocha|ctest)(?![\w-])[^`]*`"
    r"|`[^`]*\b(?:(?:npm|yarn|pnpm|bun)\s+(?:run\s+)?test|go\s+test|cargo\s+test|dotnet\s+test"
    r"|mvn\s+test|gradlew?\s+test|make\s+test|manage\.py\s+test|hatch\s+test)\b[^`]*`",
    re.IGNORECASE,
)
PASSED = re.compile(
    # the tests as the subject, at most five words before the verb: "All 101 tests now pass"
    rf"\b{TEST_WORD}\b(?:\s+[^\s.;]+){{0,5}}?\s*:?\s+{PASS_VERB}"
    rf"|\bpass(?:es|ed)?\s+(?:all\s+)?(?:the\s+)?(?:\d+\s+)?(?:existing\s+)?{TEST_WORD}\b"
    r"|\b\d+\s+passed\b|\b(\d+)\s*/\s*\1\s+(?:tests?\s+)?pass"
    r"|(?:测试|单元测试|用例)[^。\n]{0,20}(?:全部|均|都)?通过",
    re.IGNORECASE,
)
FAILED = re.compile(
    r"\bfail(?:s|ed|ing|ures?)?\b|\berrors?\b|❌|⛔|\bbroken\b|未通过|失败",
    re.IGNORECASE,
)
ZERO_FAILURES = re.compile(
    r"\b(?:0|no|zero)\s+(?:failures?|failed|errors?|failing)\b", re.IGNORECASE
)
HEDGE = re.compile(
    r"\b(?:should|ensure|make sure|verify that|needs? to|must|will|would|could|might|please|"
    r"expect(?:ed|s)?|hopefully|once|if|todo|in order to|so that|so (?:it|they)|to make|"
    r"(?<!continue )to pass)\b"
    r"|n't\b|\bnot\b|\bunable\b|\bwithout\b",
    re.IGNORECASE,
)
UNTICKED = re.compile(r"^\s*(?:[-*+]|\d+\.)\s*\[\s\]")
TICKED = re.compile(r"^\s*(?:[-*+]|\d+\.)\s*\[[xX]\]")
COUNT = re.compile(
    rf"\b(?:all\s+)?(\d{{1,6}})\s+(?:\w+\s+){{0,2}}?{TEST_WORD}\b|\b(\d{{1,6}})\s+passed\b",
    re.IGNORECASE,
)
SECTION = re.compile(r"^\s*#{1,6}\s*(.+?)\s*$")
TESTING_SECTIONS = re.compile(r"\b(?:testing|tests?|checks?|verification|validation)\b", re.I)
COMMENT = re.compile(r"<!--.*?-->", re.DOTALL)


@dataclass(frozen=True)
class Claim:
    kind: str  # "pass" or "fail"
    text: str  # the line, as written
    count: int | None  # how many tests it says passed, when it says
    explicit: bool  # said in words, rather than implied by a command listed without a failure


def claims(text: str) -> list[Claim]:
    found: list[Claim] = []
    section = ""
    for raw in COMMENT.sub("", text or "").splitlines():
        line = raw.strip()
        if not line:
            continue
        heading = SECTION.match(line)
        if heading:
            section = heading.group(1)
            continue
        if UNTICKED.match(line):
            continue
        claim = _claim(line, testing_section=bool(TESTING_SECTIONS.search(section)))
        if claim:
            found.append(claim)
    return found


def _claim(line: str, *, testing_section: bool) -> Claim | None:
    cleared = ZERO_FAILURES.sub("", line)
    command = TEST_COMMAND.search(line)
    tests_mentioned = bool(command) or bool(
        re.search(rf"\b{TEST_WORD}\b|{RUNNER}|\b\d+\s+passed\b|测试|用例", line, re.IGNORECASE)
    )
    if not tests_mentioned:
        return None
    if FAILED.search(cleared) or "⚠" in line:
        return Claim("fail", line, None, explicit=True)
    count = _count(line)
    if PASSED.search(line) and not HEDGE.search(_after_tick(line)):
        return Claim("pass", line, count, explicit=True)
    # a tick next to a test command reports a run; a tick next to "Added tests" reports work done
    if command and any(mark in line for mark in ("✅", "✔", "☑")):
        return Claim("pass", line, count, explicit=True)
    if command and testing_section and _listed(line):
        # agents such as Codex list the commands they ran under "Testing" and note failures
        return Claim("pass", line, count, explicit=False)
    return None


def _after_tick(line: str) -> str:
    return TICKED.sub("", line)


def _listed(line: str) -> bool:
    return bool(re.match(r"^\s*(?:[-*+]|\d+\.)\s", line)) or line.startswith("`")


def _count(line: str) -> int | None:
    match = COUNT.search(line)
    if not match:
        return None
    return int(match.group(1) or match.group(2))


def overall(found: list[Claim]) -> str:
    """ "pass", "implied pass", "fail", "mixed" or "none" for a whole description."""
    kinds = {c.kind for c in found}
    if kinds == {"pass"}:
        return "pass" if any(c.explicit for c in found) else "implied pass"
    if kinds == {"fail"}:
        return "fail"
    if kinds:
        return "mixed"
    return "none"
