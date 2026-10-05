---
name: testreceipt
description: Report test results so they can be checked. Use whenever you are about to say that tests pass, fail or were run, in a message, a commit message or a pull request description.
---

# Reporting test results

People and tools check "all tests pass" against what the tests did. Say exactly what ran and what it
showed.

1. **Run the tests after your last change, before you say anything about them.** A run from before
   an edit does not cover the edit.
2. **Name the command and quote the runner's summary line**, as printed:

   > Ran `python -m pytest -q`: `312 passed, 2 skipped in 41.3s`

3. **Say what the run covered.** If you ran a subset (one package, one file, the new tests, one
   platform), say so, and do not write "all tests pass":

   > Ran `pytest tests/parser -q`: `53 passed`. The full suite was not run.

4. **Report failures as failures**, including ones you believe were already there, with the names
   of the failing tests:

   > `pytest -q`: `2 failed, 310 passed`. `test_cache_expiry` and `test_retry` also fail on `main`.

5. **Never edit, skip or loosen a test to make a run pass** without saying so and why. A skip needs
   a reason a reviewer would accept: say which environment lacks what.

The testreceipt Stop hook checks the last turn: a claim that tests pass is sent back once if the
last test run in the session failed, ran before the last code edit, or never happened.
