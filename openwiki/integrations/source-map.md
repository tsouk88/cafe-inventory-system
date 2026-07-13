# Source Map

This page points future readers to the main source files for each concern.

## Backend
- `main.py` — API endpoints, FIFO deduction logic, and frontend serving.
- `database.py` — environment-driven SQLAlchemy engine/session setup.
- `models.py` — database tables and enums.
- `schemas.py` — request and response validation.
- `create_tables.py` — one-off schema bootstrap.

## Frontend
- `frontend/src/App.jsx` — dashboard layout, polling, scan flow, and variety/batch rendering.
- `frontend/src/RestockModal.jsx` — restock form and payload creation.
- `frontend/src/DeductModal.jsx` — manual removal form and payload creation.
- `frontend/src/App.css` and `frontend/src/index.css` — presentation and layout.
- `frontend/package.json` — Vite/React scripts (`dev`, `build`, `lint`, `preview`).

## Automation and deployment
- `scripts/low_stock.py` — deterministic scheduled alert job.
- `.github/workflows/openwiki-update.yml` — scheduled OpenWiki documentation refresh.
- `.fastapicloudignore` — FastAPI Cloud deployment ignore rules.

## Repository docs
- `README.md` — the best high-level product summary and local run instructions.
- `AGENTS.md` / `CLAUDE.md` — existing OpenWiki usage note for the repo.

## Notes for maintainers
The repo is compact, so the source map is intentionally short. If new domains appear later, prefer adding a focused page instead of expanding this file into a file inventory.
