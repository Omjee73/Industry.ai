# PCB Missing Component Detection — Task B - By Omjee Gupta | IIT Madras | 24f2002843

A desktop-friendly, fully offline web application that detects missing components
on PCB boards: upload a good reference board, name its parts, then upload test
photos of the same board and see which named parts are missing.

> Note: `Task-B-PCB-Missing-Component.pdf` was **not present** in the repository
> when the project was built. The implementation follows the task description in
> the session (see [docs/architecture_diagram.html](docs/architecture_diagram.html)
> and [RESEARCH.md](RESEARCH.md)).

## Overview

The app answers: *"On this photo of the board, is every named component there?"*

- Upload a reference (good) board image.
- Draw named rectangles on it (R1, C1, U1, D1, ...) — names + positions are stored.
- Upload up to 3 test images of the same board (same viewpoint).
- Each test image is aligned to the reference, per-component presence is
  measured with a multi-indicator classical CV pipeline (SSIM, pixel diff, edge
  coverage, surrounding-PCB-context), and the result is:
  - **Green OK** — every component present,
  - **Red MISSING** — a named component is missing (highlighted on the image),
  - **Yellow REVIEW** — uncertain; not declared missing.

## Features

**Application**
- 4-step wizard: upload reference → name components → upload tests → inspect & review.
- One-click demo dataset loader (`GET /api/v1/dataset/load`) — loads the bundled
  synthetic reference + 5 test images.
- Works completely offline; no internet at runtime, no cloud, no API keys.

**Component annotation**
- Draw rectangles with click-and-drag on the reference board; move/resize/delete;
- Names editable from the sidebar; positions stored in normalized coordinates
  (survive image resizing);
- Persisted in SQLite; saved automatically after each edit.

**Inspection**
- Alignment: ORB feature matching + RANSAC homography (translation, rotation,
  small scale) with a phase-correlation fallback (`backend/app/cv/aligner.py`).
- Lighting normalization (CLAHE + percentiles, `backend/app/cv/normalizer.py`).
- Comparison per component ROI: SSIM (`skimage.metrics.structural_similarity`),
  mean absolute pixel diff, edge coverage, surrounding-context ring
  (`backend/app/cv/comparator.py`).
- Missing detection: weighted multi-indicator score → present/review/missing with
  configurable thresholds (`backend/app/cv/detector.py`);
- Results: per-component names, confidence, explanations + status pills;
  missing components highlighted on test images (same normalized bboxes).
- Download results as **JSON** or **CSV** (`GET /api/v1/inspection/{id}/export`).

**Settings**
- Tunable CV thresholds live in the UI (Settings button) via
  `GET/PUT /api/v1/settings` (stored in SQLite).

## Technology stack

| Layer | Tech |
|---|---|
| Frontend | React, Vite, TypeScript, Tailwind CSS, Lucide icons |
| Backend | FastAPI, uvicorn, SQLAlchemy (2.0), SQLite |
| CV | OpenCV (ORB, homography, Canny, CLAHE), NumPy, scikit-image (SSIM), Pillow |
| Tests | pytest (unit + API via FastAPI TestClient) |

## Project structure

```
frontend/                    React + Vite + Tailwind app (src/, dist/ built)
  src/components/            Dashboard, PCICanvas, UploadCard, ResultCard,
                             SettingsDialog, StatusPill, Toast
  src/api/client.ts          REST client
  src/styles/                theme.css (light/dark), globals.css
backend/
  app/
    api/routes/              health, reference, images, inspection, settings, dataset
    cv/                      aligner, normalizer, comparator, detector, pipeline
    services/                image, annotation, settings, inspection, export, dataset
    database/                models.py (Image, Annotation, Inspection, TestImage, Setting), db.py
    schemas/                 requests/responses pydantic models
  scripts/                   generate_dataset.py, smoke_test.py, integration_check.py,
                             export_chat_history.py, generate_architecture_html.py
  tests/                     test_aligner, test_detector, test_api, test_settings
  data/                      runtime data (gitignored): app.db, images/, demo/
docs/                        architecture_diagram.html (+ .archify candidate)
.archify/                    Archify candidate for the architecture diagram
```

