import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';

/** Item drawn on the canvas: a named, normalized rectangle (+ optional status). */
export interface OverlayItem {
  id: number;
  name: string;
  x: number;
  y: number;
  width: number;
  height: number;
  status?: ComponentStatus;
  selected?: boolean;
}

export type ComponentStatus = 'present' | 'missing' | 'review';

export const STATUS_COLORS: Record<ComponentStatus, string> = {
  present: '#16A34A', // green
  missing: '#DC2626', // red
  review: '#D97706', // amber
};

const BASE_COLOR = '#60A5FA';
const SELECTED_COLOR = '#2563EB';
const HIT_PADDING = 6;
const HANDLE_SIZE = 8;
const MIN_SIZE = 0.01;

type Dir = 'n' | 's' | 'e' | 'w' | 'ne' | 'nw' | 'se' | 'sw' | 'm';

interface MoveDrag {
  id: number;
  startX: number;
  startY: number;
  x: number;
  y: number;
}

interface ResizeDrag {
  id: number;
  dir: Dir;
  startX: number;
  startY: number;
  x: number;
  y: number;
  w: number;
  h: number;
}

interface PCICanvasProps {
  image: { id: number; url: string; width: number; height: number };
  items: OverlayItem[];
  editable?: boolean;
  selectedId?: number | null;
  onSelect?: (id: number | null) => void;
  onDelete?: (id: number) => void;
  onChange?: (items: OverlayItem[]) => void;
  className?: string;
}

/**
 * Draws a board image on a canvas with rectangles (component annotations or
 * detection overlays). In editable mode it supports drawing, moving, resizing
 * and selecting rectangles (keyboard-free); in read-only mode it is an
 * overlay canvas with status-colored highlights.
 */
