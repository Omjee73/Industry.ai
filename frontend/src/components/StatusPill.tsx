import React, { useEffect } from 'react';
import { AlertTriangle, CheckCircle } from 'lucide-react';

export type PillStatus = 'ok' | 'present' | 'missing' | 'review';

const STYLES: Record<PillStatus, string> = {
  ok: 'border-ok/20 bg-ok-soft text-ok',
  present: 'border-ok/20 bg-ok-soft text-ok',
  missing: 'border-missing/20 bg-missing-soft text-missing',
  review: 'border-review/20 bg-review-soft text-review',
};

export default function StatusPill({ status, className = '' }: { status: PillStatus; className?: string }) {
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-xs font-semibold uppercase tracking-wide ${STYLES[status]} ${className}`}
    >
      {(status === 'ok' || status === 'present') && <CheckCircle className="h-3 w-3" />}
      {status === 'missing' && <AlertTriangle className="h-3 w-3" />}
      {status === 'review' && <span className="h-2 w-2 rounded-full bg-current" />}
      {status}
    </span>
  );
}

/** Top-of-dashboard banner: green OK when nothing is missing, red/yellow otherwise. */
export function OverallBanner({
  status,
  missingCount,
  reviewCount,
}: {
  status: 'ok' | 'missing' | 'review';
  missingCount: number;
  reviewCount: number;
}) {
  if (status === 'ok') {
    return (
      <div className="flex items-center gap-4 rounded-xl border-2 border-ok bg-ok-soft px-5 py-4">
        <CheckCircle className="h-6 w-6 text-ok" />
        <div>
          <p className="text-base font-bold text-ok">All components present — OK</p>
          <p className="text-sm text-muted">
            No component marked missing in {missingCount === 0 ? 'any' : missingCount + ' board(s)'}.
          </p>
        </div>
      </div>
    );
  }
  if (status === 'review') {
    return (
      <div className="flex items-center gap-4 rounded-xl border-2 border-review bg-review-soft px-5 py-4">
        <AlertTriangle className="h-6 w-6 text-review" />
        <div>
          <p className="text-base font-bold text-review">Review needed</p>
          <p className="text-sm text-muted">
            {reviewCount} component{reviewCount !== 1 ? 's' : ''} could not be confirmed as present;
            check the explanations.
          </p>
        </div>
      </div>
    );
  }
  return (
    <div className="flex items-center gap-4 rounded-xl border-2 border-missing bg-missing-soft px-5 py-4">
      <AlertTriangle className="h-6 w-6 text-missing" />
      <div>
        <p className="text-base font-bold text-missing">
          {missingCount} missing component{missingCount !== 1 ? 's' : ''}
        </p>
        <p className="text-sm text-muted">
          Some components on the test images do not appear on the boards.
        </p>
      </div>
    </div>
  );
}

/** Simple auto-dismiss helper (used by Toast indirectly via setTimeout). */
export function useAutoDismiss(message: string, onClose: () => void, ms = 3200) {
  useEffect(() => {
    if (!message) return;
    const t = setTimeout(onClose, ms);
    return () => clearTimeout(t);
  }, [message, ms, onClose]);
}
