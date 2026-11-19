# Research — PCB Missing Component Detection (Task B)

This document records what was researched before/while building the application,
with real sources. Everything below was fetched/verified during the session; raw
fetch logs and full GitHub API result pages are saved as:

- `docs_github_search.json` — GitHub API search results (all pages, full data)
- `docs_research_facts.txt` — verified doc-page facts (OpenCV, scikit-image, DeepPCB)

Note on environment: the `websearch` tool was unavailable/cancelled in this
session, so research used `webfetch` (GitHub REST API, OpenCV docs, scikit-image
docs, raw READMEs) and the GitHub API — all real network sources.

## Research method

1. **Existing open-source projects** — queried the GitHub REST API
   (`api.github.com/search/repositories`) with these queries (sorted by stars):
   - `"DeepPCB dataset PCB defect detection"`
   - `"PCB defect detection OpenCV missing component"`
   - `"PCB visual inspection OpenCV"`
   Scripts: `backend/scripts/research_github.py` (compact summaries),
   `backend/scripts/research_verify.py` (URL verification), `backend/scripts/research_deeppcb.py`
   (canonical dataset README).
2. **Docs verification** — fetched and checked:
   - OpenCV calib3d group page (`https://docs.opencv.org/4.x/d9/d0c/group__calib3d.html`, verified mentions `findHomography`)
   - scikit-image metrics page (`https://scikit-image.org/docs/stable/api/skimage.metrics.html`, verified mentions `structural_similarity`)
3. **PCB datasets** — fetched `https://raw.githubusercontent.com/tangsanli5201/DeepPCB/master/README.md` (verified).

## Existing tools and projects (verified, ranked by fit)

