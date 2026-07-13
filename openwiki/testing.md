# Testing and Validation

## What exists today
The repository does not currently expose a formal Python test suite in the inspected sources. Validation is therefore mostly by running the app and the frontend build/lint commands.

## Recommended checks when changing the repo
### Backend changes
- Start the API: `uvicorn main:app --reload`
- Exercise the affected endpoints manually.
- If schema creation changed, run `python create_tables.py` against a disposable database.

### Frontend changes
From `frontend/`:
- `npm run build`
- `npm run lint`
- `npm run dev` for manual verification

### Low-stock script changes
- Run `python scripts/low_stock.py` in an environment with the required database and Gmail credentials.
- Verify it prints the expected result when no stock is low.

## Risk areas to verify manually
- Weight-based vs unit-based branching in both the backend and the modals.
- FIFO behavior by creating multiple batches with different expiry dates.
- Dashboard polling after scan/restock/removal actions.
- Deployment behavior, especially that the built frontend still serves correctly through FastAPI.

## Practical rule
If you change any API payload or any tracking-type branch, validate the matching frontend modal, the backend handler, and the rendered dashboard together. The business logic is split across those three places.
