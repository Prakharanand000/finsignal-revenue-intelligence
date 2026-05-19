"The agent initially asserted the bronze columns were case-insensitive. I had it verify empirically before building on the assumption — it discovered they were quoted-lowercase identifiers from write_pandas and corrected all model SQL to use quoted references. Catching that before dbt run saved a full debug cycle."

Silver validation: dedup confirmed empirically (31,469 → 30,852 invoices, 617 rows = ~2% duplicate rate removed via ROW_NUMBER() window partition; zero duplicate invoice_ids remained). Null tiers preserved-and-flagged (300 of 31,346, ~1%) rather than dropped, preventing silent ARR understatement.

ARR Movement Model — Design Decisions and Lessons
Initial build classified billing noise (±10% MRR jitter) as expansion/contraction events, producing ~14,000 false movements on 2,000 customers. Real ARR movement is driven by plan tier changes, not billing variance. Rebuilt using fixed tier-based ARR (Starter $2,400 / Growth $14,400 / Enterprise $72,000) so only actual tier transitions generate movement rows. Final counts: 159 real expansions, 61 real contractions across 3 fiscal years — plausible for the simulated 8% annual expansion rate.
ARR bridge identity (Beginning + New + Reactivation + Expansion − Contraction − Churn = Ending) holds within ~1% at the quarterly level. Small residuals arise from intra-quarter round-trips: customers who are both "new" and "churned" within the same fiscal quarter appear in both movement buckets but the quarter-end snapshot captures only their final state. This is a known property of monthly-grain movement tables verified against quarterly snapshots, not a model error.

## What This Project Demonstrates

### CoCo / Cortex Code Usage
Built entirely through Cortex Code (Snowsight agent + CLI), ~[N] logged
sessions across [dates]. The agent self-corrected a quoted-identifier
assumption mid-build, caught a fiscal-quarter labeling error in my own
spec, and recovered from 2 runtime errors in the data generator without
intervention. Session log: cortex_session_log.md.

### Fiscal Year / Earnings Cycle Ownership
Implemented a Feb-1 fiscal calendar (FY ≠ calendar year). Built a
quarter-close routine that validates, snapshots, and exports a formatted
IR-style Excel pack for any fiscal quarter. Verified the ARR bridge
identity (Beginning + New + Reactivation + Expansion − Contraction −
Churn = Ending) holds within ~1% — residuals from intra-quarter
round-trips, not model errors.

### Finance Domain Vocabulary — Implemented, Not Listed
- ARR movement classification: caught and fixed a bug where ±10% billing
  noise was masquerading as 14,000 false expansion/contraction events.
  Rebuilt on fixed tier-based ARR so only real tier transitions generate
  movement rows (159 real expansions vs 14,277 false ones).
- NRR cohort model: tracks existing customers forward from their signup
  quarter, excluding new logos, so NRR reflects true retention.
- Revenue waterfall: quarterly ARR bridge with QoQ growth %, visible
  churn spike in FY2026-Q3 (the deliberately seeded bad quarter).

### Key Design Decisions
- Bronze quoted-lowercase identifiers from write_pandas normalized in
  silver staging layer — first thing dbt models do.
- NULL plan_tier rows (~1%) flagged with is_missing_tier boolean, not
  dropped — prevents silent ARR understatement.
- 617 duplicate invoice rows removed via ROW_NUMBER() window dedup,
  verified empirically (31,469 → 30,852).