| Project | Stars | Description (from repo) | Relevance |
|---|---|---|---|
| [tangsanli5201/DeepPCB](https://github.com/tangsanli5201/DeepPCB) | 580 | "A PCB defect dataset." — the canonical DeepPCB dataset referenced by many projects | Dataset facts below |
| [VanillaHours/pcbDefectDetectionYOLO](https://github.com/VanillaHours/pcbDefectDetectionYOLO) | 26 | "PCB defect detection using YOLOv3, on DeepPCB dataset." | Deep learning alternative (not chosen) |
| [Ahsan-Neural/pcb-defect-detection](https://github.com/Ahsan-Neural/pcb-defect-detection) | 0 | "Real-time PCB manufacturing defect detection using YOLOv8s. 95.3% mAP@50 on DeepPCB benchmark." | Benchmark + DL alternative |
| [stephrs/DeepPCB-Defect-Detection-YOLOv8](https://github.com/stephrs/DeepPCB-Defect-Detection-YOLOv8) | 0 | "Real-time microscopic defect detection pipeline for Printed Circuit Boards (PCB) using YOLOv8-Nano. Built for Automated Optical Inspection (AOI) in smart manufacturing." | DL alternative + AOI context |
| [moszer/PCB_DETECT_RMUTT_GUI](https://github.com/moszer/PCB_DETECT_RMUTT_GUI) | 1 | "PCB defect inspection station — YOLO detection matched against a reference profile to give PASS/FAIL verdicts with missing, wrong and extra components. PyQt6 desktop app with live camera. RMUTT project." | Closest to our concept: missing/extra vs reference → PASS/FAIL |
| [jaya1240/pcb-fault-detection-tracking-system](https://github.com/jaya1240/pcb-fault-detection-tracking-system) | 0 | "Built a full-stack PCB inspection pipeline using OpenCV ORB feature alignment and contour-based image diffing to automatically detect and classify defects (missing holes, shorts, open circuits) against a golden reference image. Designed a linked component inventory module (stock tracking...)." | Closest classical pipeline: ORB + reference image diffing |
| [archocron/opencv-pcb-fiducials](https://github.com/archocron/opencv-pcb-fiducials) | 0 | "Python project using OpenCV to detect fiducials and rotate to the correct angle and cutoff. To be applicated in combination with visual inspection projects." | Alignment-relevant: fiducial detection |
| [Emrebyrktr/DeepPCB-Surface-Defect-Detection](https://github.com/Emrebyrktr/DeepPCB-Surface-Defect-Detection) | 0 | PCB Dataset with Hardware trojan (chipsets) | Related dataset |
| [Shaswathisanjana/PCB-Defect-Detection-using-LightYOLOv11](https://github.com/Shaswathisanjana/PCB-Defect-Detection-using-LightYOLOv11) | 0 | "PCB Defect Detection using LightYOLOv11 on the DeepPCB Dataset" | DL alternative |

## Datasets

### DeepPCB (canonical, `tangsanli5201/DeepPCB`) — verified facts from its README

- **1,500 image pairs**: each pair is a defect-free template image and an aligned tested image with ground-truth annotations.
- **6 most common defect types**: open, short, mousebite, spur, pin hole and spurious copper.
- **Capture**: linear scan CCD at ~48 px/mm; original images ~16k×16k px, cropped into 640×640 sub-images.
- **Annotations**: `x1,y1,x2,y2` bounding boxes + integer type ID (0 = background, …).
- The same dataset is cited by projects like `VanillaHours/pcbDefectDetectionYOLO` ("on DeepPCB dataset").

This app models the same problem space: a good reference board + test photos of the same board, with named components and missing-part verdicts — but built as a classical OpenCV/Python offline pipeline (assignment requirement), and it extends DeepPCB's template-vs-test idea with interactive, user-named component annotations.

*(Could not verify the DeepPCB paper citation via web search in this environment; the dataset repo above is the canonical, verified source.)*

### Other datasets

- `lonlonago/DeepPCB-PCB-Board-Defect-Detection-Data-Set-1500-Images-in-6-Categories` — "dataset page (readme + preview images)".

## Algorithms and alternatives

### Alignment / registration (feature-based)

**Chosen:** ORB + ratio-tested matching + RANSAC homography (`cv2.findHomography`),
`cv2.warpPerspective(test, H, ref_size)` where `H` maps test coords → ref coords
(verified empirically — see below); fallback chain: phase correlation
(`cv2.phaseCorrelate`, verified sign convention) → identity warp.

- **ORB (OpenCV, `cv2.ORB_create`)**: nfeatures=8000, scaleFactor=1.15, nlevels=6 — patent-free, fast, adequate for our scale; unit-tested with translations and rotation+scale.
- **AKAZE**: also OpenCV; better repeatability in some scenes but patent expired long ago and less battle-tested in this configuration; not needed here.
- **SIFT**: more features/slower; historically patent-encumbered; a drop-in alternative.
- **ECC (`cv2.findTransformECC`, MOTION_EUCLIDEAN/AFFINE)**: classic registration method requiring a decent initial guess; for pure translation/rotation cases our ORB path already covers it.
- **Phase correlation**: verified here with a controlled warp: for `test = warpAffine(ref, [[1,0,37],[0,1,-22]])`, `cv2.phaseCorrelate(ref, test)` returns `(37, -22)`; aligning with `warpAffine(test, [[1,0,-dx],[0,1,-dy]])` reproduces `ref` exactly (mean abs diff 0.0).

### Lighting normalization

**Chosen:** CLAHE (`cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8,8))`) + percentile stretch (1%/99%).

- **Why CLAHE:** robust local contrast equalization handles uneven PCB illumination; histogram equalization (global) is content-sensitive; per-tile CLAHE is the standard OpenCV choice for camera scenes.
- **Detail discovered during development:** percentiles must be computed on the CLAHE output of the *reference* ROI and applied to both images (shared scale). Per-image stretches produce systematic brightness differences that inflate the SSIM gap (SSIM 0.31 between near-identical synthetic boards). Evidence: excerpt 2 in AI_COLLAB.md.

### Missing detection (classical, per component ROI)

**Chosen:** weighted multi-indicator score:

```
diff_score  = min(mean_abs_diff / diff_ok, 1)                  # pixel difference
ssim_gap    = clip((ssim_ok - ssim) / (ssim_ok - ssim_review),0,1)   # structural similarity
edge_gap    = clip((edge_ok - edge_cov) / (edge_ok - edge_review),0,1)  # edge coverage
context_score = min(ring_diff / context_veto, 1)               # surrounding PCB context
missing = 0.40·diff_score + 0.30·ssim_gap + 0.15·edge_gap + 0.15·context_score
```

Bands: **present** if missing < 0.40, **review** if < 0.60, **missing** ≥ 0.60.
Thresholds are user-configurable (see RESEARCH "rejected alternatives").

**Alternatives compared:**

- **Pixel-diff-only (MSE/MAE):** too lighting-sensitive. Verified in this project: with brightness/noise changes, diff-based scores flagged present components as missing. Rejected.
- **SSIM alone:** can be low even for identical boards in this project due to normalization artifacts (see the "SSIM 0.31" debugging above); combined with diff/edges it is robust. Kept as one of four indicators.
- **Edge coverage only:** detects "pattern gone" but misses flat patterns; kept as one indicator (20% weight).
- **Context ring diff:** guards against misalignment; adds 20%.
- **DeepPCB-style template differencing** (differencing test against the template, contour-based): the dataset's own approach — standard and effective, but requires pixel-perfect alignment and binarization; our classical evidence-based detector is chosen for explainability and for avoiding "declared missing from a single signal".
- **Deep-learning approaches** (the projects above): rejected — assignment mandates a classical pipeline; no training data; offline.

### Comparison primitives

- **SSIM:** `skimage.metrics.structural_similarity` — verified docs page: https://scikit-image.org/docs/stable/api/skimage.metrics.html (Wang et al., "Image quality assessment: from error visibility to structural similarity", IEEE TIP 2004 — the canonical SSIM paper).
- **Edges:** `cv2.Canny` + dilated coverage between reference and test edge maps.
- **Alternatives rejected:** PSNR/MSE (less structural), FSIM (adds gradient-phase; not needed).

### Database

- **Chosen:** SQLite via SQLAlchemy 2.0 (`backend/app/database/`).
- Alternatives: PostgreSQL (overkill, no concurrency, local app), plain `sqlite3` stdlib (valid alternative; SQLAlchemy chosen for declarative models, transactions, ORM-style session handling).

### Architecture diagram

- **Chosen:** Archify skill + hand-placed fallback (see ARCHITECTURE.md "Diagram generation note").
- Alternatives: Mermaid (architecture-ish), hand-drawn SVG, D2/PlantUML — Archify was preferred for polish; the hand-placed fallback followed Archify's documented "shell unavailable" path.

## Facts vs decisions

- **Facts (researched):** everything in the projects table, the DeepPCB README facts, OpenCV/scikit-image doc facts (verified URLs above).
- **Project decisions (not researched):** the weighted score formula and thresholds, the exact normalization details, ORB parameters, SQLite+SQLAlchemy choice, serving the SPA via `StaticFiles`, the 4-step wizard UX, testing strategy — these are engineering decisions documented in ARCHITECTURE.md and AI_COLLAB.md.
