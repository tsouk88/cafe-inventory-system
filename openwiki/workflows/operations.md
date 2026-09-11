---
type: "Reference"
title: "Workflows and Operations"
description: "Daily operator flows (scan, restock, manual removal), the low-stock alert job, environment variables, and the local setup runbook for the café inventory system."
tags: ["workflows", "operations", "runbook", "low-stock", "fifo", "environment"]
verified:
  - by: openwiki/0.5.1
    at: 2026-09-11T18:21:42.744Z
sources:
  - id: openwiki-source-cb5451ecbfb2b6e0666dbc3a
    resource: repo://database.py
  - id: openwiki-source-49b284af4abdb5084d5b9d09
    resource: repo://frontend/src/App.jsx
  - id: openwiki-source-833e692518af9eeaf8564cc6
    resource: repo://main.py
  - id: openwiki-source-23775c3de52f3ab95a13cb8b
    resource: repo://README.md
  - id: openwiki-source-7ed2d9b3005cd559f37189d1
    resource: repo://scripts/low_stock.py
generated: { by: "openwiki/0.5.1", at: "2026-09-11T18:21:42.744Z" }
---

# Workflows and Operations

This page documents the operator-facing workflows that drive the café inventory system — scanning barcodes at the counter, restocking a new delivery, manual removal — plus the scheduled low-stock alert job, environment configuration, and the local setup runbook. All branching behavior is grounded in `main.py`; the frontend modals that trigger these flows live in `frontend/src/`.

## Daily operator flow

### Scan a barcode

The scan flow is the primary day-to-day action at the counter: a product is sold and stock is deducted by one barcode read.

- The operator types or scans a barcode into the dashboard scan bar (`App.jsx` `handleScanSubmit`).
- The frontend POSTs `{ barcode }` to `POST /scan` (`main.py`).
- The backend looks up the `Product` by barcode, loads its `Variety`, and deducts stock from the earliest-expiring batch using FIFO rules that branch on `variety.tracking_type`:
  - **`WEIGHT`** — subtract `product.package_size_grams` by walking batches ordered by `expiry_date` ascending, zeroing batches as needed and tracking any uncovered `stock_shortfall`. The `StockMovement` always records the full `package_size_grams` as the grams removed (a package physically leaves the shop regardless of whether the on-file batches could cover it). The response status is `"completed"` when the shortfall is `0`, otherwise `"stock_mismatch"`.
  - **`UNITS`** — find the first batch (ordered by `expiry_date`) with `units_remaining > 0` and decrement exactly `1` unit. If no such batch exists, return `404 Batch not found`. The `StockMovement` records `grams=1` (the overloaded units count). The response is always `{"units_removed": 1, "status": "completed"}` with no shortfall tracking.
- On a successful scan the frontend calls `loadData()` to re-fetch `/varieties` and `/batches` immediately, so the dashboard reflects the new totals without waiting for the next 10-second poll.

Note the asymmetry: the weight branch walks the whole batch chain and can spill over into later batches; the unit branch touches **only the first available batch** and removes exactly one unit.

### Restock a product

Restocking records a new delivery as a new `Batch` plus an inbound `IN` movement.

- The operator opens **New Restock** (`RestockModal.jsx`).
- The modal shows a grams field or a units field depending on the selected variety's `tracking_type` (`weight` vs `units`).
- On submit it POSTs to `POST /batches` with `variety_id`, `expiry_date`, and the matching quantity field (`grams_remaining` for weight, `units_remaining` for units; the other is `null`).
- The backend (`main.py` `create_batch`) inserts the `Batch`, then inserts an `IN` `StockMovement` whose `grams` column carries the restock quantity **regardless of tracking type**: for weight it is `new_batch.grams_remaining`, for units it is `new_batch.units_remaining`. The `StockMovement.grams` column is overloaded this way across all three write paths (`/batches`, `/scan`, `/deduct`), so the audit trail and the low-stock consumption sum both read one integer field.
- The dashboard refreshes via the same `loadData()` path.

