"""Rules on CI workflows, build scripts and test configuration.

Workflows and scripts are compared command by command (lines continued with a backslash are joined):
the commands a change adds are checked for ways to let a test run fail quietly (`|| true`,
`continue-on-error`), to run fewer tests (`--deselect`, `-k "not …"`) or to stop running them. The
pytest options in `pyproject.toml` and ini files are read in full and compared option by option.
"""

from __future__ import annotations

import configparser
import difflib
import re
import shlex
import tomllib
from collections import Counter
from collections.abc import Iterator
from pathlib import PurePosixPath

from ..changes import FileChange
from ..model import Finding, Level

WORKFLOW_NAMES = frozenset(
    {
        ".gitlab-ci.yml",
        "azure-pipelines.yml",
        ".travis.yml",
        "Jenkinsfile",
        "bitbucket-pipelines.yml",
        "appveyor.yml",
        ".drone.yml",
        "cloudbuild.yaml",
    }
)
SCRIPT_NAMES = frozenset(
    {"Makefile", "makefile", "GNUmakefile", "justfile", "Justfile", "Taskfile.yml", "noxfile.py"}
)
PYTEST_CONFIGS = frozenset({"pyproject.toml", "pytest.ini", "tox.ini", "setup.cfg"})
COVERAGE_CONFIGS = frozenset({".coveragerc", "codecov.yml", ".codecov.yml"})
GUARD_FILES = frozenset({".testreceipt.toml", "testreceipt.toml"})

TEST_COMMAND = re.compile(
    r"(?<!\w)(?:py\.test|pytest|tox|nox|nose2|unittest|ctest|jest|vitest|mocha)(?![\w-])"
    r"|\bmanage\.py\s+test\b|\bhatch\s+(?:run\s+\S*)?test\b|\bmake\s+(?:-\S+\s+)*\w*test\w*"
    r"|\b(?:go|cargo|mvn|gradlew?|dotnet|bazel|just|task)\s+test\b"
    r"|\b(?:npm|yarn|pnpm|bun)\s+(?:run\s+)?test\b|\./\S*test\S*\.sh\b"
)
INSTALL = re.compile(
    r"\b(?:pip3?|conda|mamba|pipx|apt(?:-get)?|brew)\s+install\b|\buv\s+(?:pip\s+install|add|sync)\b"
    r"|\bpoetry\s+add\b|--with\b|\bimport\s+pytest\b|\buses:|\bname:"
)
IGNORE_FAILURE = re.compile(
    r"\|\|\s*(?:true\b|:(?:\s|$)|exit\s+0\b|echo\b)|;\s*(?:true|exit\s+0)\s*$"
)
THRESHOLD = re.compile(
    r"(?:fail[_-]under|cov-fail-under|minimum[_-]coverage|coverage[_-]threshold)"
    r"\s*[=:]?\s*[\"']?(\d+(?:\.\d+)?)"
)
CODECOV_TARGET = re.compile(r"\btarget:\s*[\"']?(\d+(?:\.\d+)?)")
DISABLED = re.compile(r"^\s*-?\s*if:\s*(?:false|0|\$\{\{\s*false\s*\}\})\s*$")
ALLOWED_TO_FAIL = re.compile(r"^\s*-?\s*(?:continue-on-error|allow_failure):\s*true\b")

_Hit = tuple[str, Level, int | None, str]


def kinds(path: str) -> set[str]:
    """What a file is to these rules: "workflow", "script", "pytest-config", "coverage", "guard"."""
    p = PurePosixPath(path)
    found: set[str] = set()
    if p.name in GUARD_FILES:
        found.add("guard")
    if (path.startswith(".github/workflows/") and p.suffix in {".yml", ".yaml"}) or (
        p.name in WORKFLOW_NAMES or path.startswith((".circleci/", ".buildkite/"))
    ):
        found.add("workflow")
    if p.name in SCRIPT_NAMES or p.name == "tox.ini" or (p.suffix == ".sh" and "test" in p.name):
        found.add("script")
    if p.name in PYTEST_CONFIGS:
        found.add("pytest-config")
    if p.name in COVERAGE_CONFIGS or p.name in PYTEST_CONFIGS:
        found.add("coverage")
    return found