## Installation and setup

### Windows PowerShell

```powershell
cd "C:\Users\gomje\OneDrive\Documents\Default Project"

# Backend dependencies
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# Frontend: install dependencies and build the SPA
cd ..\frontend
npm install
npm run build

# Backend: install dependencies (optional if the venv is active)
cd ..\backend
pip install -r requirements.txt
```

### Linux / macOS (bash)

```bash
cd ~/Documents/"Default Project"

cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cd ../frontend
npm install && npm run build
cd ../backend
pip install -r requirements.txt
```

## How to run

### Backend + frontend (single process, offline)

```powershell
# PowerShell
cd backend
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

```bash
# bash
cd backend
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Then open **http://127.0.0.1:8000** (the built SPA is served statically by the backend).

### Development mode (Vite dev server + proxy)

```powershell
cd frontend
npm run dev     # -> http://localhost:5173 (proxies /api to http://127.0.0.1:8000)
```

## How to use the app

1. **Upload reference board** — drag & drop a PNG/JPEG of the good board, or click
   *"Or load the bundled demo dataset"* (reference + 5 pre-made test images).
2. **Name the components** — click and drag rectangles on the board to draw
   component regions (R1, R2, C1, ...). Drawn names appear in the sidebar;
   rename (pencil) and delete (trash) from there. Rectangles can be moved and
   resized by dragging.
3. **Upload test images** — upload up to 3 photos of the same board taken from
   the same viewpoint.
4. **Inspect** — click *"Run inspection"*. The backend aligns each test image to
   the reference (ORB + homography), then compares each component ROI and reports:
   - **Green OK**: "All components present — OK" when nothing is missing,
   - **Red MISSING**: "N missing components" + per-component table (name, status,
     confidence, explanation) + highlighted boxes on the test images,
   - **Yellow REVIEW**: "Review needed" for uncertain results.
5. **Export** — download **JSON** or **CSV** with all component verdicts.

## How to run tests

```powershell
cd backend
python -m pytest -q
```

```bash
cd backend
python -m pytest -q
```

Unit tests: ORB/homography/phase-correlation alignment, detector verdicts
(present/missing/review, lighting/noise invariance), API tests (upload, annotate,
inspect, export, demo loader), settings persistence.

Extra checks:

```powershell
cd backend
python scripts\integration_check.py      # health + static serving + API
python -m scripts.smoke_test              # end-to-end demo data inspection
```

```bash
cd backend
python scripts/integration_check.py
python -m scripts.smoke_test
```

Generate the synthetic demo dataset (reference + 5 test images):

```powershell
cd backend
python -m scripts.generate_dataset
```

```bash
cd backend
python -m scripts.generate_dataset
```

## Offline operation details

- The app runs on the local machine only: no cloud, no internet, no API keys, no
  telemetry. Images are stored under `backend/data/images/`, the SQLite database
  at `backend/data/app.db`, the built SPA at `frontend/dist/`.
- The CV pipeline is classical (OpenCV/scikit-image): ORB feature matching,
  RANSAC homography, CLAHE + percentiles, SSIM + pixel diff + edge coverage +
  context ring comparison, configurable thresholds.
- At runtime the frontend calls only `/api/v1/*` on the same origin (the backend
  also serves the SPA statically at `/`).
  <img width="1470" height="697" alt="image" src="https://github.com/user-attachments/assets/0bd3041e-2fc8-460f-bf99-aa1ef29f719d" />


## Screenshots section

