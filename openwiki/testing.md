---
type: "Reference"
title: "Testing and Validation"
description: "Manual validation strategy for a repo with no formal test suite, covering backend API, frontend build/lint, low-stock script, and the risk areas where tracking-type logic is split across three components."
tags: ["testing", "validation", "backend", "frontend", "manual-verification"]
verified:
  - by: openwiki/0.5.1
    at: 2026-09-11T18:21:42.744Z
sources:
  - id: openwiki-source-76524f4e00c120c9aa9c9390
    resource: repo://create_tables.py
  - id: openwiki-source-1047363cf615000e4c9bb694
    resource: repo://frontend/package.json
  - id: openwiki-source-49b284af4abdb5084d5b9d09
    resource: repo://frontend/src/App.jsx
  - id: openwiki-source-c1b3e89d74bd2715617287c8
    resource: repo://frontend/src/DeductModal.jsx
  - id: openwiki-source-1c255feabbe58b8055271a72
    resource: repo://frontend/src/RestockModal.jsx
  - id: openwiki-source-833e692518af9eeaf8564cc6
    resource: repo://main.py
  - id: openwiki-source-47aa29ed50b918e91518a4a7
    resource: repo://models.py
  - id: openwiki-source-7ed2d9b3005cd559f37189d1
    resource: repo://scripts/low_stock.py
generated: { by: "openwiki/0.5.1", at: "2026-09-11T18:21:42.744Z" }
---

# Testing and Validation

## What exists today

The repository has **no formal Python test suite**. No `test_*.py`, `*_test.py`, or `conftest.py` files exist anywhere in the tree, and no test runner is configured. There is no frontend test harness either — `frontend/package.json` defines only `dev`, `build`, `lint`, and `preview` scripts, none of which execute assertions. As a result, every change is validated by running the application and its build/lint commands rather than by an automated suite.

Because there are no regression guards, the safest stance is the AGENTS.md rule applied locally: choose the narrowest quiet check that proves the *changed* behavior, while preserving the *complete* failure output so a genuine breakage is not hidden behind a filtered summary.

## Backend validation

Run from the repo root:

1. Start the API with `uvicorn main:app --reload`.
2. Exercise the affected endpoints manually. The endpoints that carry real branching logic, and therefore the most likely to regress, are:
   - `POST /scan` — weight vs unit deduction (FIFO over `expiry_date`), `stock_mismatch` vs `completed` status, and the movement record.
   - `POST /deduct` — weight vs unit deduction with its own FIFO loop and `stock_mismatch` status.
   - `POST /batches` — restock, which also writes the inbound `StockMovement`.
3. If schema creation changed, run `python create_tables.py` against a **disposable** database (point `DATABASE_URL` at a throwaway DB). `create_tables.py` calls `Base.metadata.create_all(bind=engine)` and prints `Tables created successfully!`, so it both recreates tables and confirms the models import cleanly.

Validate requests and responses against `schemas.py`. The Pydantic models enforce the non-trivial invariants the handlers rely on — for example `BatchCreate.check_quantity` and `ProductDeduct.check_quantity` reject payloads where both `grams`/`grams_remaining` and `units`/`units_remaining` are `None`. A schema change here changes what the API accepts, so re-check the corresponding handler and modal together.

## Frontend validation

Run from `frontend/` using the scripts declared in `frontend/package.json`:

- `npm run build` (`vite build`) — compiles and bundles the React app; this is the hard gate that catches type/import errors before deployment. The built `frontend/dist` is what `main.py` serves via `app.frontend("/", directory="frontend/dist")`, so a passing build is also a deployability check.
- `npm run lint` (`oxlint`) — the configured linter; run it to catch surface-level regressions in changed files.
- `npm run dev` (`vite`) — start the dev server for manual checks against a running backend (CORS in `main.py` allows `http://localhost:5173`).

## Low-stock script validation

`scripts/low_stock.py` reads `GMAIL_ADDRESS` and `GMAIL_PASSWORD` from the environment, queries outbound movements from the last week, computes days-of-stock-left per variety, and either sends a Gmail warning or prints `No low stocks detected`. Validate it in an environment with a reachable `DATABASE_URL` and Gmail credentials:

- `python scripts/low_stock.py` — run it directly.
- Confirm the happy path first: when no variety falls below the 5-days-left threshold it prints exactly `No low stocks detected` and sends nothing.