def _is_comment(text: str) -> bool:
    return text.lstrip().startswith("#")


def is_test_command(text: str) -> bool:
    return bool(TEST_COMMAND.search(text)) and not _is_comment(text) and not INSTALL.search(text)


def _logical(text: str) -> list[tuple[int, str]]:
    """Lines with backslash continuations joined, each with the number of its first line."""
    out: list[tuple[int, str]] = []
    pending: list[str] = []
    start = 0
    for number, line in enumerate(text.splitlines(), 1):
        if not pending:
            start = number
        stripped = line.rstrip()
        if stripped.endswith("\\"):
            pending.append(stripped[:-1])
            continue
        pending.append(line)
        out.append((start, " ".join(" ".join(pending).split())))
        pending = []
    if pending:
        out.append((start, " ".join(" ".join(pending).split())))
    return out


def _diff(
    before: list[tuple[int, str]], after: list[tuple[int, str]]
) -> tuple[list[tuple[int, str]], list[tuple[int, str]]]:
    old = [t for _, t in before]
    new = [t for _, t in after]
    removed: list[tuple[int, str]] = []
    added: list[tuple[int, str]] = []
    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(
        None, old, new, autojunk=False
    ).get_opcodes():
        if tag in {"replace", "delete"}:
            removed += before[i1:i2]
        if tag in {"replace", "insert"}:
            added += after[j1:j2]
    return removed, added


def _physical(text: str) -> list[tuple[int, str]]:
    return list(enumerate(text.splitlines(), 1))


def check_ci(changes: list[FileChange]) -> list[Finding]:
    findings: list[Finding] = []
    commands_before: Counter[str] = Counter()
    commands_after: Counter[str] = Counter()
    deleted_runners: list[str] = []
    first_runner: str | None = None
    for change in changes:
        found = kinds(change.path)
        if not found:
            continue
        before, after = change.before or "", change.after or ""
        hits: list[_Hit] = []
        if "guard" in found:
            if change.before is not None:
                hits.append(("TR406", Level.CAUGHT, None, "testreceipt's configuration changed"))
            findings += [_finding(change.path, h) for h in hits]
            continue
        removed, added = _diff(_physical(before), _physical(after))
        hits += _guard_lines(after, removed, added)
        hits += _thresholds(removed, added, codecov="codecov" in change.path)
        if found & {"workflow", "script"}:
            old_commands, new_commands = _commands(before), _commands(after)
            commands_before.update(old_commands)
            commands_after.update(new_commands)
            if old_commands and first_runner is None:
                first_runner = change.path
            if change.after is None and old_commands:
                deleted_runners.append(change.path)
            makefile = PurePosixPath(change.path).name in {"Makefile", "makefile", "GNUmakefile"}
            removed_commands, added_commands = _diff(_logical(before), _logical(after))
            hits += _command_lines(removed_commands, added_commands, makefile=makefile)
        if "workflow" in found:
            hits += _workflow_lines(after, added)
        if "pytest-config" in found:
            hits += _pytest_config(change)
        if change.before is None:
            # a new workflow or script weakens nothing that ran before; it is still worth a look
            hits = [
                (rule, Level.SUSPICIOUS, line, f"{message} (in a new file)")
                if rule != "TR406"
                else (rule, level, line, message)
                for rule, level, line, message in hits
            ]
        findings += [_finding(change.path, h) for h in hits]

    for path in deleted_runners:
        findings.append(
            Finding("TR405", Level.SUSPICIOUS, path, None, "a file that ran tests was deleted")
        )
    lost = sum(commands_before.values()) - sum(commands_after.values())
    if lost > 0 and not deleted_runners and first_runner:
        gone = next(iter(commands_before - commands_after), "")
        none_left = not commands_after
        findings.append(
            Finding(
                "TR405",
                Level.CAUGHT if none_left else Level.SUSPICIOUS,
                first_runner,
                None,
                f"{lost} test command{'s' if lost > 1 else ''} removed, e.g. `{gone}`"
                + ("; the changed files no longer run any tests" if none_left else ""),
            )
        )
    return findings


