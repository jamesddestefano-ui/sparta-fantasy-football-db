# FantasyPros NFL API — Sparta read-only pilot

Scope: Billy's 2026 Sparta league only. This integration is NFL research intelligence, **not** Yahoo ownership, transaction, lineup, waiver, or FAAB authority. It must never alter immutable decision records or NFL Pulse lineage.

## Authentication

Use a newly rotated FantasyPros API key in the `FANTASYPROS_API_KEY` environment variable. Never paste the key into GitHub, a committed file, workflow YAML, a command-line argument, a screenshot, or an output artifact. Do not commit `.env` files.

## Pilot execution

Run only after setting the environment variable securely:

```bash
python -m unittest discover -s tests -p 'test_fantasypros_ingest.py'
python scripts/fantasypros_ingest.py --season 2026 --week 6 --output-dir /tmp/sparta-fantasypros-review
```

The pilot makes **three requests**, one each for NFL PPR consensus FLEX rankings, NFL player projections, and NFL injuries. Confirm that the key's quota permits them before running. No recurring collection is enabled. Results are written only to the specified local output directory, marked `unvalidated_for_decisions`, and must be reviewed before use. No automatic GitHub commit occurs.

The pilot deliberately fails closed if authentication, network access, JSON parsing, season/week checks, or expected result arrays fail. Error messages omit credentials and response bodies.

## Next validation

1. Set a rotated credential securely in a trusted execution environment with outbound HTTPS.
2. Execute the three read-only requests and verify HTTP 200 and nonempty, correctly scoped payloads.
3. Cross-check the player identity mapping and dates against authenticated Sparta Yahoo data and independent NFL injury reports.
4. Evaluate projection calibration without changing decision weights from a single result.
5. Only after successful review consider a **manual**, secret-backed GitHub Actions workflow. Never enable a scheduled workflow without quota approval.

The attempted GitHub Actions workflow creation on October 17, 2026 was blocked by connector safety checks; **no workflow was installed**.