### Manual removal

Manual removal lets an operator deduct stock by variety (not barcode) without a product sale.

- The operator opens **Remove** (`DeductModal.jsx`).
- The modal uses the selected variety's `tracking_type` to show a grams or units field and POSTs `{ variety_id, grams, units }` to `POST /deduct` (`main.py` `manual_deduct`).
- The backend applies the same FIFO-by-`expiry_date` rule as `/scan`, but with important differences:
  - For **`WEIGHT`**, it subtracts `deduct.grams` across the batch chain and always returns `{"status": "completed"}` — it does **not** compute or report a shortfall, even when the batches cannot cover the requested grams. The `StockMovement` records `grams=deduct.grams` (the requested amount).
  - For **`UNITS`**, it walks the batches (filtered to `units_remaining > 0`, ordered by `expiry_date`), subtracts `deduct.units` with spillover, computes `units_removed = deduct.units - remaining_to_subtract`, records `grams=units_removed`, and returns `{"status": "completed" if remaining_to_subtract == 0 else "stock_mismatch"}`.

### stock_mismatch behavior inconsistency

There is a non-obvious behavioral inconsistency between the weight paths of `/scan` and `/deduct` that engineers must either preserve consciously or fix:

- `POST /scan` weight branch returns `status: "stock_mismatch"` when the on-file batches cannot cover `package_size_grams` (the shortfall is tracked and returned as `stock_shortfall`).
- `POST /deduct` weight branch **always** returns `status: "completed"` and returns no shortfall, even when the same spillover leaves an uncovered remainder.
- `POST /deduct` unit branch **does** track the mismatch (`status: "stock_mismatch"` when `remaining_to_subtract != 0`).
- `POST /scan` unit branch removes exactly one unit and always reports `completed`; it has no shortfall concept.

So only the weight `/scan` and unit `/deduct` paths surface a mismatch; weight `/deduct` silently swallows it. Any change to this behavior must be deliberate, because the dashboard's scan message (`Removed ${data.grams_removed}g`) and the audit trail both assume the current shapes.

## FIFO deduction branching logic

<!-- openwiki: mermaid parse failed and this diagram was converted to a text fence so it does not break rendering. Fix the diagram source and restore the mermaid fence. Parser error: Heuristic: a semicolon inside a label breaks rendering; rephrase the label. -->
```text
flowchart TD
    Start["POST /scan or /deduct"] --> Lookup["Look up Product by barcode, or Variety by variety_id"]
    Lookup --> TT["Check variety.tracking_type"]
    TT -->|"WEIGHT"| WQty["Set remaining_to_subtract = package_size_grams / deduct.grams"]
    WQty --> WLoop["Iterate batches ordered by Batch.expiry_date ascending"]
    WLoop --> WDecide{"batch.grams_remaining >= remaining_to_subtract?"}
    WDecide -->|"yes"| WSub["batch.grams_remaining -= remaining_to_subtract; remaining_to_subtract = 0"]
    WDecide -->|"no"| WZero["remaining_to_subtract -= batch.grams_remaining; batch.grams_remaining = 0"]
    WSub --> WNext{"more batches and remaining > 0?"}
    WZero --> WNext
    WNext -->|"yes"| WLoop
    WNext -->|"no"| WDone["Record StockMovement OUT grams = full package size / requested grams"]
    TT -->|"UNITS"| UFind["scan: first batch with units > 0; deduct: all batches with units > 0, ordered by expiry_date"]
    UFind --> UDec["Decrement 1 unit, or loop subtracting deduct.units with spillover"]
    UDec --> UDone["Record StockMovement OUT grams = 1 / units_removed"]
    WDone --> WStatus["scan: completed if shortfall 0 else stock_mismatch; deduct: always completed"]
    UDone --> UStatus["scan: completed; deduct: completed if remaining 0 else stock_mismatch"]
```

