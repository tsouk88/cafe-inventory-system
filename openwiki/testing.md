---
type: "Reference"
title: "Testing and Validation"
description: "Manual validation strategy for a repo with no formal test suite, covering backend API, report endpoints, frontend build/lint, Reports.jsx, low-stock script, and the risk areas where tracking-type logic and raw-SQL reports are split across components."
tags: ["testing", "validation", "backend", "frontend", "reports", "manual-verification"]
sources:
  - id: openwiki-source-76524f4e00c120c9aa9c9390
    resource: repo://create_tables.py
  - id: openwiki-source-1047363cf615000e4c9bb694
    resource: repo://frontend/package.json
  - id: openwiki-source-49b284af4abdb5084d5b9d09
    resource: repo://frontend/src/App.jsx
  - id: openwiki-source-c1b3e89d74bd2715617287c8
    resource: repo://frontend/src/DeductModal.jsx
  - id: openwiki-source-e828310cceb581a07cef2a85
    resource: repo://frontend/src/Reports.jsx
  - id: openwiki-source-1c255feabbe58b8055271a72
    resource: repo://frontend/src/RestockModal.jsx
  - id: openwiki-source-833e692518af9eeaf8564cc6
    resource: repo://main.py
  - id: openwiki-source-47aa29ed50b918e91518a4a7
    resource: repo://models.py
  - id: openwiki-source-7ed2d9b3005cd559f37189d1
    resource: repo://scripts/low_stock.py
generated: { by: "openwiki/0.6.1", at: "2026-10-01T12:43:49.948Z" }
verified:
  - by: openwiki/0.6.1
    at: 2026-10-01T12:43:49.948Z
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

## Reports endpoint validation

The four report endpoints return **raw SQL result rows**, not Pydantic-validated models:

- `GET /reports/stock-per-variety` — `name`, `remaining`, `active_batches`, `tracking_type`.
- `GET /reports/fefo-next` — `name`, `min_expiry`, `remaining` (the soonest non-expired batch with stock).
- `GET /reports/expired-with-stock` — `name`, `tracking_type`, `stock`, `expired_at`.
- `GET /reports/last7` — `name`, `timestamp`, `direction`, `stock` (movements from the last 7 days).

None of these declare a `response_model`, so FastAPI performs no schema coercion. Each handler executes hand-written SQL via `text(...)` and returns `.mappings().all()` directly — a list of dict-like rows. This means a change to the SQL or to the underlying tables will **not** be caught by a response-model mismatch; it can only be caught by inspecting the response body. Validate each report by calling the endpoint directly and confirming both the column set and the rows:

1. With a known dataset, `curl http://localhost:8000/reports/stock-per-variety` and verify each variety's `remaining` matches `sum(coalesce(units_remaining, grams_remaining))` over its active batches, and `active_batches` is the count of batches with positive remaining stock.
2. `curl /reports/fefo-next` and confirm the returned `min_expiry` per variety is the earliest `expiry_date > now()` among batches with positive stock, ordered ascending.
3. `curl /reports/expired-with-stock` and confirm only batches with `expiry_date < now()` and positive stock appear, ordered by `expired_at` descending.
4. `curl /reports/last7` and confirm only movements newer than 7 days appear, newest first, with `stock` reading the `grams` column.

> **Known issue — `timestamp` column reference.** `/reports/last7` selects `s.timestamp` and filters `s.timestamp > now() - interval '7 days'`, but `models.py` defines the `StockMovement` timestamp column as `received_at` — there is no `stock_movements.timestamp` column. The same discrepancy appears in `scripts/low_stock.py`, which filters on `StockMovement.timestamp`. Until the column is renamed to `timestamp` (or the query/script switch to `received_at`), expect `/reports/last7` to fail with a SQL error and `low_stock.py` to raise an `AttributeError`. This must be validated before relying on either path.

## Frontend validation

Run from `frontend/` using the scripts declared in `frontend/package.json`:

- `npm run build` (`vite build`) — compiles and bundles the React app; this is the hard gate that catches type/import errors before deployment. The built `frontend/dist` is what `main.py` serves via `app.frontend("/", directory="frontend/dist")`, so a passing build is also a deployability check.
- `npm run lint` (`oxlint`) — the configured linter; run it to catch surface-level regressions in changed files.
- `npm run dev` (`vite`) — start the dev server for manual checks against a running backend (CORS in `main.py` allows `http://localhost:5173`).

### Reports.jsx component validation

`Reports.jsx` renders all four report endpoints as tables in a single view, driven by a `REPORTS` array where each entry binds a `path` to a `columns` definition. To validate it:

1. Run `npm run build` to confirm the component compiles (it imports only `react`, so the build also catches any JSX/syntax regression).
2. With the backend running, toggle the dashboard to the reports view — the "Reports" button in `App.jsx` flips `view` between `"stock"` and `"reports"`, mounting `<Reports />`.
3. Confirm all four tables render with the correct columns and data:
   - **Stock per variety** — Variety / Remaining (with `g` or ` units` suffix) / Active batches.
   - **Next batch to use (FEFO)** — Variety / Expires (date) / Remaining.
   - **Expired batches still in stock** — Variety / Expired (date) / Remaining (with `g` or ` units` suffix).
   - **Movements, last 7 days** — When (date-time) / Variety (`—` when null) / Direction / Qty.
4. Confirm the empty/loading/error states: each `ReportTable` shows `Loading...` while fetching, `No rows.` when the endpoint returns `[]`, and an error banner when the fetch fails (which is how a failing `/reports/last7` surfaces in the UI).

## Low-stock script validation

`scripts/low_stock.py` reads `GMAIL_ADDRESS` and `GMAIL_PASSWORD` from the environment, queries outbound movements from the last week, computes days-of-stock-left per variety, and either sends a Gmail warning or prints `No low stocks detected`. Validate it in an environment with a reachable `DATABASE_URL` and Gmail credentials:

- `python scripts/low_stock.py` — run it directly.
- Confirm the happy path first: when no variety falls below the 5-days-left threshold it prints exactly `No low stocks detected` and sends nothing.

This script depends on `StockMovement.grams` (see the risk-area note below), so any change to how movements are recorded must be re-validated here as well as in the backend.

> **Known issue — `StockMovement.timestamp` reference.** `low_stock.py` filters `StockMovement.timestamp >= datetime.now(timezone.utc) - timedelta(weeks=1)`, but `models.py` names that column `received_at`. The script will raise an `AttributeError` at runtime unless the model is changed to expose `timestamp` or the query is updated to use `received_at`. Validate this before treating the script as functional.

## Risk-area checklist

These are the non-obvious couplings where a localized edit silently breaks a distant component. Work through the relevant items whenever the corresponding area changes.

### API payload or tracking-type branching changes

The business logic for weight-based vs unit-based stock is split across **three** places that must be validated together:

1. **Backend handler** (`main.py`) — `POST /scan` and `POST /deduct` branch on `variety.tracking_type == TrackingType.WEIGHT` and return different response shapes (`grams_removed` vs `units_removed`, plus `stock_shortfall`/`status`).
2. **Matching frontend modal** — `RestockModal.jsx` (posts `grams_remaining`/`units_remaining` to `/batches`) and `DeductModal.jsx` (posts `grams`/`units` to `/deduct`). Both switch their visible field and request body on `tracking_type === "weight"` vs `"units"`.
3. **Dashboard rendering** (`App.jsx`) — `VarietySection` and `BatchRow` branch on `tracking_type === "weight"` to choose `grams_remaining` vs `units_remaining` and to format the totals/labels; `handleScanSubmit` displays the response assuming the weight path (`Removed ${data.grams_removed}g`).

If you change an API payload field name, a status string, or which branch a tracking type takes, all three must be checked together: a mismatch in any one produces silent UI breakage (wrong label, missing field, or a stale message) with no test to catch it.

### Reports subsystem (endpoints + Reports.jsx)

The reports layer has its own split across **two** places that must be validated together:

1. **Backend report endpoints** (`main.py`) — four `GET /reports/*` handlers execute raw SQL and return `.mappings().all()` with **no `response_model`**. The column names in each query are the contract: `Reports.jsx` reads exactly those keys.
2. **Reports.jsx** — the `REPORTS` array binds each endpoint `path` to a fixed `columns` list of `{ key, label, format }`. The `key` must match the SQL column name exactly, or the cell renders `undefined`.

Specific couplings to check when a report SQL statement or the `REPORTS` table config changes:

- **Column-name parity** — if a report query renames a column (e.g. `remaining` → `qty`), the matching `key` in `Reports.jsx` must be updated or the cell goes blank with no error.
- **`isWeight()` casing normalization** — the `isWeight(row)` helper does `String(row.tracking_type).toLowerCase() === "weight"`. Raw-SQL report endpoints return the enum as stored in the DB (`"WEIGHT"`), while ORM-backed endpoints elsewhere return `"weight"`. This normalization is the only thing keeping the `g` vs ` units` suffix correct in the *Stock per variety* and *Expired batches* tables. If a new report is added that includes `tracking_type`, or if the SQL changes how the enum is selected, verify `isWeight()` still resolves correctly for both casings.
- **No response-model safety net** — because the endpoints return raw dict rows, a dropped or renamed column produces a silent `undefined` cell in the UI, not a validation error. Validate by inspecting the raw JSON response, not just the rendered table.

### StockMovement.grams overload

`StockMovement.grams` is a single integer column that is **overloaded** by tracking type — it stores grams for weight movements and a **unit count** for unit movements:

- `POST /scan` unit branch writes `grams=1` for one unit removed; the weight branch writes `grams=product.package_size_grams`.
- `POST /deduct` unit branch writes `grams=units_removed` (the computed unit count), not grams.
- `POST /batches` writes `grams=grams_remaining` for weight batches and `grams=units_remaining` for unit batches.

Two consumers depend on this overloaded field:

- The **audit trail** — every inbound/outbound event is a `StockMovement` row, so the meaning of `grams` must stay consistent with whatever the handlers write.
- The **low-stock script** — `scripts/low_stock.py` sums `movement.grams` for outbound movements over the last week to compute weekly consumption, then divides remaining stock by it to estimate days left. The `/reports/last7` endpoint also exposes this same `grams` value as the `stock` column.

Changing how movements are recorded therefore affects **both** the audit trail and the low-stock consumption calculation. Any edit to the value written to `grams` (e.g. switching a unit branch to write a different field) must be validated by re-running the backend deduction, inspecting a saved `StockMovement` row, and re-running `scripts/low_stock.py` to confirm its days-left math is unchanged.

### received_at vs timestamp discrepancy

`models.py` defines the movement timestamp column as `received_at` on both `Batch` and `StockMovement`, but two consumers reference a `timestamp` attribute/column that does not exist:

- `scripts/low_stock.py` filters `StockMovement.timestamp >= ...` — this raises an `AttributeError` at runtime.
- `/reports/last7` selects and filters on `s.timestamp` — this fails with a SQL error against the `stock_movements` table.

If the column is renamed to `timestamp`, or if both consumers are fixed to use `received_at`, re-validate: run `low_stock.py` end-to-end, call `/reports/last7` and confirm rows, and confirm the `Reports.jsx` *Movements, last 7 days* table still renders its `When` column. Until then, treat both as broken and note the failure explicitly.

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

If you change any API payload or any tracking-type branch, validate the matching frontend modal, the backend handler, and the rendered dashboard together — the business logic is split across all three and no test guards the seam. Pair each such change with a re-run of `scripts/low_stock.py` whenever the change touches how `StockMovement.grams` is written, because the low-stock consumption calculation and the audit trail both read that overloaded field. For the reports subsystem, always validate a report endpoint and the matching `Reports.jsx` `REPORTS` entry together by inspecting the raw JSON response: the endpoints have no `response_model`, so a renamed SQL column will silently break a table cell rather than fail loudly. Before relying on `/reports/last7` or `low_stock.py`, confirm the `received_at`/`timestamp` discrepancy has been resolved, since both currently reference a nonexistent `timestamp` column.