export default function PCICanvas({
  image,
  items,
  editable = false,
  selectedId = null,
  onSelect,
  onDelete,
  onChange,
  className = '',
}: PCICanvasProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const imgElRef = useRef<HTMLImageElement | null>(null);
  const [measureVersion, setMeasureVersion] = useState(0);
  const [moveDrag, setMoveDrag] = useState<MoveDrag | null>(null);
  const [resizeDrag, setResizeDrag] = useState<ResizeDrag | null>(null);
  const [ghost, setGhost] = useState<OverlayItem | null>(null);

  // The canvas is displayed at natural size; scale shrinks large images to fit.
  const scale = useMemo(() => {
    const el = containerRef.current;
    if (!el || !image.width) return 1;
    const avail = el.clientWidth - 32;
    return Math.max(0.25, Math.min(2, avail / image.width));
  }, [measureVersion, image.width]);

  const dispW = image.width * scale;
  const dispH = image.height * scale;

  const toNorm = useCallback((x: number, y: number) => ({ x: x / dispW, y: y / dispH }), [dispW, dispH]);

  // Redraw whenever anything relevant changes.
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas || !image.width || !image.height || !dispW) return;
    canvas.width = Math.round(dispW);
    canvas.height = Math.round(dispH);
    const ctx = canvas.getContext('2d');
    if (!ctx) return;
    const img = imgElRef.current;
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    if (img) ctx.drawImage(img, 0, 0, canvas.width, canvas.height);

    const drawItem = (it: OverlayItem) => {
      const x = it.x * dispW;
      const y = it.y * dispH;
      const w = Math.max(it.width * dispW, 1);
      const h = Math.max(it.height * dispH, 1);
      const color = it.status
        ? STATUS_COLORS[it.status]
        : it.selected
          ? SELECTED_COLOR
          : BASE_COLOR;
      ctx.strokeStyle = color;
      ctx.lineWidth = it.selected ? 3 : 2.5;
      ctx.strokeRect(x, y, w, h);
      const label = it.name
        ? it.status
          ? `${it.name} [${it.status}]`
          : it.name
        : it.status
          ? `[${it.status}]`
          : '';
      if (label) {
        const tw = Math.min(w, 260);
        ctx.fillStyle = 'rgba(0, 0, 0, 0.6)';
        ctx.fillRect(x + 6, y + 5, tw + 10, 18);
        ctx.fillStyle = '#FFFFFF';
        ctx.font = '600 11px system-ui, sans-serif';
        ctx.fillText(label, x + 11, y + 17);
      }
    };

    for (const it of items) {
      if (editable && it.id === selectedId) continue; // draw previews below instead
      drawItem(it);
    }
    if (moveDrag) {
      const it = items.find((i) => i.id === moveDrag.id);
      if (it) drawItem({ ...it, x: moveDrag.x, y: moveDrag.y, selected: true });
    }
    if (resizeDrag) {
      const it = items.find((i) => i.id === resizeDrag.id);
      if (it) {
        drawItem({
          id: it.id,
          name: it.name,
          x: resizeDrag.x,
          y: resizeDrag.y,
          width: resizeDrag.w,
          height: resizeDrag.h,
          status: it.status,
          selected: true,
        });
      }
    }
    if (ghost && ghost.width > 0 && ghost.height > 0) {
      ctx.strokeStyle = '#FBBF24';
      ctx.lineWidth = 2;
      ctx.strokeRect(ghost.x * dispW, ghost.y * dispH, ghost.width * dispW, ghost.height * dispH);
      ctx.fillStyle = 'rgba(251, 191, 36, 0.25)';
      ctx.fillRect(ghost.x * dispW, ghost.y * dispH, ghost.width * dispW, ghost.height * dispH);
    }
    if (editable && selectedId !== null) {
      const it = items.find((i) => i.id === selectedId);
      if (it) {
        const handles: Array<[number, number, Dir]> = [
          [it.x, it.y, 'nw'],
          [it.x + it.width / 2, it.y, 'n'],
          [it.x + it.width, it.y, 'ne'],
          [it.x, it.y + it.height / 2, 'w'],
          [it.x + it.width, it.y + it.height / 2, 'e'],
          [it.x, it.y + it.height, 'sw'],
          [it.x + it.width / 2, it.y + it.height, 's'],
          [it.x + it.width, it.y + it.height, 'se'],
        ];
        for (const [hx, hy, d] of handles) {
          void d;
          const px = hx * dispW - HANDLE_SIZE / 2;
          const py = hy * dispH - HANDLE_SIZE / 2;
          ctx.fillStyle = SELECTED_COLOR;
          ctx.fillRect(px, py, HANDLE_SIZE, HANDLE_SIZE);
          ctx.strokeStyle = '#FFFFFF';
          ctx.lineWidth = 1;
          ctx.strokeRect(px, py, HANDLE_SIZE, HANDLE_SIZE);
          void d;
        }
        // Delete affordance on the selected rectangle.
        if (onDelete) {
          const bx = it.x * dispW - 16;
          const by = it.y * dispH - 16;
          ctx.fillStyle = '#F87171';
          ctx.beginPath();
          ctx.arc(bx, by, 13, 0, Math.PI * 2);
          ctx.fill();
          ctx.fillStyle = '#FFFFFF';
          ctx.font = 'bold 14px system-ui';
          ctx.textAlign = 'center';
          ctx.textBaseline = 'middle';
          ctx.fillText('×', bx, by);
          ctx.textAlign = 'start';
        }
      }
    }
  }, [image.width, image.height, dispW, dispH, items, selectedId, moveDrag, resizeDrag, ghost, editable, onDelete]);

  // Load the image element and watch container size changes.
  useEffect(() => {
    const img = new Image();
    img.onload = () => setMeasureVersion((v) => v + 1);
    img.src = image.url;
    imgElRef.current = img;
    const container = containerRef.current;
    let ro: ResizeObserver | undefined;
    if (container && typeof ResizeObserver !== 'undefined') {
      ro = new ResizeObserver(() => setMeasureVersion((v) => v + 1));
      ro.observe(container);
    }
    return () => {
      img.onload = null;
      ro?.disconnect();
      if (imgElRef.current === img) imgElRef.current = null;
    };
  }, [image.url]);

  const hitTest = useCallback(
    (p: { x: number; y: number }): { id: number; dir: Dir } | null => {
      for (const it of items) {
        const x = it.x * dispW;
        const y = it.y * dispH;
        const w = it.width * dispW;
        const h = it.height * dispH;
        const cx = x + w / 2;
        const cy = y + h / 2;
        const inside = p.x >= x - 4 && p.x <= x + w + 4 && p.y >= y - 4 && p.y <= y + h + 4;
        if (editable && it.id === selectedId) {
          const near = (a: number, b: number) => Math.abs(a - b) <= HIT_PADDING;
          if (near(p.x, x) && near(p.y, y)) return { id: it.id, dir: 'nw' };
          if (near(p.x, cx) && near(p.y, y)) return { id: it.id, dir: 'n' };
          if (near(p.x, x + w) && near(p.y, y)) return { id: it.id, dir: 'ne' };
          if (near(p.x, x) && near(p.y, cy)) return { id: it.id, dir: 'w' };
          if (near(p.x, x + w) && near(p.y, cy)) return { id: it.id, dir: 'e' };
          if (near(p.x, x) && near(p.y, y + h)) return { id: it.id, dir: 'sw' };
          if (near(p.x, cx) && near(p.y, y + h)) return { id: it.id, dir: 's' };
          if (near(p.x, x + w) && near(p.y, y + h)) return { id: it.id, dir: 'se' };
        }
        if (inside) return { id: it.id, dir: 'm' };
      }
      return null;
    },
    [items, dispW, dispH, editable, selectedId]
  );

  const clamp01 = useCallback(
    (v: number, lo: number, hi: number) => Math.max(lo, Math.min(hi, v)),
    []
  );

  const handleMouseDown = useCallback(
    (e: React.MouseEvent<HTMLCanvasElement>) => {
      if (!editable) return;
      const canvas = canvasRef.current;
      if (!canvas) return;
      const rect = canvas.getBoundingClientRect();
      const p = toNorm(e.clientX - rect.left, e.clientY - rect.top);
      const hit = hitTest({ x: p.x, y: p.y });
      if (hit) {
        onSelect?.(hit.id);
        if (hit.dir !== 'm') {
          const it = items.find((i) => i.id === hit.id);
          if (it) setResizeDrag({ id: it.id, dir: hit.dir, startX: p.x, startY: p.y, x: it.x, y: it.y, w: it.width, h: it.height });
        } else {
          const it = items.find((i) => i.id === hit.id);
          if (it) setMoveDrag({ id: it.id, startX: p.x, startY: p.y, x: it.x, y: it.y });
        }
        return;
      }
      onSelect?.(null);
      setGhost({ id: 0, name: '', x: p.x, y: p.y, width: 0, height: 0 });
    },
    [editable, hitTest, items, onSelect, toNorm]
  );

  const handleMouseMove = useCallback(
    (e: React.MouseEvent<HTMLCanvasElement>) => {
      if (!editable) return;
      const canvas = canvasRef.current;
      if (!canvas) return;
      const rect = canvas.getBoundingClientRect();
      const p = toNorm(e.clientX - rect.left, e.clientY - rect.top);
      if (moveDrag) {
        const it = items.find((i) => i.id === moveDrag.id);
        if (it) {
          const nx = clamp01(it.x + (p.x - moveDrag.startX), 0, 1 - it.width);
          const ny = clamp01(it.y + (p.y - moveDrag.startY), 0, 1 - it.height);
          setMoveDrag((d) => ({ ...d!, x: nx, y: ny }));
        }
        return;
      }
      if (resizeDrag) {
        const d = resizeDrag;
        const dx = p.x - d.startX;
        const dy = p.y - d.startY;
        let { x, y, w, h } = d;
        if (d.dir === 'nw') { x += dx; w -= dx; y += dy; h -= dy; }
        else if (d.dir === 'ne') { w += dx; y += dy; h -= dy; }
        else if (d.dir === 'sw') { x += dx; w -= dx; h += dy; }
        else if (d.dir === 'se') { w += dx; h += dy; }
        else if (d.dir === 'n') { y += dy; h -= dy; }
        else if (d.dir === 's') { h += dy; }
        else if (d.dir === 'w') { x += dx; w -= dx; }
        else { w += dx; } // 'e'
        x = clamp01(x, 0, 1);
        y = clamp01(y, 0, 1);
        w = clamp01(w, MIN_SIZE, 1 - x);
        h = clamp01(h, MIN_SIZE, 1 - y);
        setResizeDrag({ ...d, x, y, w, h });
        return;
      }
      if (ghost) {
        setGhost({ ...ghost, width: p.x - ghost.x, height: p.y - ghost.y });
      }
    },
    [editable, moveDrag, resizeDrag, ghost, items, toNorm, clamp01]
  );

  const handleMouseUp = useCallback(() => {
    if (moveDrag) {
      const it = items.find((i) => i.id === moveDrag.id);
      setMoveDrag(null);
      if (it) {
        onChange?.(
          items.map((i) =>
            i.id === moveDrag.id ? { ...i, x: moveDrag.x, y: moveDrag.y } : i
          )
        );
        onSelect?.(it.id);
      }
      return;
    }
    if (resizeDrag) {
      const it = items.find((i) => i.id === resizeDrag.id);
      setResizeDrag(null);
      if (it) {
        onChange?.(
          items.map((i) =>
            i.id === resizeDrag.id
              ? { ...i, x: resizeDrag.x, y: resizeDrag.y, width: resizeDrag.w, height: resizeDrag.h }
              : i
          )
        );
        onSelect?.(it.id);
      }
      return;
    }
    if (ghost) {
      const { x, y, width, height } = ghost;
      setGhost(null);
      if (width >= MIN_SIZE && height >= MIN_SIZE && x >= 0 && y >= 0 && x + width <= 1 && y + height <= 1) {
        const id = items.length ? Math.max(...items.map((i) => i.id)) + 1 : 1;
        onChange?.([...items, { id, name: '', x, y, width, height }]);
        onSelect?.(id);
      }
    }
  }, [editable, moveDrag, resizeDrag, ghost, items, onChange, onSelect]);

  return (
    <div
      ref={containerRef}
      className={`relative max-w-full overflow-x-auto rounded-lg border-2 border-border bg-black/5 ${className}`}
    >
      <canvas
        ref={canvasRef}
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onMouseLeave={handleMouseUp}
        className="block cursor-crosshair"
      />
    </div>
  );
}
