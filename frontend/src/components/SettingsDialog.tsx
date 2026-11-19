import React, { useEffect, useState } from 'react';

interface SettingsDialogProps {
  open: boolean;
  onClose: () => void;
  thresholds: Record<string, number>;
  defaults: Record<string, number>;
  onSave: (values: Record<string, number>) => void;
  busy?: boolean;
}

const THRESHOLD_META: Record<string, { label: string; help: string }> = {
  diff_ok: {
    label: 'Pixel difference (present)',
    help: 'Mean pixel difference between reference and test ROIs; below this value the component is considered present.',
  },
  diff_review: {
    label: 'Pixel difference (uncertain zone)',
    help: 'Above the OK value, where uncertain verdicts may be flagged as review.',
  },
  ssim_ok: {
    label: 'Structural similarity (present)',
    help: 'SSIM of the component ROIs; above this value the component is considered present.',
  },
  ssim_review: {
    label: 'Structural similarity (uncertain zone)',
    help: 'SSIM below the OK value contributes to the missing score.',
  },
  edge_ok: {
    label: 'Edge coverage (present)',
    help: 'Fraction of reference component edges found in the test image.',
  },
  edge_review: {
    label: 'Edge coverage (uncertain zone)',
    help: 'Below this coverage the edge indicator penalizes presence.',
  },
  context_veto: {
    label: 'Surrounding context (review veto)',
    help: 'If the area around a component differs by more than this, a missing verdict becomes review (uncertainty protection).',
  },
};

/** Modal for tuning the CV detection thresholds (stored server-side). */
export default function SettingsDialog({
  open,
  onClose,
  thresholds,
  defaults,
  onSave,
  busy = false,
}: SettingsDialogProps) {
  const [local, setLocal] = useState<Record<string, number>>(thresholds);

  // Re-sync local values whenever the dialog opens.
  useEffect(() => {
    if (open) setLocal({ ...thresholds });
  }, [open, thresholds]);

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [open, onClose]);

  if (!open) return null;

  const keys = Object.keys(THRESHOLD_META);

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4"
      onClick={onClose}
    >
      <div
        className="w-full max-w-xl rounded-xl border-2 border-border bg-panel p-6 shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        <h2 className="mb-1 text-xl font-bold text-fg">Inspection settings</h2>
        <p className="mb-5 text-sm text-muted">
          Tunable CV thresholds used to decide whether a component is present, missing or uncertain.
        </p>
        <div className="space-y-4">
          {keys.map((key) => (
            <div key={key} className="rounded-lg border border-border bg-panel-elevated p-3">
              <div className="flex items-baseline justify-between gap-3">
                <label className="text-sm font-semibold text-fg">{THRESHOLD_META[key].label}</label>
                <div className="flex items-center gap-2">
                  <input
                    type="number"
                    step="0.05"
                    min="0"
                    max="1"
                    value={local[key] ?? thresholds[key]}
                    onChange={(e) => {
                      const v = Number(e.target.value);
                      if (!Number.isNaN(v)) setLocal((l) => ({ ...l, [key]: v }));
                    }}
                    className="w-20 rounded-md border border-border bg-panel px-2 py-1 font-mono text-sm text-fg"
                  />
                  <span className="text-xs text-muted">
                    default {defaults[key]?.toFixed(3) ?? '-'}
                  </span>
                </div>
              </div>
              <p className="mt-1 text-xs text-muted">{THRESHOLD_META[key].help}</p>
            </div>
          ))}
        </div>
        <div className="mt-6 flex justify-end gap-2">
          <button
            type="button"
            onClick={() => setLocal({ ...thresholds })}
            className="rounded-lg border border-border px-3 py-2 text-sm text-muted hover:text-fg"
          >
            Reset to saved
          </button>
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg border border-border px-3 py-2 text-sm text-muted hover:text-fg"
          >
            Cancel
          </button>
          <button
            type="button"
            disabled={busy}
            onClick={() => onSave(local)}
            className="rounded-lg bg-primary px-3 py-2 text-sm font-semibold text-primary-fg disabled:opacity-60"
          >
            Save thresholds
          </button>
        </div>
      </div>
    </div>
  );
}
