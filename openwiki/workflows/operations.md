# Workflows and Operations

## Daily operator flow
### Scan a barcode
- The operator types or scans a barcode into the dashboard scan bar.
- The frontend POSTs `{ barcode }` to `/scan`.
- The backend finds the product, loads its variety, and deducts stock from the earliest-expiring batch.
- The UI refreshes stock data after a successful scan.

### Restock a product
- The operator opens **New Restock**.
- The modal shows either grams or units depending on the selected variety.
- A new batch is POSTed to `/batches` with `variety_id`, `expiry_date`, and the matching quantity field.
- The backend inserts both the batch and an `IN` movement.

### Manual removal
- The operator opens **Remove**.
- The modal uses the selected variety to show grams or units.
- The frontend POSTs to `/deduct`.
- The backend applies the same FIFO rule used for scans, then records an `OUT` movement.

## Low-stock alert job
`/scripts/low_stock.py` is a standalone scheduled script, not an API route.
Its intended flow is:
1. read recent `OUT` movements from the last 7 days
2. total remaining stock by variety
3. project days remaining using `remaining × 7 / consumed`
4. email the owner when projected days remaining drop below the threshold

This script depends on `GMAIL_ADDRESS` and `GMAIL_PASSWORD`.

## Local setup and runbook notes
From the README:
- create a virtual environment
- install Python dependencies from `requirements.txt`
- run `python create_tables.py` once to create tables
- start the backend with `uvicorn main:app --reload`
- in `frontend/`, run `npm install` and `npm run dev`

## Environment variables
- `DATABASE_URL` — required by `database.py` for SQLAlchemy.
- `GMAIL_ADDRESS` and `GMAIL_PASSWORD` — used by the low-stock email script.

## Operational cautions
- The frontend is translated into English for the public demo, but the README notes the original staff-facing UI was Greek. If you change labels or copy, verify that the documentation still reflects the public demo rather than the original internal UI.
- Because the dashboard polls every 10 seconds, backend responses should remain fast and predictable.
- If you adjust request/response payloads in `main.py`, update the modal forms in `frontend/src/` at the same time.