The flowchart shows the two branches the weight and unit paths take through `/scan` and `/deduct`. The weight branch walks the entire batch chain in expiry order and (in `/scan` only) tracks a shortfall; the unit branch in `/scan` touches only the first batch with stock, while the unit branch in `/deduct` chains across batches like the weight branch and tracks its own mismatch.

## Low-stock alert job

`scripts/low_stock.py` is a standalone scheduled script — **not** an API route and not part of the live request path. The README describes it as a daily/cron job, since a café only needs a daily heads-up to reorder in time.

Its flow, grounded in `scripts/low_stock.py`:

1. Query `StockMovement` rows where `direction == OUT` within the last 7 days, joined to `Product` on `StockMovement.barcode == Product.barcode` to recover `variety_id`. Sum `movement.grams` per `variety_id` into `moves` (weekly consumption).
2. For each `variety_id` in `moves`, sum remaining stock across its batches: `batch.grams_remaining` for `WEIGHT` varieties, `batch.units_remaining` for `UNITS` varieties.
3. Compute `days_left = remaining * 7 / consumed` per variety, skipping any variety where `consumed == 0`.
4. Flag any variety with `days_left < 5`; collect those variety names into `low_stock_items`.
5. If none are low, print `No low stocks detected` and send nothing. Otherwise, build a MIME email `"Watchout! {names} have low stock.."` with subject `LOW STOCK WARNING`, addressed from and to `GMAIL_ADDRESS`, and send it over `smtplib.SMTP("smtp.gmail.com", 587)` with `starttls()` and a `server.login(gmail, password)`.

Because the script sums `movement.grams` — the overloaded `StockMovement.grams` column — its consumption figure is correct only as long as the handlers keep writing grams for weight and the unit count for units into that one column. A change to how movements are recorded must be re-validated against this script.

## Local setup runbook

Verified against `README.md`:

```bash
# backend
python -m venv venv
venv\Scripts\activate        # Windows
pip install -r requirements.txt
python create_tables.py
uvicorn main:app --reload

# frontend
cd frontend
npm install
npm run dev
```

- `create_tables.py` is a one-off that calls `Base.metadata.create_all(bind=engine)` and prints `Tables created successfully!`; it recreates tables from the models and confirms they import cleanly.
- `main.py` mounts the built frontend at `/` from `frontend/dist` via `app.frontend("/", directory="frontend/dist")`, so for a production-style run you must `npm run build` first.
- CORS in `main.py` allows `http://localhost:5173` (the Vite dev server origin), which is why `npm run dev` works against the local backend.
- `frontend/package.json` defines `dev`, `build`, `lint`, and `preview` scripts — no test runner.

## Environment variables

- `DATABASE_URL` — required by `database.py`, which calls `create_engine(os.getenv("DATABASE_URL"))` after `load_dotenv()` to build the SQLAlchemy `engine` and `SessionLocal`. A `.env` file (not committed) is the intended source; the script reads it at import time, so it must be set before the app starts.
- `GMAIL_ADDRESS` and `GMAIL_PASSWORD` — read by `scripts/low_stock.py` via `os.getenv`; used as both the sender and recipient of the low-stock warning and as the SMTP login credentials against `smtp.gmail.com:587`.

## Operational cautions

- The frontend is translated into English for the public demo, but the README notes the original staff-facing UI was in Greek. If you change labels or copy, verify the documentation still reflects the public demo rather than the original internal UI.
- The dashboard polls `/varieties` and `/batches` every 10 seconds (`setInterval(loadData, 10000)` in `App.jsx`) and re-fetches immediately after each successful scan/restock/removal. Keep backend responses fast and predictable so the poll cadence stays smooth; avoid endpoint changes that break the `loadData` fetch pair.
- The business logic for weight vs unit tracking is split across **three** places — the backend handler in `main.py`, the matching frontend modal (`RestockModal.jsx` / `DeductModal.jsx`), and the dashboard rendering in `App.jsx` — with no automated test guarding the seam. If you adjust request/response payloads, field names, or which branch a tracking type takes, update all three together and re-run `scripts/low_stock.py` whenever the change touches how `StockMovement.grams` is written.
