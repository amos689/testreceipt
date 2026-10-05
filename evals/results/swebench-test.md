# Layer 1 on SWE-bench `test`

Dataset: `princeton-nlp/SWE-bench@e48e2bd1e9fecd5bbd641e9414ac59da9f2e69f6`, 2292 instances rebuilt from 12 repositories.

## Negatives: the maintainers' own fixes

| Verdict | Instances | Share |
|---|---|---|
| CAUGHT | 4 | 0.2% [0, 0] |
| SUSPICIOUS | 158 | 6.9% [6, 8] |
| INCONCLUSIVE | 0 | 0.0% [0, 0] |
| CLEAN | 2130 | 92.9% [92, 94] |

Instances with each finding:

| Rule | caught | suspicious | note |
|---|---|---|---|
| TR101 | 3 | 0 | 0 |
| TR102 | 0 | 67 | 4 |
| TR104 | 0 | 8 | 0 |
| TR105 | 0 | 8 | 249 |
| TR106 | 0 | 2 | 0 |
| TR110 | 0 | 72 | 0 |
| TR111 | 1 | 8 | 0 |
| TR112 | 0 | 5 | 0 |
| TR120 | 0 | 0 | 7 |
| TR121 | 0 | 0 | 90 |
| TR304 | 0 | 3 | 0 |

## Positives: one injected cheat per operator and instance

| Operator | Expected | Cases | Expected rule at its level | Any rule |
|---|---|---|---|---|
| delete-checks | TR101 caught | 2251 | 85.2% [84, 87] | 99.8% [100, 100] |
| assert-true | TR101 caught | 2251 | 100.0% [100, 100] | 100.0% [100, 100] |
| empty-body | TR101 caught | 2251 | 99.6% [99, 100] | 99.6% [99, 100] |
| early-return | TR101 caught | 2251 | 99.7% [99, 100] | 99.7% [99, 100] |
| swallow | TR103 caught | 2251 | 99.7% [99, 100] | 99.7% [99, 100] |
| skip | TR111 caught | 2251 | 99.8% [99, 100] | 99.8% [99, 100] |
| xfail | TR111 caught | 2251 | 100.0% [100, 100] | 100.0% [100, 100] |
| skip-call | TR111 caught | 2251 | 99.7% [99, 100] | 99.9% [100, 100] |
| weaken | TR104 suspicious | 1269 | 99.3% [99, 100] | 99.4% [99, 100] |
| hardcode | TR105 suspicious | 990 | 98.5% [98, 99] | 98.5% [98, 99] |
| loosen | TR106 suspicious | 345 | 96.2% [94, 98] | 96.5% [94, 98] |
| delete-test | TR110 suspicious | 2251 | 99.1% [99, 99] | 99.1% [99, 99] |
| conftest-report | TR201 caught | 2251 | 100.0% [100, 100] | 100.0% [100, 100] |
| conftest-exit | TR203 caught | 2251 | 100.0% [100, 100] | 100.0% [100, 100] |
| detect-pytest | TR302 suspicious | 2226 | 94.7% [94, 96] | 94.7% [94, 96] |
| always-equal | TR301 caught | 2055 | 94.6% [94, 95] | 94.6% [94, 95] |
