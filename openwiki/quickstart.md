# OpenWiki Quickstart

This repository is a small full-stack café inventory app for dried nuts and fruits. The codebase is centered on expiry-aware stock tracking: every restock creates a batch, and sales/removals are deducted from the earliest-expiring batch first.

Start here if you are new to the repo or need to update the wiki.

## What this repo does
- Tracks **varieties** of products, each using either **weight** tracking or **unit** tracking.
- Tracks **products** by barcode and maps them to a variety.
- Tracks **batches** with expiry dates so stock is consumed in FIFO/expiry order.
- Serves a React dashboard from the same FastAPI app used for the API.
- Includes a deterministic low-stock email script for scheduled runs.

The README explains the product goal and the main operational rules, especially FIFO expiry handling and the English-language demo UI used for the public deployment.

## Where to go next
- [Architecture overview](architecture/overview.md) — how FastAPI, SQLAlchemy, the React UI, and deployment fit together.
- [Domain concepts](domain/concepts.md) — the core data model and FIFO/expiry rules.
- [Operations and workflows](workflows/operations.md) — scan, restock, removal, and low-stock alert behavior.
- [Integration map](integrations/source-map.md) — where the main logic lives in source.
- [Testing guidance](testing.md) — how to validate changes with the available scripts.

## Repo shape at a glance
- `main.py` exposes the API endpoints and serves the built frontend.
- `models.py`, `schemas.py`, and `database.py` define the persistence layer and request/response types.
- `frontend/src/` contains the React dashboard, restock modal, and manual removal modal.
- `scripts/low_stock.py` is a standalone scheduled job, not part of the live request path.
- `create_tables.py` bootstraps the schema from the SQLAlchemy models.

## Important implementation notes
- The dashboard polls the backend periodically, so the UI stays current without manual refresh.
- Weight-based products deduct grams; unit-based products deduct whole units.
- The backend stores movement history in `stock_movements`, which is useful for stock auditing and the low-stock script.
- The repo is deployed on FastAPI Cloud, and the frontend is served from `frontend/dist` through `app.frontend()`.

## Before you change anything
If you are updating business logic, check both the backend endpoint in `main.py` and the matching UI form in `frontend/src/`. The behavior is intentionally coupled: the forms build request payloads for the API, and the API assumes the weight/unit distinction defined by the selected variety.