def _finding(path: str, hit: _Hit) -> Finding:
    rule, level, line, message = hit
    return Finding(rule, level, path, line, message)


def _commands(text: str) -> list[str]:
    return [t.lstrip("- ").removeprefix("run: ") for _, t in _logical(text) if is_test_command(t)]


# --- options that change which tests run -------------------------------------------------------


def _tokens(command: str) -> list[str]:
    try:
        return shlex.split(command, comments=False, posix=True)
    except ValueError:
        return command.split()


def _option_hits(old: list[str], new: list[str]) -> Iterator[tuple[str, Level, str]]:
    """Options in `new`, and not in `old`, that leave tests out or keep them from running."""

    def options(tokens: list[str]) -> Counter[str]:
        found: Counter[str] = Counter()
        for i, token in enumerate(tokens):
            following = tokens[i + 1] if i + 1 < len(tokens) else ""
            if token == "--deselect" or token.startswith("--deselect="):
                found["deselect"] += 1
            elif token in {"-k", "-m"} and following.split()[:1] == ["not"]:
                found[token] += 1
            elif token.startswith(("-k", "-m")) and token[2:].lstrip("= ").startswith("not "):
                found[token[:2]] += 1
            elif token in {"--ignore", "--ignore-glob"} or token.startswith(
                ("--ignore=", "--ignore-glob=")
            ):
                found["ignore"] += 1
            elif token in {"--collect-only", "--co"}:
                found["collect-only"] += 1
        return found

    for option in options(new) - options(old):
        if option == "deselect":
            yield "TR403", Level.CAUGHT, "`--deselect` leaves named tests out"
        elif option == "-k":
            yield "TR403", Level.CAUGHT, '`-k "not …"` leaves named tests out'
        elif option == "-m":
            yield "TR403", Level.SUSPICIOUS, '`-m "not …"` leaves marked tests out'
        elif option == "ignore":
            yield "TR403", Level.SUSPICIOUS, "`--ignore` leaves test files out"
        elif option == "collect-only":
            yield "TR405", Level.CAUGHT, "tests are collected but no longer run"


def _command_lines(
    removed: list[tuple[int, str]], added: list[tuple[int, str]], *, makefile: bool = False
) -> Iterator[_Hit]:
    def ignores_failure(text: str) -> bool:
        # in a Makefile, a recipe line starting with `-` ignores its failure
        return bool(IGNORE_FAILURE.search(text)) or (makefile and text.lstrip("@+").startswith("-"))

    removed_commands = [t for _, t in removed if is_test_command(t)]
    removed_texts = {t for _, t in removed}
    old_ignoring = sum(1 for t in removed_commands if ignores_failure(t))
    old_tokens = [token for t in removed_commands for token in _tokens(t)]
    for number, text in added:
        if is_test_command(text):
            if ignores_failure(text):
                if old_ignoring:
                    old_ignoring -= 1
                else:
                    yield "TR401", Level.CAUGHT, number, f"test failures ignored: `{text}`"
            for rule, level, message in _option_hits(old_tokens, _tokens(text)):
                yield rule, level, number, f"{message}: `{text}`"
        elif _is_comment(text):
            uncommented = " ".join(text.lstrip().lstrip("#").split())
            if uncommented in removed_texts and is_test_command(uncommented):
                yield "TR405", Level.CAUGHT, number, f"test command commented out: `{uncommented}`"


def _indent(text: str) -> int:
    return len(text) - len(text.lstrip(" "))


def _block(lines: list[str], index: int) -> list[str]:
    """The YAML mapping a line belongs to: its sibling keys, their children and its list item."""
    level = _indent(lines[index])
    start = index
    while start > 0:
        prev = lines[start - 1]
        if prev.strip() and _indent(prev) < level:
            if prev.lstrip().startswith("- ") and _indent(prev) + 2 == level:
                start -= 1
            break
        start -= 1
    end = index
    while end + 1 < len(lines) and (not lines[end + 1].strip() or _indent(lines[end + 1]) >= level):
        end += 1
    return lines[start : end + 1]


