"""The rules, by ID. Each module checks one kind of file; `check.py` runs them all."""

from __future__ import annotations

TITLES: dict[str, str] = {
    # tests
    "TR101": "assertions neutralised",
    "TR102": "assertions removed",
    "TR103": "assertion failures swallowed",
    "TR104": "assertion weakened",
    "TR105": "expected value changed",
    "TR106": "tolerance loosened",
    "TR110": "tests removed",
    "TR111": "tests skipped or marked xfail",
    "TR112": "parametrized cases removed",
    "TR120": "mocks added",
    "TR121": "new test checks nothing",
    # test infrastructure
    "TR201": "test reports rewritten",
    "TR202": "test collection narrowed",
    "TR203": "test process exits early",
    # production code
    "TR301": "comparison that always succeeds",
    "TR302": "code detects the test run",
    "TR303": "code reads the tests",
    "TR304": "test-mode switch",
    # CI and configuration
    "TR401": "test failures ignored",
    "TR402": "test job allowed to fail",
    "TR403": "test selection narrowed",
    "TR404": "coverage threshold lowered",
    "TR405": "test step removed or disabled",
    "TR406": "testreceipt's own configuration changed",
}
