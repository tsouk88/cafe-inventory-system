---
type: Reference
title: OpenWiki Quickstart
description: Entry point that orients new readers to the café inventory repo and routes them to the right wiki page for their task.
tags: [quickstart, navigation, overview]
verified:
  - by: openwiki/0.5.1
    at: 2026-09-11T18:21:42.744Z
sources:
  - id: openwiki-source-76524f4e00c120c9aa9c9390
    resource: repo://create_tables.py
  - id: openwiki-source-cb5451ecbfb2b6e0666dbc3a
    resource: repo://database.py
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
  - id: openwiki-source-23775c3de52f3ab95a13cb8b
    resource: repo://README.md
  - id: openwiki-source-e0407a790bbcbedb69a6ca50
    resource: repo://schemas.py
  - id: openwiki-source-7ed2d9b3005cd559f37189d1
    resource: repo://scripts/low_stock.py
generated: { by: "openwiki/0.5.1", at: "2026-09-11T18:21:42.744Z" }
---

# OpenWiki Quickstart

This repository is a small full-stack café inventory app for dried nuts and fruits. The codebase is centered on expiry-aware stock tracking: every restock creates a batch, and sales or manual removals are deducted from the earliest-expiring batch first.

Start here if you are new to the repo or need to update the wiki.

## What this repo does

- Tracks **varieties** of products, each using either **weight** tracking (grams) or **unit** tracking (pieces), selected via `TrackingType` in `models.py`.
- Tracks **products** by barcode and maps each to a variety; weight-based products carry a `package_size_grams` size used at scan time.
- Tracks **batches** with their own `expiry_date` so stock is consumed in FIFO/expiry order.
- Serves a React dashboard from the same FastAPI app that hosts the API.
- Includes a deterministic low-stock email script (`scripts/low_stock.py`) for scheduled/cron runs, not part of the live request path.

The README explains the product goal and the main operational rules, especially FIFO expiry handling and the English-language demo UI used for the public deployment.

## Where to go next

For your task, start with the matching page:

- [Architecture overview](architecture/overview.md) — how FastAPI, SQLAlchemy, the React UI, and deployment fit together.
- [Domain concepts](domain/concepts.md) — the core data model (`Variety`, `Product`, `Batch`, `StockMovement`) and the FIFO/expiry rules.
- [Operations and workflows](workflows/operations.md) — scan, restock, manual removal, the low-stock alert job, and local setup.
- [Integration source map](integrations/source-map.md) — where the main logic lives in source, file by file.
- [Testing and validation](testing.md) — how to validate changes given there is no formal test suite.

## Repo shape at a glance

- `main.py` exposes the API endpoints (`/varieties`, `/products`, `/batches`, `/scan`, `/deduct`) and serves the built frontend via `app.frontend("/", directory="frontend/dist")`.
- `models.py` defines the SQLAlchemy persistence layer (`Variety`, `Product`, `Batch`, `StockMovement`, plus the `Direction` and `TrackingType` enums).
- `schemas.py` defines the Pydantic request/response types and validates that a quantity (`grams` or `units`) is supplied for deducts and batch creation.
- `database.py` sets up the SQLAlchemy engine, session factory, and the `get_db` dependency.
- `create_tables.py` is a one-off bootstrap that runs `Base.metadata.create_all` from the models.
- `frontend/src/` contains the React dashboard (`App.jsx`) plus the restock and manual-removal modals.
- `scripts/low_stock.py` is a standalone scheduled job, not part of the live request path.

## Important implementation notes

- The dashboard polls `/varieties` and `/batches` on a 10-second interval, so the UI stays current without a manual refresh — useful for a screen left open throughout the day.
- Weight-based products deduct grams; unit-based products deduct whole units. The branch is selected from the variety's `tracking_type` at each endpoint.
- Every restock, scan, and manual removal writes a `StockMovement` row (direction `IN` or `OUT`), which the low-stock script aggregates over the last 7 days of `OUT` movements.
- The repo is deployed on FastAPI Cloud, and the frontend is served from `frontend/dist` through `app.frontend()`. `.fastapicloudignore` keeps the built frontend dist out of the ignored-asset set so the server can mount it.

## Before you change anything

Business logic is intentionally coupled across the backend and frontend. If you are updating behavior, check both the backend endpoint in `main.py` and the matching UI form in `frontend/src/`:

- Restock: `RestockModal.jsx` POSTs a `BatchCreate` payload (`variety_id`, `expiry_date`, and either `grams_remaining` or `units_remaining`) to `/batches`, which the backend handles in `main.py`.
- Manual removal: `DeductModal.jsx` POSTs a `ProductDeduct` payload (`variety_id` with either `grams` or `units`) to `/deduct`, which the backend handles in `main.py`.
- Scan: `App.jsx` POSTs a barcode to `/scan`, whose response (`grams_removed`/`units_removed`, `status`) drives the on-screen message.

The forms build request payloads the API expects, and the API branches on the weight/unit distinction defined by the selected variety. Change both sides together, and prefer the narrowest quiet validation that proves the changed behavior (per the AGENTS.md guidance: treat source code and tests as authoritative and preserve complete failure output).
