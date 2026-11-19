import React, { useCallback, useEffect, useRef, useState } from 'react';
import {
  AlertTriangle,
  Download,
  Loader2,
  Moon,
  Pencil,
  ScanSearch,
  Settings,
  Sun,
  Trash2,
  Upload,
} from 'lucide-react';

import * as api from '../api/client';
import type { Annotation, InspectionDetail, TestImageResults } from '../types';
import PCICanvas from './PCICanvas';
import UploadCard from './UploadCard';
import Toast from './Toast';
import SettingsDialog from './SettingsDialog';
import ResultCard from './ResultCard';
import StatusPill, { OverallBanner } from './StatusPill';

interface ReferenceState {
  id: number;
  url: string;
  width: number;
  height: number;
  annotations: Annotation[];
}

interface TestImageState {
  id: number;
  url: string;
  width: number;
  height: number;
}

interface RenameState {
  id: number;
  name: string;
}

const STEPS = [
  { id: 1, title: 'Upload reference board' },
  { id: 2, title: 'Name the components' },
  { id: 3, uploads: 3, title: 'Upload test images' },
  { id: 4, title: 'Inspect & review' },
] as const;

export default function Dashboard() {
  const [dark, setDark] = useState<boolean>(() => {
    try {
      const saved = window.localStorage.getItem('pcb-theme');
      if (saved === 'dark' || saved === 'light') return saved === 'dark';
    } catch {
      /* ignore */
    }
    return false; // default: professional grey/white theme
  });
  const [step, setStep] = useState(1);
  const [reference, setReference] = useState<ReferenceState | null>(null);
  const [tests, setTests] = useState<TestImageState[]>([]);
  const [inspection, setInspection] = useState<InspectionDetail | null>(null);
  const [processing, setProcessing] = useState<string | null>(null);
  const [uploadingTest, setUploadingTest] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [toast, setToast] = useState<string | null>(null);
  const [rename, setRename] = useState<RenameState | null>(null);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [expandedTest, setExpandedTest] = useState<number | null>(null);
  const [thresholds, setThresholds] = useState<Record<string, number>>({});
  const [defaults, setDefaults] = useState<Record<string, number>>({});
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [demoLoading, setDemoLoading] = useState(false);
  const lastSavedRef = useRef<string>('');

  useEffect(() => {
    try {
      window.localStorage.setItem('pcb-theme', dark ? 'dark' : 'light');
    } catch {
      /* ignore */
    }
    document.documentElement.classList.toggle('dark', dark);
  }, [dark]);

  const toastMsg = useCallback((msg: string) => setToast(msg), []);

  // Load thresholds on mount.
  useEffect(() => {
    api
      .getSettings()
      .then((s) => {
        setThresholds(s.thresholds);
        setDefaults(s.defaults);
      })
      .catch(() => {
        /* backend down; settings UI will retry when opened */
      });
  }, []);

  const saveAnnotations = useCallback(
    async (list: Annotation[]) => {
      if (!reference) return;
      lastSavedRef.current = JSON.stringify(list);
      try {
        const saved = await api.saveAnnotations(reference.id, list);
        setReference((r) => (r ? { ...r, annotations: saved } : r));
      } catch (e) {
        toastMsg(`Could not save annotations: ${e instanceof Error ? e.message : String(e)}`);
      }
    },
    [reference, toastMsg]
  );

  // Auto-save annotations shortly after they change (debounced).
  useEffect(() => {
    if (!reference) return;
    const key = JSON.stringify(reference.annotations);
    if (lastSavedRef.current === key) return;
    const t = setTimeout(() => void saveAnnotations(reference.annotations), 450);
    return () => clearTimeout(t);
  }, [reference?.annotations, saveAnnotations]);

  const handleReferenceUpload = async (file: File) => {
    setProcessing('Uploading reference image…');
    try {
      const info = await api.uploadReference(file);
      setReference({
        id: info.id,
        url: api.referenceImageUrl(info.id),
        width: info.width,
        height: info.height,
        annotations: [],
      });
      setTests([]);
      setInspection(null);
      setSelectedId(null);
      setStep(2);
      toastMsg(`Reference uploaded: ${info.width}×${info.height}`);
    } catch (e) {
      setError(api.errorMessage(e));
    } finally {
      setProcessing(null);
    }
  };

  const handleLoadDemo = async () => {
    setProcessing('Loading demo dataset…');
    try {
      const data = await api.loadDemoDataset();
      const latest = await api.getLatestReference();
      setReference({
        id: data.reference_id,
        url: api.referenceImageUrl(data.reference_id),
        width: latest.width,
        height: latest.height,
        annotations: data.annotations,
      });
      const testsOut: TestImageState[] = [];
      for (const tid of data.test_ids) {
        const info = await api.getTestImage(tid);
        testsOut.push({ id: tid, url: api.testImageUrl(tid), width: info.width, height: info.height });
      }
      // The backend allows at most 3 test images per inspection: show the first 3.
      setTests(testsOut.slice(0, 3));
      setStep(2);
      toastMsg(
        testsOut.length > 3
          ? `${data.message} (showing 3 of ${testsOut.length} test images — max 3 per inspection)`
          : data.message
      );
    } catch (e) {
      setError(api.errorMessage(e));
    } finally {
      setProcessing(null);
      setDemoLoading(false);
    }
  };

  const handleTestUpload = async (file: File, slot: number) => {
    if (!reference) {
      setError('Upload a reference image first.');
      return;
    }
    setUploadingTest(slot);
    setProcessing(`Uploading test image ${slot}…`);
    try {
      const info = await api.uploadTest(file);
      setTests((prev) => {
        if (prev.length >= 3) return prev;
        return [...prev, { id: info.id, url: api.testImageUrl(info.id), width: info.width, height: info.height }];
      });
      toastMsg(`Test image ${slot} uploaded: ${info.width}×${info.height}`);
    } catch (e) {
      setError(api.errorMessage(e));
    } finally {
      setProcessing(null);
      setUploadingTest(null);
    }
  };

  const handleAnnotationsChange = useCallback(
    (list: Annotation[]) => {
      setReference((r) => (r ? { ...r, annotations: list } : r));
    },
    []
  );

  const handleRenameSave = async () => {
    if (!reference || !rename) return;
    const name = rename.name.trim() || `Unnamed ${rename.id}`;
    const list = reference.annotations.map((a) => (a.id === rename.id ? { ...a, name } : a));
    setRename(null);
    await saveAnnotations(list);
  };

  const handleDeleteAnnotation = async (id: number) => {
    if (!reference) return;
    const list = reference.annotations.filter((a) => a.id !== id);
    setSelectedId(null);
    setReference((r) => (r ? { ...r, annotations: list } : r));
    await saveAnnotations(list);
  };

  const handleInspect = async () => {
    if (!reference) {
      setError('Upload a reference image first.');
      return;
    }
    if (tests.length === 0) {
      setError('Upload at least one test image.');
      return;
    }
    setProcessing('Running inspection…');
    try {
      const detail = await api.runInspection({
        reference_image_id: reference.id,
        test_image_ids: tests.map((t) => t.id),
      });
      setInspection(detail);
      setStep(4);
      toastMsg('Inspection completed');
    } catch (e) {
      setError(api.errorMessage(e));
    } finally {
      setProcessing(null);
    }
  };

  const handleExport = async (format: 'json' | 'csv') => {
    if (!inspection) return;
    setProcessing(`Preparing ${format.toUpperCase()} export…`);
    try {
      await api.downloadExport(inspection.id, format);
    } catch (e) {
      setError(api.errorMessage(e));
    } finally {
      setProcessing(null);
    }
  };

  const results: TestImageResults[] =
    inspection?.testImages ?? [];
  const missingCount = results.reduce((n, t) => n + t.results.filter((r) => r.status === 'missing').length, 0);
  const reviewCount = results.reduce((n, t) => n + t.results.filter((r) => r.status === 'review').length, 0);
  const overallStatus: TestImageResults['status'] = results.some((t) => t.status === 'missing')
    ? 'missing'
    : results.some((t) => t.status === 'review')
      ? 'review'
      : 'ok';

  const renameInputId = rename?.id;
  void renameInputId;

  return (
    <div className="min-h-screen bg-bg text-fg antialiased">
      {/* Header */}
      <header className="sticky top-0 z-20 border-b-2 border-border bg-panel/95 backdrop-blur">
        <div className="mx-auto flex max-w-screen-2xl items-center justify-between gap-4 px-4 py-3">
          <div className="flex items-center gap-3">
            <ScanSearch className="h-6 w-6 text-primary" />
            <h1 className="text-xl font-bold tracking-tight">PCB Missing Component Detection</h1>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setSettingsOpen(true)}
              title="Inspection settings"
              className="rounded-lg border border-border p-2 text-muted hover:text-fg"
            >
              <Settings className="h-5 w-5" />
            </button>
            <button
              onClick={() => setDark((d) => !d)}
              title={dark ? 'Switch to light theme' : 'Switch to dark theme'}
              className="rounded-lg border border-border p-2 text-muted hover:text-fg"
            >
              {dark ? <Sun className="h-5 w-5" /> : <Moon className="h-5 w-5" />}
            </button>
          </div>
        </div>
      </header>

      {/* Main layout */}
      <main className="mx-auto grid max-w-screen-2xl gap-6 px-4 py-6 md:grid-cols-[280px_minmax(0,1fr)]">
        {/* Sidebar */}
        <aside className="flex flex-col gap-4">
          <nav className="rounded-xl border-2 border-border bg-panel p-4">
            <h2 className="mb-3 text-sm font-semibold text-fg">Workflow</h2>
            <ol className="space-y-2">
              {STEPS.map((s) => {
                const done = s.id < step;
                const active = s.id === step;
                return (
                  <li key={s.id}>
                    <button
                      onClick={() => {
                        if (s.id >= 1 && s.id <= 3 || (s.id === 4 && inspection)) setStep(s.id);
                      }}
                      className={`flex w-full items-center gap-3 rounded-lg px-3 py-2 text-left text-sm transition-colors ${
                        active
                          ? 'bg-primary/10 font-semibold text-fg'
                          : done
                            ? 'text-fg hover:bg-panel-elevated'
                            : 'text-muted hover:bg-panel-elevated'
                      }`}
                    >
                      <span
                        className={`flex h-6 w-6 items-center justify-center rounded-full border-2 text-xs font-bold ${
                          done ? 'border-ok bg-ok/15 text-ok' : active ? 'border-primary text-primary' : 'border-border text-subtle'
                        }`}
                      >
                        {done ? '✓' : s.id}
                      </span>
                      {s.title}
                    </button>
                  </li>
                );
              })}
            </ol>
          </nav>

          {reference && (
            <div className="rounded-xl border-2 border-border bg-panel p-4">
              <h3 className="mb-3 text-sm font-semibold text-fg">
                Component inventory ({reference.annotations.length})
              </h3>
              <ul className="space-y-1">
                {reference.annotations.map((a) => (
                  <li key={a.id} className="flex items-center gap-2 rounded-lg px-2 py-1.5">
                    <button
                      onClick={() => setSelectedId(a.id)}
                      className="flex min-w-0 flex-1 items-center gap-2 text-left"
                    >
                      <span className="h-2.5 w-2.5 shrink-0 rounded-full bg-primary" />
                      {rename && rename.id === a.id ? (
                        <input
                          autoFocus
                          value={rename.name}
                          onChange={(e) => setRename({ id: rename.id, name: e.target.value })}
                          onKeyDown={(e) => {
                            if (e.key === 'Enter') void handleRenameSave();
                            if (e.key === 'Escape') setRename(null);
                          }}
                          onBlur={() => void handleRenameSave()}
                          className="w-full rounded border border-primary bg-panel px-1.5 py-0.5 text-sm text-fg"
                        />
                      ) : (
                        <span className="truncate text-sm text-fg">{a.name || 'Unnamed'}</span>
                      )}
                    </button>
                    <button
                      onClick={() => setRename({ id: a.id, name: a.name })}
                      title="Rename"
                      className="rounded p-1 text-muted hover:text-fg"
                    >
                      <Pencil className="h-3.5 w-3.5" />
                    </button>
                    <button
                      onClick={() => void handleDeleteAnnotation(a.id)}
                      title="Delete"
                      className="rounded p-1 text-muted hover:text-missing"
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </button>
                  </li>
                ))}
                {reference.annotations.length === 0 && (
                  <p className="text-xs text-muted">Draw rectangles on the board, then name them.</p>
                )}
              </ul>
            </div>
          )}

          {reference && step === 3 && (
            <div className="rounded-xl border-2 border-border bg-panel p-4">
              <h3 className="mb-2 text-sm font-semibold text-fg">Uploaded test images ({tests.length}/3)</h3>
              <ul className="space-y-2">
                {tests.map((t, i) => (
                  <li key={t.id} className="flex items-center gap-2 text-sm text-fg">
                    <img
                      src={t.url}
                      alt={`Test ${t.id}`}
                      className="h-10 w-14 rounded border-2 border-border object-cover"
                    />
                    Test image {i + 1} — {t.width}×{t.height}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </aside>

        {/* Step content */}
        <section className="min-w-0">
          {error && (
            <div className="mb-6 flex items-start gap-3 rounded-xl border-2 border-missing bg-missing-soft p-4" role="alert">
              <AlertTriangle className="mt-0.5 h-5 w-5 shrink-0 text-missing" />
              <div>
                <p className="font-semibold text-missing">Something went wrong</p>
                <p className="text-sm text-fg">{error}</p>
              </div>
              <button onClick={() => setError(null)} className="ml-auto text-sm text-missing hover:underline">
                Dismiss
              </button>
            </div>
          )}

          {step === 1 && (
            <div>
              <h2 className="mb-4 text-2xl font-bold">Step 1 — Upload the reference board</h2>
              <p className="mb-6 text-sm text-muted">
                Upload a photo of the good board. You will name each component next.
              </p>
              <UploadCard
                title="Upload reference board"
                subtitle="PNG, JPG or WEBP — same view for all test images"
                onFile={handleReferenceUpload}
                busy={processing === 'Uploading reference image…'}
              />
              <div className="mt-4 flex items-center gap-3">
                <button
                  onClick={() => void handleLoadDemo()}
                  disabled={demoLoading}
                  className="flex items-center gap-2 rounded-lg border-2 border-primary bg-primary/10 px-4 py-3 text-sm font-semibold text-primary hover:bg-primary/15 disabled:cursor-not-allowed disabled:opacity-60"
                >
                  {demoLoading ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : (
                    <ScanSearch className="h-4 w-4" />
                  )}
                  Or load the bundled demo dataset
                </button>
              </div>
              <p className="mt-4 text-sm text-muted">
                Offline-only app. Images stay on your device.
              </p>
            </div>
          )}

          {step === 2 && reference && (
            <div>
              <h2 className="mb-4 text-2xl font-bold">Step 2 — Name the components on the reference board</h2>
              <p className="mb-4 text-sm text-muted">
                Click and drag on the board to draw a rectangle around each part. Drawings become the
                named inventory used to find missing parts later. You can reposition or delete them.
              </p>
              <PCICanvas
                editable
                image={reference}
                items={reference.annotations}
                selectedId={selectedId}
                onSelect={setSelectedId}
                onChange={handleAnnotationsChange}
                onDelete={(id) => {
                  setSelectedId(null);
                  setReference((r) => (r ? { ...r, annotations: r.annotations.filter((a) => a.id !== id) } : r));
                }}
                className="max-w-full"
              />
              <div className="mt-4 rounded-xl border-2 border-border bg-panel p-3">
                <h3 className="mb-2 text-sm font-semibold text-fg">Named components ({reference.annotations.length})</h3>
                {reference.annotations.length > 0 ? (
                  <table className="w-full text-sm">
                    <tbody>
                      {reference.annotations.map((a) => (
                        <tr key={a.id} className="border-t border-border first:border-0">
                          <td className="py-1.5 font-mono text-fg">{a.name || 'Unnamed'}</td>
                          <td className="py-1.5 text-right text-muted">
                            x{(a.x * reference.width).toFixed(0)}, y{(a.y * reference.height).toFixed(0)} — {(a.width * reference.width).toFixed(0)}×{(a.height * reference.height).toFixed(0)} px
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                ) : (
                  <p className="text-sm text-muted">No components named yet.</p>
                )}
              </div>
              <div className="mt-6 flex items-center justify-between">
                <button
                  onClick={() => setStep(1)}
                  className="rounded-lg border-2 border-border px-4 py-2 text-sm font-semibold text-muted hover:text-fg"
                >
                  Back
                </button>
                <button
                  onClick={() => setStep(3)}
                  disabled={reference.annotations.length === 0}
                  className="rounded-lg bg-primary px-5 py-2 text-sm font-semibold text-primary-fg disabled:cursor-not-allowed disabled:opacity-50"
                >
                  Continue
                </button>
              </div>
            </div>
          )}

          {step === 3 && reference && (
            <div>
              <h2 className="mb-4 text-2xl font-bold">Step 3 — Upload test images</h2>
              <p className="mb-6 text-sm text-muted">
                Upload up to 3 photos of the same board taken from the same viewpoint.
              </p>
              <div className="grid gap-4 sm:grid-cols-3">
                {[1, 2, 3].map((slot) => (
                  <UploadCard
                    key={slot}
                    title={`Test Image ${slot}`}
                    subtitle={tests.length >= slot ? 'Uploaded — ready' : 'PNG, JPG or WEBP'}
                    icon={<Upload className="h-6 w-6 text-muted" />}
                    onFile={(file) => void handleTestUpload(file, slot)}
                    busy={uploadingTest === slot}
                  />
                ))}
              </div>
              <p className="mt-4 text-sm text-muted">
                Uploaded: <span className="font-semibold">{tests.length}</span>/3
              </p>
              <div className="mt-6 flex items-center justify-between">
                <button
                  onClick={() => setStep(2)}
                  className="rounded-lg border-2 border-border px-4 py-2 text-sm font-semibold text-muted hover:text-fg"
                >
                  Back
                </button>
                <button
                  onClick={() => setStep(4)}
                  disabled={tests.length === 0}
                  className="rounded-lg bg-primary px-5 py-2 text-sm font-semibold text-primary-fg disabled:cursor-not-allowed disabled:opacity-50"
                >
                  Continue to inspection
                </button>
              </div>
            </div>
          )}

          {step === 4 && (
            <div>
              <h2 className="mb-4 text-2xl font-bold">Step 4 — Inspection results</h2>
              {inspection ? (
                <>
                  <OverallBanner status={overallStatus} missingCount={missingCount} reviewCount={reviewCount} />
                  <div className="mt-6 space-y-5">
                    {results.map((t, i) => (
                      <ResultCard
                        key={t.testImageId}
                        results={t}
                        expanded={expandedTest === t.testImageId}
                        onToggleExpand={() => setExpandedTest((cur) => (cur === t.testImageId ? null : t.testImageId))}
                      />
                    ))}
                  </div>
                  <div className="mt-6 flex flex-wrap gap-3">
                    <button
                      onClick={() => void handleExport('json')}
                      className="flex items-center gap-2 rounded-lg border-2 border-border px-4 py-2 text-sm font-semibold text-fg hover:bg-panel-elevated"
                    >
                      <Download className="h-4 w-4" />
                      Download JSON
                    </button>
                    <button
                      onClick={() => void handleExport('csv')}
                      className="flex items-center gap-2 rounded-lg border-2 border-border px-4 py-2 text-sm font-semibold text-fg hover:bg-panel-elevated"
                    >
                      <Download className="h-4 w-4" />
                      Download CSV
                    </button>
                  </div>
                  <p className="mt-3 text-sm text-muted">
                    Red = missing, yellow = review, green = present.
                  </p>
                </>
              ) : (
                <div className="flex flex-col items-center gap-4 rounded-xl border-2 border-dashed border-border bg-panel p-8 text-center">
                  <Loader2 className="h-8 w-8 animate-spin text-primary" />
                  <p className="text-sm text-muted">
                    Run the inspection to see missing components on your test images.
                  </p>
                  <button
                    onClick={() => handleInspect()}
                    disabled={tests.length === 0 || !reference}
                    className="rounded-lg bg-primary px-5 py-2 text-sm font-semibold text-primary-fg disabled:cursor-not-allowed disabled:opacity-50"
                  >
                    Run inspection
                  </button>
                </div>
              )}
            </div>
          )}
        </section>
      </main>

      {/* Processing indicator */}
      {processing && (
        <div className="fixed bottom-6 left-1/2 z-40 -translate-x-1/2 rounded-xl border border-border bg-panel px-4 py-3 text-sm font-medium text-fg shadow-xl">
          <span className="mr-2 inline-block h-4 w-4 animate-spin rounded-full border-2 border-primary border-t-transparent align-middle" />
          {processing}
        </div>
      )}

      <Toast message={toast ?? ''} onClose={() => setToast(null)} />

      <SettingsDialog
        open={settingsOpen}
        onClose={() => setSettingsOpen(false)}
        thresholds={thresholds}
        defaults={defaults}
        onSave={(values) => {
          api
            .updateSettings(values)
            .then((s) => {
              setThresholds(s.thresholds);
              setDefaults(s.defaults);
              toastMsg('Inspection settings saved');
            })
            .catch((e) => setError(e instanceof Error ? e.message : String(e)))
            .finally(() => setSettingsOpen(false));
        }}
      />
    </div>
  );
}
