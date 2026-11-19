import React from 'react';
import { ChevronDown, ChevronUp } from 'lucide-react';
import type { TestImageResults } from '../types';
import PCICanvas from './PCICanvas';
import StatusPill, { type PillStatus } from './StatusPill';

/**
 * One test image in the results dashboard: status pill, canvas with the
 * status-colored missing/review overlays, and a details table (names,
 * confidence, explanations).
 */
export default function ResultCard({
  results,
  expanded,
  onToggleExpand,
}: {
  results: TestImageResults;
  expanded: boolean;
  onToggleExpand: () => void;
}) {
  const { image, status, results: comps } = results;
  const missingNames = comps.filter((c) => c.status === 'missing').map((c) => c.name);
  const reviewNames = comps.filter((c) => c.status === 'review').map((c) => c.name);
  const pillStatus: PillStatus = status;

  return (
    <div className="rounded-xl border-2 border-border bg-panel p-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <span className="font-semibold text-fg">Test image {image.id}</span>
          <StatusPill status={pillStatus} />
          <span className="text-xs font-mono text-subtle">
            {image.width}×{image.height}
          </span>
        </div>
        <button
          onClick={onToggleExpand}
          className="flex items-center gap-1.5 text-sm font-semibold text-muted hover:text-fg"
        >
          {expanded ? (
            <>
              Hide details <ChevronUp className="h-4 w-4" />
            </>
          ) : (
            <>
              Show details <ChevronDown className="h-4 w-4" />
            </>
          )}
        </button>
      </div>
      {missingNames.length > 0 && (
        <p className="mt-2 text-sm text-missing">
          Missing: <span className="font-semibold">{missingNames.join(', ')}</span>
        </p>
      )}
      {reviewNames.length > 0 && (
        <p className="mt-1 text-sm text-review">
          In question: <span className="font-semibold">{reviewNames.join(', ')}</span>
        </p>
      )}

      <PCICanvas
        editable={false}
        image={image}
        items={comps.map((c, i) => ({
          id: i + 1,
          name: c.name,
          x: c.bbox.x,
          y: c.bbox.y,
          width: c.bbox.width,
          height: c.bbox.height,
          status: c.status,
        }))}
        className="mt-4 max-w-full"
      />

      {expanded && comps.length > 0 && (
        <div className="mt-4 overflow-x-auto rounded-lg border border-border">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border bg-panel-elevated text-left text-xs uppercase tracking-wide text-muted">
                <th className="px-3 py-2">Component</th>
                <th className="px-3 py-2">Status</th>
                <th className="px-3 py-2">Confidence</th>
                <th className="px-3 py-2">Explanation</th>
              </tr>
            </thead>
            <tbody>
              {comps.map((c) => (
                <tr key={c.name} className="border-b border-border last:border-0">
                  <td className="px-3 py-2 font-mono text-fg">{c.name}</td>
                  <td className="px-3 py-2">
                    <StatusPill status={c.status} />
                  </td>
                  <td className="whitespace-nowrap px-3 py-2 font-mono text-muted">
                    {Math.round(c.confidence * 100)}%
                  </td>
                  <td className="max-w-xl px-3 py-2 text-muted">{c.explanation}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
