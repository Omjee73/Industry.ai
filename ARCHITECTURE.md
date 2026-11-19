# Architecture — PCB Missing Component Detection (Task B)

This document describes the architecture of the local, offline web application that
detects missing components on PCB boards.

**Diagram:** [docs/architecture_diagram.html](docs/architecture_diagram.html)

## System overview

```
Operator (browser, e.g. http://localhost:8000)
        │  opens the 4-step wizard
        ▼
React SPA (frontend/, built with Vite; served statically by the backend)
        │  REST calls (UploadCard, PCICanvas, Results, SettingsDialog, ...)
        ▼
FastAPI backend (backend/app/) + uvicorn on :8000
        │  serves /api/v1/* and the static SPA
        ├──────────────────┬─────────────────────────────────────┐
        ▼                  ▼                                     ▼
SQLite store       CV pipeline                        Demo dataset
(SQLAlchemy)       (backend/app/cv/)                  (backend/data/demo/)
  images/            aligner → normalizer →            reference.png +
  annotations/       comparator → detector             5 test images + manifest
  inspections/       (OpenCV + scikit-image)
```

Everything runs on the operator's laptop — no cloud services, no API keys, no
internet dependency (see `README.md` "Offline operation details").

## Layers

1. **Frontend** (`frontend/`)
   - `src/App.tsx` — entry.
   - `src/components/Dashboard.tsx` — orchestrator: 4-step wizard
     (upload reference → name components → upload tests → inspect & review),
     theme toggle (dark/light), processing indicators, error banner, toasts.
   - `src/components/PCICanvas.tsx` — interactive canvas: draws board images,
     editable rectangles (draw/move/resize/select/delete) in annotation mode,
     status-colored overlays (present green / missing red / review amber) in
     results mode.
   - `src/components/UploadCard.tsx` — drag-and-drop upload card.
   - `src/components/ResultCard.tsx` — per-test results card: status pill, canvas
     with overlays, details table (name/status/confidence/explanation).
   - `src/components/StatusPill.tsx` — status badges + overall banner (green OK,
     red missing, yellow review).
   - `src/components/SettingsDialog.tsx` — threshold tuning UI.
   - `src/components/Toast.tsx` — bottom-right notifications.
   - `src/api/client.ts` — REST client (relative URLs, works when served by
     FastAPI; `vite.config.ts` proxies `/api` to the backend during dev).

2. **Backend API** (`backend/app/api/routes/`)
   - `health.py` — `GET /api/v1/health`
   - `reference.py` — reference upload, `GET /reference/latest`, image serving,
     annotations save/get.
   - `images.py` — test image upload, image serving, `GET /test/{id}`.
   - `inspection.py` — `POST /api/v1/inspection`, `GET /inspection/{id}`,
     JSON/CSV export endpoints.
   - `settings.py` — `GET/PUT /api/v1/settings` (thresholds).
   - `dataset.py` — `GET /api/v1/dataset/load` (one-click demo loader).

3. **Backend services** (`backend/app/services/`)
   - `image_service.py` — upload validation, file saving, DB registration.
   - `annotation_service.py` — atomic save/delete of component annotations
     (normalized coordinates).
   - `settings_service.py` — thresholds with validation.
   - `inspection_service.py` — orchestrates inspections; stores results JSON.
   - `export_service.py` — JSON/CSV export of inspection results.
   - `dataset_service.py` — demo dataset loader.

4. **CV pipeline** (`backend/app/cv/`, modular — each stage independently
   replaceable):
   - `aligner.py` — **registration**: ORB feature detection + Lowe-style ratio
     matching + RANSAC homography (`cv2.findHomography`), mapping test coords to
     reference coords; falls back to phase-correlation translation and finally
     identity warp. Reports `ok` so callers can escalate to "review".
   - `normalizer.py` — **lighting normalization**: CLAHE + percentile stretch;
     `clahe()` core reusable for the detector's shared-scale comparison.
   - `comparator.py` — **comparison primitives**: SSIM (`skimage.metrics.
     structural_similarity`), mean absolute pixel difference, Canny edge
     density, edge coverage between reference/test edges (with dilation),
     and "ring crops" (the area around the component — surrounding PCB context).
   - `detector.py` — **missing detection**: weighted "missing score"
     (0.40·diff_score + 0.30·ssim_gap + 0.15·edge_gap + 0.15·context_score),
     with verdict bands: present < 0.35, review < 0.60, missing ≥ 0.60.
     Per-component results carry status, confidence, explanation and the
     normalized bbox.
   - `pipeline.py` — **orchestration**: align → compare → detect.