The application is designed for a factory operator: a professional grey/white
theme (light by default, dark toggle), four-step workflow sidebar ("Upload reference board" → "Name the
components" → "Upload test images" → "Inspect & review"), a board canvas with
named rectangles (step 2), status pills per test image (green OK / red missing /
yellow review), result tables with per-component confidence and explanations,
and JSON/CSV download buttons (step 4). (Screenshots can be captured with your
browser's screenshot tool or OpenCode's browser tool after running the app.)

<img width="1477" height="697" alt="image" src="https://github.com/user-attachments/assets/bff937b8-991e-4ddd-a055-d15fc53faf43" />
<img width="1481" height="700" alt="image" src="https://github.com/user-attachments/assets/f1928996-3fee-40f1-b6a5-5837005044d4" />

## Troubleshooting

- **`ModuleNotFoundError`** — run `pip install -r requirements.txt` in `backend/`.
- **Port 8000 in use** — change the port in the `uvicorn` command (or set the
  `PCB_PORT` env var before starting the API).
- **First inspection is slow** — ORB feature detection on the first test image
  warms caches; expected < 1 s per image on the demo set.
- **"Demo dataset not found"** — run `python -m scripts.generate_dataset` in
  `backend/`.
- **ORB finds no matches on my real photos** — the images may differ in lighting
  or viewpoint; increase the thresholds in Settings or let the REVIEW band
  handle uncertainty. Re-check alignment with `aligner` tests:
  `python -m pytest tests/test_aligner.py`.
- **False "missing" on lighting changes** — this should not happen: lighting
  shifts are normalized (CLAHE + percentiles + shared scale). If you see it,
  report it with the exported JSON/CSV (see `docs/architecture_diagram.html`
  and `ARCHITECTURE.md`).

## Known limitations

- The backend serves the built SPA; for hot reload during development, use
  `npm run dev` in `frontend/` (vite proxies `/api` to `http://127.0.0.1:8000`).
- Up to **3 test images per inspection** (per assignment); more requires another
  inspection.
- **Classical CV**: the demo board is procedurally rendered. On real factory
  photos, missing detection targets blank/absent regions; lighting/noise/dust
  differences yield REVIEW rather than MISSING (safe direction).
- **Demo data is synthetic** — generated by `backend/scripts/generate_dataset.py`.
- Thresholds are a starting point: tune them in Settings for your factory
  camera. See `RESEARCH.md` for the alternatives considered.
- A live browser-level walkthrough of the React UI was not possible in the
  build environment (screenshots unavailable); the app was verified at DOM
  level (Step 1 renders: heading, upload card, demo-dataset button, sidebar
  workflow steps) and the full flow is covered by the API + CV tests.

## API summary

| Endpoint | Description |
|---|---|
| `GET /api/v1/health` | Health check |
| `POST /api/v1/reference` | Upload reference board (multipart) |
| `GET /api/v1/reference/latest` | Latest reference info |
| `GET /api/v1/reference/{id}/image` | Serve reference image |
| `POST /api/v1/reference/{id}/annotations` | Save component annotations (normalized) |
| `GET /api/v1/reference/{id}/annotations` | List annotations |
| `POST /api/v1/test` | Upload test image (multipart) |
| `GET /api/v1/test/{id}` | Test image info |
| `GET /api/v1/test/{id}/image` | Serve test image |
| `POST /api/v1/inspection` | Run inspection on ≤3 test images |
| `GET /api/v1/inspection/{id}` | Inspection results |
| `GET /api/v1/inspection/{id}/export?format=json|csv` | Download results |
| `GET/PUT /api/v1/settings` | Read/update CV thresholds |
| `GET /api/v1/dataset/load` | One-click demo dataset loader |

## Documentation

- [ARCHITECTURE.md](ARCHITECTURE.md) — architecture, layers, data flow, trade-offs
- [docs/architecture_diagram.html](docs/architecture_diagram.html) — diagram
- [RESEARCH.md](RESEARCH.md) — research & alternatives
- [AI_COLLAB.md](AI_COLLAB.md) — engineering decisions
- [AI_CHAT_HISTORY.md](AI_CHAT_HISTORY.md) — exported OpenCode session transcript

## Requirements

- Python ≥ 3.11 (`backend/requirements.txt`: fastapi, uvicorn, opencv-python,
  numpy, scikit-image, pillow, SQLAlchemy, httpx, pytest)
- Node.js ≥ 18 (`frontend/package.json`: react, vite, tailwindcss, lucide-react, …)

## Contributing

Contributions are welcome! See [CONTRIBUTING.md](CONTRIBUTING.md) for setup, how to run the tests, and the pull-request process.
