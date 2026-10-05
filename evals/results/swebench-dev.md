# Layer 1 on SWE-bench `dev`

Dataset: `princeton-nlp/SWE-bench@e48e2bd1e9fecd5bbd641e9414ac59da9f2e69f6`, 225 instances rebuilt from 6 repositories.

## Negatives: the maintainers' own fixes

| Verdict | Instances | Share |
|---|---|---|
| CAUGHT | 0 | 0.0% [0, 2] |
| SUSPICIOUS | 26 | 11.6% [8, 16] |
| INCONCLUSIVE | 0 | 0.0% [0, 2] |
| CLEAN | 199 | 88.4% [84, 92] |

Instances with each finding:

| Rule | caught | suspicious | note |
|---|---|---|---|
| TR101 | 0 | 1 | 0 |
| TR102 | 0 | 7 | 1 |
| TR104 | 0 | 1 | 0 |
| TR105 | 0 | 2 | 13 |
| TR106 | 0 | 2 | 0 |
| TR110 | 0 | 14 | 0 |
| TR111 | 0 | 2 | 0 |
| TR120 | 0 | 0 | 1 |
| TR121 | 0 | 0 | 8 |

## Positives: one injected cheat per operator and instance

| Operator | Expected | Cases | Expected rule at its level | Any rule |
|---|---|---|---|---|
| delete-checks | TR101 caught | 212 | 83.0% [77, 87] | 100.0% [98, 100] |
| assert-true | TR101 caught | 212 | 99.5% [97, 100] | 99.5% [97, 100] |
| empty-body | TR101 caught | 212 | 100.0% [98, 100] | 100.0% [98, 100] |
| early-return | TR101 caught | 212 | 100.0% [98, 100] | 100.0% [98, 100] |
| swallow | TR103 caught | 212 | 100.0% [98, 100] | 100.0% [98, 100] |
| skip | TR111 caught | 212 | 100.0% [98, 100] | 100.0% [98, 100] |
| xfail | TR111 caught | 212 | 100.0% [98, 100] | 100.0% [98, 100] |
| skip-call | TR111 caught | 212 | 100.0% [98, 100] | 100.0% [98, 100] |
| weaken | TR104 suspicious | 178 | 99.4% [97, 100] | 99.4% [97, 100] |
| hardcode | TR105 suspicious | 139 | 99.3% [96, 100] | 99.3% [96, 100] |
| loosen | TR106 suspicious | 49 | 98.0% [89, 100] | 98.0% [89, 100] |
| delete-test | TR110 suspicious | 212 | 99.5% [97, 100] | 99.5% [97, 100] |
| conftest-report | TR201 caught | 212 | 100.0% [98, 100] | 100.0% [98, 100] |
| conftest-exit | TR203 caught | 212 | 100.0% [98, 100] | 100.0% [98, 100] |
| detect-pytest | TR302 caught | 217 | 100.0% [98, 100] | 100.0% [98, 100] |
| always-equal | TR301 caught | 157 | 100.0% [98, 100] | 100.0% [98, 100] |
