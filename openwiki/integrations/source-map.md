---
type: Reference
title: Source Map
description: Pointer to the main source files for each concern — backend API, frontend UI, automation, and docs — so engineers can navigate the compact codebase quickly.
tags: [source-map, navigation, backend, frontend, automation]
verified:
  - by: openwiki/0.5.1
    at: 2026-09-11T18:21:42.744Z
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

# Source Map

This page points engineers to the main source files for each concern. The repo is compact, so this is a navigation aid, not a file inventory; for behavior and control flow see [Architecture overview](../architecture/overview.md) and [Operations and workflows](../workflows/operations.md).

Per [AGENTS.md](../../AGENTS.md), source code is authoritative — treat these files as the source of truth over generated wiki text.

## Backend
- `main.py` — FastAPI app: endpoints (`/varieties`, `/products`, `/batches`, `/scan`, `/deduct`), FIFO/expiry-ordered deduction logic, and frontend static serving via `app.frontend()`.
- `database.py` — SQLAlchemy engine/session driven by the `DATABASE_URL` environment variable; exposes the `get_db` dependency.
- `models.py` — SQLAlchemy tables (`Variety`, `Product`, `Batch`, `StockMovement`) and enums (`Direction`, `TrackingType`).
- `schemas.py` — Pydantic request/response models; validates that batches and deductions supply a quantity.
- `create_tables.py` — one-off schema bootstrap that calls `Base.metadata.create_all`.

## Frontend
- `frontend/src/App.jsx` — dashboard, polling of `/varieties` and `/batches`, scan flow, and variety/batch rendering with expiry urgency.
- `frontend/src/RestockModal.jsx` — restock form that POSTs a new batch to `/batches`.
- `frontend/src/DeductModal.jsx` — manual removal form that POSTs to `/deduct`.
- `frontend/src/App.css` and `frontend/src/index.css` — presentation and layout.
- `frontend/package.json` — Vite/React scripts (`dev`, `build`, `lint` via oxlint, `preview`).

## Automation and deployment
- `scripts/low_stock.py` — deterministic low-stock alert job: sums recent OUT movements, projects days-until-empty, and emails the owner via SMTP when a variety is projected to run out soon. Run via cron, not in the request path.
- `.github/workflows/openwiki-update.yml` — monthly scheduled GitHub Action that runs `openwiki code --update` and opens a pull request to refresh this wiki.
- `.fastapicloudignore` — FastAPI Cloud deployment ignore rules (excludes `frontend/dist`).

## Repository docs
- `README.md` — product summary, FIFO/expiry tracking explanation, local run instructions, and tech stack.
- `AGENTS.md` — OpenWiki agent instructions for the repo (source is authoritative; do not hand-edit generated wiki).
- `CLAUDE.md` — pointer to `AGENTS.md`.

## Notes for maintainers
Prefer adding a focused page over expanding this file into a file inventory when new domains appear.
