# Contributing to Industry.ai

Thanks for considering contributing! This is a small, offline PCB missing-component
detection app: a FastAPI backend plus a React (Vite + TypeScript) frontend, with
classical computer vision in between.

## Getting started

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### Frontend

```bash
cd frontend
npm install
npm run dev        # or npm run build for the production SPA
```

### How to run the app

```bash
cd backend
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

The built SPA is served statically by the backend; for the Vite dev flow run
`npm run dev` in `frontend` (it proxies `/api` to `http://127.0.0.1:8000`).

To try the app immediately, load the bundled demo dataset:

```bash
curl -X GET http://127.0.0.1:8000/api/v1/dataset/load
```

### Running tests

```bash
cd backend
python -m pytest -q
```

Unit tests cover the CV pipeline (ORB/homography + phase-correlation alignment,
lighting normalization, per-component comparison, detector verdicts:
present/missing/review, including lighting/noise invariance) and the API layer
(upload/annotate/inspect/export, demo loader, settings persistence).

Extra checks:

```bash
cd backend
python scripts/integration_check.py    # health + static serving + API
python -m scripts.smoke_test            # end-to-end inspection on the bundled demo data
```

Generate the synthetic demo dataset (reference + 5 test images):

```bash
cd backend
python -m scripts.generate_dataset
```

## Code style

- One logical change per pull request; keep the diff focused.
- Add docstrings for new public helpers in `app/` and short comments for
  non-obvious heuristics in `app/cv/`.
- Do not add runtime dependencies without mentioning it in the PR description.

## Pull requests

1. Create a branch off `main` (e.g. `docs/your-change`).
2. Make the change and run the tests above before opening the PR.
3. Open the PR with a short title and a description of the problem or feature
   (see [.github/PULL_REQUEST_TEMPLATE.md](../.github/PULL_REQUEST_TEMPLATE.md)).

Thanks for helping make this project better!
