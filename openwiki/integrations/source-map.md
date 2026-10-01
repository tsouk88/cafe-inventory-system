---
type: Reference
title: Source Map
description: Pointer to the main source files for each concern — backend API, frontend UI, automation, and docs — so engineers can navigate the compact codebase quickly.
tags: [source-map, navigation, backend, frontend, automation]
sources:
  - id: openwiki-source-6d4b4e707b8d60b6ccfa3425
    resource: repo://.github/workflows/openwiki-update.yml
  - id: openwiki-source-8037e2358a2c4f9b2c722a11
    resource: repo://AGENTS.md
  - id: openwiki-source-a2371d6362e5db4bc834ad03
    resource: repo://CLAUDE.md
  - id: openwiki-source-76524f4e00c120c9aa9c9390
    resource: repo://create_tables.py
  - id: openwiki-source-cb5451ecbfb2b6e0666dbc3a
    resource: repo://database.py
  - id: openwiki-source-1047363cf615000e4c9bb694
    resource: repo://frontend/package.json
  - id: openwiki-source-49b284af4abdb5084d5b9d09
    resource: repo://frontend/src/App.jsx
  - id: openwiki-source-c1b3e89d74bd2715617287c8
    resource: repo://frontend/src/DeductModal.jsx
  - id: openwiki-source-976cce2671f0f217275e3f31
    resource: repo://frontend/src/main.jsx
  - id: openwiki-source-e828310cceb581a07cef2a85
    resource: repo://frontend/src/Reports.jsx
  - id: openwiki-source-1c255feabbe58b8055271a72
    resource: repo://frontend/src/RestockModal.jsx
  - id: openwiki-source-833e692518af9eeaf8564cc6
    resource: repo://main.py
  - id: openwiki-source-47aa29ed50b918e91518a4a7
    resource: repo://models.py
  - id: openwiki-source-23775c3de52f3ab95a13cb8b
    resource: repo://README.md
  - id: openwiki-source-e0407a790bbcbedb69a6ca50
    resource: repo://schemas.py
  - id: openwiki-source-7ed2d9b3005cd559f37189d1
    resource: repo://scripts/low_stock.py
generated: { by: "openwiki/0.6.1", at: "2026-10-01T12:43:49.948Z" }
verified:
  - by: openwiki/0.6.1
    at: 2026-10-01T12:43:49.948Z
---

# Source Map

This page points engineers to the main source files for each concern. The repo is compact, so this is a navigation aid, not a file inventory; for behavior and control flow see [Architecture overview](../architecture/overview.md) and [Operations and workflows](../workflows/operations.md).

Per [AGENTS.md](../../AGENTS.md), source code is authoritative — treat these files as the source of truth over generated wiki text.

## Backend
- `main.py` — FastAPI app: CRUD endpoints (`/varieties`, `/products`, `/batches`), the `/scan` and `/deduct` stock-reduction endpoints with FIFO/expiry-ordered deduction logic for both weight and unit tracking, and four raw-SQL report endpoints (`/reports/stock-per-variety`, `/reports/fefo-next`, `/reports/expired-with-stock`, `/reports/last7`). The built frontend is served via `app.frontend()`.
- `database.py` — SQLAlchemy engine/session driven by the `DATABASE_URL` environment variable (loaded via `dotenv`); exposes the `get_db` dependency.
- `models.py` — SQLAlchemy tables (`Variety`, `Product`, `Batch`, `StockMovement`) and enums (`Direction` with `IN`/`OUT`, `TrackingType` with `WEIGHT`/`UNITS`). Both `Batch` and `StockMovement` timestamp their rows with a `received_at` column.
- `schemas.py` — Pydantic request/response models; `BatchCreate` and `ProductDeduct` each use a `model_validator` to require a quantity (`grams_remaining`/`units_remaining`, or `grams`/`units`).
- `create_tables.py` — one-off schema bootstrap that calls `Base.metadata.create_all`.

> **Schema discrepancy:** `models.py` defines the timestamp column as `received_at` on both `Batch` and `StockMovement`, but the `/reports/last7` SQL in `main.py` and the `scripts/low_stock.py` query both reference `timestamp` (`s.timestamp`, `StockMovement.timestamp`). Those queries will error against the current schema until the column name is reconciled.

## Frontend
- `frontend/src/main.jsx` — React entry point: mounts `<App />` inside `StrictMode` into the `#root` element.
- `frontend/src/App.jsx` — dashboard. Polls `/varieties` and `/batches` on a 10-second interval, renders varieties and batches with expiry urgency, and runs the barcode scan flow. A `view` state toggle plus a "Reports" button switches the main panel between the stock dashboard and `<Reports />` (imported from `Reports.jsx`).
- `frontend/src/Reports.jsx` — reports view. Renders four report tables, each fetching its own endpoint via the `REPORTS` array config (paths, column labels, and per-column formatters). The `isWeight()` helper normalizes `tracking_type` casing between raw-SQL responses (`WEIGHT`) and ORM responses (`weight`).
- `frontend/src/RestockModal.jsx` — restock form that POSTs a new batch to `/batches`.
- `frontend/src/DeductModal.jsx` — manual removal form that collects variety and quantity (grams or units) and POSTs to `/deduct`.
- `frontend/src/App.css` and `frontend/src/index.css` — presentation and layout.
- `frontend/package.json` — Vite/React scripts (`dev`, `build`, `lint` via oxlint, `preview`).

## Automation and deployment
- `scripts/low_stock.py` — deterministic low-stock alert job: sums recent `OUT` movements (referencing `StockMovement.timestamp`), projects days-until-empty per variety, and emails the owner via SMTP using `GMAIL_ADDRESS`/`GMAIL_PASSWORD` when a variety is projected to run out soon. Run via cron, not in the request path.
- `.github/workflows/openwiki-update.yml` — monthly scheduled GitHub Action that runs `openwiki code --update` and opens a pull request to refresh this wiki.
- `.fastapicloudignore` — FastAPI Cloud deployment ignore rules (excludes `frontend/dist`).

## Repository docs
- `README.md` — product summary, FIFO/expiry tracking explanation, local run instructions, and tech stack.
- `AGENTS.md` — OpenWiki agent instructions for the repo (source is authoritative; do not hand-edit generated wiki unless explicitly asked).
- `CLAUDE.md` — pointer to `AGENTS.md`.

## Notes for maintainers
Prefer adding a focused page over expanding this file into a file inventory when new domains appear.