This script depends on `StockMovement.grams` (see the risk-area note below), so any change to how movements are recorded must be re-validated here as well as in the backend.

## Risk-area checklist

These are the non-obvious couplings where a localized edit silently breaks a distant component. Work through the relevant items whenever the corresponding area changes.

### API payload or tracking-type branching changes

The business logic for weight-based vs unit-based stock is split across **three** places that must be validated together:

1. **Backend handler** (`main.py`) — `POST /scan` and `POST /deduct` branch on `variety.tracking_type == TrackingType.WEIGHT` and return different response shapes (`grams_removed` vs `units_removed`, plus `stock_shortfall`/`status`).
2. **Matching frontend modal** — `RestockModal.jsx` (posts `grams_remaining`/`units_remaining` to `/batches`) and `DeductModal.jsx` (posts `grams`/`units` to `/deduct`). Both switch their visible field and request body on `tracking_type === "weight"` vs `"units"`.
3. **Dashboard rendering** (`App.jsx`) — `VarietySection` and `BatchRow` branch on `tracking_type === "weight"` to choose `grams_remaining` vs `units_remaining` and to format the totals/labels; `handleScanSubmit` displays the response assuming the weight path (`Removed ${data.grams_removed}g`).

If you change an API payload field name, a status string, or which branch a tracking type takes, all three must be checked together: a mismatch in any one produces silent UI breakage (wrong label, missing field, or a stale message) with no test to catch it.

### StockMovement.grams overload

`StockMovement.grams` is a single integer column that is **overloaded** by tracking type — it stores grams for weight movements and a **unit count** for unit movements:

- `POST /scan` unit branch writes `grams=1` for one unit removed; the weight branch writes `grams=product.package_size_grams`.
- `POST /deduct` unit branch writes `grams=units_removed` (the computed unit count), not grams.
- `POST /batches` writes `grams=grams_remaining` for weight batches and `grams=units_remaining` for unit batches.

Two consumers depend on this overloaded field:

- The **audit trail** — every inbound/outbound event is a `StockMovement` row, so the meaning of `grams` must stay consistent with whatever the handlers write.
- The **low-stock script** — `scripts/low_stock.py` sums `movement.grams` for outbound movements over the last week to compute weekly consumption, then divides remaining stock by it to estimate days left.

Changing how movements are recorded therefore affects **both** the audit trail and the low-stock consumption calculation. Any edit to the value written to `grams` (e.g. switching a unit branch to write a different field) must be validated by re-running the backend deduction, inspecting a saved `StockMovement` row, and re-running `scripts/low_stock.py` to confirm its days-left math is unchanged.

### FIFO deduction order

Both `POST /scan` (weight branch) and `POST /deduct` iterate batches ordered by `Batch.expiry_date` ascending, subtracting from the soonest-expiring batch first. Validate FIFO explicitly:

1. Create multiple batches for the same weight variety with **different expiry dates** (earliest-expiring first on the shelf).
2. Perform a deduction smaller than the first batch's `grams_remaining`.
3. Confirm the earliest-expiring batch is reduced and the later batches are untouched.
4. Perform a deduction larger than the first batch; confirm the first is zeroed, the overflow comes off the next batch in expiry order, and a `stock_mismatch`/shortfall is reported only when all batches are exhausted.

The unit branches use the same `expiry_date` ordering, so repeat the check for a `units` variety via `/deduct`.

### Dashboard data refresh

`App.jsx` polls `/varieties` and `/batches` every 10 seconds (`setInterval(loadData, 10000)`) and also calls `loadData()` immediately after a scan, restock, or deduct succeeds. After any scan/restock/removal action, verify the dashboard reflects the new totals without a manual reload — this is the only feedback that a write + re-fetch chain is intact.

### Deployment / static serving

`main.py` mounts the built frontend at `/` from `frontend/dist`. If you change the build output or the mount path, confirm a production-style run (`uvicorn main:app` against a freshly built `frontend/dist`) still serves the app correctly — a `vite build` that succeeds is necessary but not sufficient if the served directory or route differs.

## Practical rule

If you change any API payload or any tracking-type branch, validate the matching frontend modal, the backend handler, and the rendered dashboard together — the business logic is split across all three and no test guards the seam. Pair each such change with a re-run of `scripts/low_stock.py` whenever the change touches how `StockMovement.grams` is written, because the low-stock consumption calculation and the audit trail both read that overloaded field.