def _workflow_lines(after: str, added: list[tuple[int, str]]) -> Iterator[_Hit]:
    lines = after.splitlines()
    for number, text in added:
        if not (ALLOWED_TO_FAIL.match(text) or DISABLED.match(text)):
            continue
        if not any(is_test_command(t) for t in _block(lines, number - 1)):
            continue
        if ALLOWED_TO_FAIL.match(text):
            yield "TR402", Level.CAUGHT, number, f"a test job may now fail: `{text.strip()}`"
        else:
            yield "TR405", Level.CAUGHT, number, f"a test step is disabled: `{text.strip()}`"


def _guard_lines(
    after: str, removed: list[tuple[int, str]], added: list[tuple[int, str]]
) -> Iterator[_Hit]:
    """testreceipt's own step removed, changed or allowed to fail. Adding it is fine."""
    for number, text in removed:
        if "testreceipt" in text:
            yield "TR406", Level.CAUGHT, number, f"testreceipt's set-up changed: `{text.strip()}`"
            return
    lines = after.splitlines()
    for number, text in added:
        if ALLOWED_TO_FAIL.match(text) or DISABLED.match(text) or IGNORE_FAILURE.search(text):
            block = _block(lines, number - 1) if lines else []
            if "testreceipt" in text or any("testreceipt" in t for t in block):
                yield (
                    "TR406",
                    Level.CAUGHT,
                    number,
                    f"testreceipt's step weakened: `{text.strip()}`",
                )
                return


def _thresholds(
    removed: list[tuple[int, str]], added: list[tuple[int, str]], *, codecov: bool
) -> Iterator[_Hit]:
    pattern = CODECOV_TARGET if codecov else THRESHOLD
    old = [float(m.group(1)) for _, t in removed if (m := pattern.search(t))]
    new = [(float(m.group(1)), n) for n, t in added if (m := pattern.search(t))]
    for before, (after, number) in zip(old, new, strict=False):
        if after < before:
            message = f"coverage threshold lowered from {before:g} to {after:g}"
            yield "TR404", Level.CAUGHT, number, message


# --- pytest configuration, read in full --------------------------------------------------------

_LIST_KEYS = ("testpaths", "python_files", "python_classes", "python_functions")


def _pytest_options(path: str, text: str | None) -> dict[str, list[str]] | None:
    """pytest's options in a configuration file; None when the file cannot be read."""
    if not text:
        return {}
    name = PurePosixPath(path).name
    try:
        if name == "pyproject.toml":
            tool = tomllib.loads(text).get("tool", {})
            pytest = tool.get("pytest", {})
            options = pytest.get("ini_options", pytest)
            return {str(k): _as_list(k, v) for k, v in options.items()}
        parser = configparser.ConfigParser(interpolation=None, strict=False)
        parser.read_string(text)
    except (tomllib.TOMLDecodeError, configparser.Error, AttributeError, ValueError):
        return None
    section = {"setup.cfg": "tool:pytest"}.get(name, "pytest")
    if not parser.has_section(section):
        return {}
    return {k: (_tokens(v) if k == "addopts" else v.split()) for k, v in parser.items(section)}


def _as_list(key: object, value: object) -> list[str]:
    if isinstance(value, list):
        return [str(v) for v in value]
    if isinstance(value, str):
        return _tokens(value) if key == "addopts" else value.split()
    return [str(value)]


def _pytest_config(change: FileChange) -> Iterator[_Hit]:
    old = _pytest_options(change.path, change.before)
    new = _pytest_options(change.path, change.after)
    if old is None or new is None:
        return
    for rule, level, message in _option_hits(old.get("addopts", []), new.get("addopts", [])):
        yield rule, level, None, f"{message} (pytest `addopts`)"
    for key in _LIST_KEYS:
        lost = [v for v in old.get(key, []) if v not in new.get(key, [])]
        if lost and key in new:
            yield "TR403", Level.SUSPICIOUS, None, f"`{key}` no longer includes {', '.join(lost)}"
    gained = [v for v in new.get("norecursedirs", []) if v not in old.get("norecursedirs", [])]
    if gained:
        yield "TR403", Level.SUSPICIOUS, None, f"`norecursedirs` now leaves out {', '.join(gained)}"
