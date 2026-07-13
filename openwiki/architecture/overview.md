# Architecture Overview

## System shape
This is a single-deployment full-stack app:
- **Backend:** FastAPI with SQLAlchemy models and a PostgreSQL database.
- **Frontend:** React + Vite SPA under `frontend/`.
- **Serving model:** the FastAPI app mounts the built frontend with `app.frontend("/", directory="frontend/dist")`.
- **Deployment:** FastAPI Cloud, per the README and the recent deployment-support commit.

## Request flow
1. The React dashboard loads and immediately fetches `/varieties` and `/batches`.
2. The UI polls those same endpoints on an interval so operators see fresh stock state.
3. Barcode scans POST to `/scan`.
4. Restock actions POST to `/batches`.
5. Manual removals POST to `/deduct`.

## Backend responsibilities
`main.py` contains the API layer and the business rules that matter most:
- `/varieties` lists and creates tracked product varieties.
- `/products` lists and creates barcode-bound products.
- `/batches` lists and creates stock batches with expiry dates.
- `/scan` decrements the earliest-expiring batch first.
- `/deduct` applies the same FIFO logic for manual removal.

`database.py` loads `DATABASE_URL` from the environment and creates the SQLAlchemy session factory.

## Data model summary
`models.py` defines four core tables:
- `varieties` — product family and tracking mode (`weight` or `units`).
- `products` — barcode to variety mapping, with an optional package size for weight-tracked items.
- `batches` — per-delivery stock, remaining quantity, expiry date, and received timestamp.
- `stock_movements` — IN/OUT audit trail for stock changes.

## Why the architecture looks this way
The repository is intentionally optimized for a café workflow, not a general warehouse system. The important constraint is expiry-aware consumption: stock must be removed from the batch that expires first so operators do not silently sell older inventory too late.

The frontend mirrors that model by filtering batches by variety, sorting by expiry, and showing urgency states derived from the expiry date.

## Small but important constraints
- CORS is currently configured for the local Vite dev server origin only.
- The frontend API base is empty because the app expects same-origin serving in deployment.
- The backend code commits movements when batches are restocked or deducted, which makes scheduled reporting possible without guessing from current totals.
- `scripts/low_stock.py` is explicitly separate from request handling, so alerts can be scheduled independently of user traffic.
