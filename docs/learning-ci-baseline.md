# Learning CI baseline and regression policy

The frozen baseline `ci/baselines/learning-2026-10-19.json` preserves every one of the653 findings from original validator/source commitd8b72fab79c61d9ec8814f513483b63f73a908f7. The full ordered inventory is pinned by SHA256 in `scripts/learning_regression_gate.py`. No baseline-regeneration command or additive allowlist exists. The offline test `test_frozen_653_inventory_reproduces_from_original_git_commit` extracts original source and learning data from Git and reproduces the exact ordered list and validator hash. CI fetches full history to make this reproducible.

These are **pre-v2 findings**, not653 newly failing current-rule checks. Main6a984cf already approved AGENTS72–74 and validator v2, which recognizes operational entries/Brain attribution and permits four enumerated historical warnings. We retain that upstream governance unchanged. CI separately runs the current validator with its unmodified fatal exit behavior. It reports four warnings; exceptions are never silently expanded.

The additional gate verifies:

- exact hash of the baseline, current approved validator, exception file, existing learning schemas and historical rule files;
- exact original bytes of frozen ledger and lineage prefixes, including all approved records present when this baseline was created;
- append-only ledger and lineage against the full trusted **PR base SHA** or **push-before SHA**, so records added in future merges remain immutable too;
- current validation exit status and exact warning identities/multiplicity, so a new malformed review using an old exception ID cannot disappear into the old warning count;
- strict JSON and confidence type on appended events, and required fields on appended Pulse relationships.

Valid new decisions and valid outcome reviews of grandfathered decisions are permitted under v2. Invalid reviews, duplicate decisions, historical edits/deletions, new exceptions, additional warnings and newly malformed records fail. Frozen findings never substitute for current validation. Improvements must be append-only evidence/reviews; no hindsight rewriting. A deliberate future validator/schema evolution requires explicit reviewed baseline/code changes, not automatic rebaselining. GitHub protections and review remain the control over deliberately changing both code and pins.

Run `python scripts/learning_regression_gate.py --comparison-ref <exact-base-SHA> --report-dir /tmp/learning-report`; without a comparison ref, local HEAD is used. CI supplies the actual event's base/before SHA, never a user-entered reference. `validate.yml` runs all offline tests and both Sparta/current-learning validators, prints every historical finding and preserves the complete report as a private30-day Actions artifact. Reporting steps use always() but cannot turn a failed prior step green.

No historical decisions, transactions, FAAB, Yahoo artifacts or Pulse cursors are modified by this work. Four grandfathered warnings remain visible and unresolved as evidence gaps. This gate enforces existing structural checks; it is not proof that every recommendation was correct or that every historical source is complete.