5. **Database** (`backend/app/database/`)
   - `models.py` — `Image` (reference/test, file path, size, hash),
     `Annotation` (name + normalized bbox on the reference), `Inspection`
     (status + results JSON), `TestImage` (join table), `Setting` (thresholds).
   - `db.py` — SQLAlchemy 2.0 engine, session factory, `init_db()`.

6. **Static hosting** — `backend/app/main.py` mounts `frontend/dist`
   (`StaticFiles(html=True)`) when it exists; FastAPI serves the SPA.

## Data flow

1. Operator uploads reference → `POST /api/v1/reference` → row in `images`
   (kind=reference) + PNG in `backend/data/images/`.
2. Operator draws rectangles on the canvas → auto-saved via
   `POST /api/v1/reference/{id}/annotations` (normalized coordinates).
3. Operator uploads up to 3 test images → `POST /api/v1/test`.
4. `POST /api/v1/inspection {reference_image_id, test_image_ids}` → for each
   test image: grayscale load → ORB+homography alignment → normalize lighting →
   per-component compare (SSIM, diff, edge coverage, context ring) → verdict
   (present/missing/review). Results stored on the `Inspection` row.
5. Frontend renders: green/red/yellow status pills, highlights on the test
   images (same bboxes, in reference coordinates), tables of component
   verdicts; downloads JSON/CSV via `GET /api/v1/inspection/{id}/export`.
6. `GET /api/v1/settings` / `PUT` — tune thresholds live.

## Trade-offs (chosen / gave up / why)

| # | Decision | Chosen | Alternatives rejected | Why |
|---|----------|--------|----------------------|-----|
| 1 | Pipeline style | Classical OpenCV/scikit-image | Deep learning models | Assignment mandates a classical CV pipeline; offline-only runtime with no training data; deterministic and explainable (score + explanation per component). |
| 2 | Alignment | ORB + RANSAC homography | SIFT, AKAZE, template matching | ORB is patent-free, fast, and adequate for this scale; AKAZE is a close second but adds a dependency; homography (perspective) is more robust than pure translation. Phase-correlation is a cheap, verified fallback for translation-only cases. |
| 3 | Verdict logic | Multi-indicator score (diff + SSIM + edge coverage + context ring) with present/review/missing bands | Single-threshold pixel diff | Assignments' "avoid false missing due to lighting" requires redundancy: one weak indicator must not declare missing (review band instead). SSIM is needed because pixel diff is lighting-sensitive; edge coverage adds component structure evidence. |
| 4 | Lighting invariance | Per-ROI CLAHE + percentile stretch, plus mapping the test ROI onto the reference's percentile range | Global histogram matching | Local (per-ROI) normalization avoids whole-image bias; the shared scale keeps the reference/test ROIs comparable (found via debugging: per-image stretches produce false SSIM drops). |
| 5 | Persistence | SQLite via SQLAlchemy, images on disk | PostgreSQL, in-memory | Local single-user app; SQLAlchemy gives structure; data is disposable. |
| 6 | Threshold configurability | SQLite `settings` table + `GET/PUT /api/v1/settings` | Env-var-only, config file | Live tuning from the UI while demonstrating. |
| 7 | Serving the SPA | StaticFiles mount in FastAPI | Separate web server (nginx/Express) | One process, fewer moving parts; dev mode uses `vite` proxy. |
| 8 | DB access | `Depends(get_db)` sync sessions | async ORM | Local app; sync is simple and correct. |
| 9 | Tests | pytest (unit + API tests via `TestClient`) | unittest, hypothesis | Standard, fast, no extra infra. |
| 10 | Export | stdlib `csv` + `json` | pandas | No dependency for simple formats. |

## Diagram generation note

- Primary path: Archify skill, candidate at
  `.archify/architecture-pcb-inspector-20261119-1855/candidate.json`.
- Archify's `finalize` CLI was attempted multiple times but aborts with
  `finalize/receipt-publication` (`finalize-receipt-changed-during-inspection`);
  the skill was re-installed (the first install was interrupted) and the abort
  persists.
- Fallback used (documented in Archify's skill): hand-placed diagram generated by
  `backend/scripts/generate_architecture_html.py` from the verified candidate →
  `docs/architecture_diagram.html`.
