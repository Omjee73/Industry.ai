/** REST client for the PCB Inspector API (relative URLs work when served by FastAPI)." */

import type {
  Annotation,
  ComponentResult,
  DatasetLoadOut,
  ImageInfo,
  ImageStatus,
  InspectionDetail,
  SettingsData,
} from '../types';

async function parseError(res: Response): Promise<string> {
  try {
    const data = await res.json();
    if (data?.detail) {
      const d = data.detail;
      if (typeof d === 'string') return d;
      if (Array.isArray(d)) {
        const parts = d.map((e) => (e && typeof e.msg === 'string' ? e.msg : String(e)));
        return parts.join('; ');
      }
      return JSON.stringify(d);
    }
  } catch {
    /* not JSON */
  }
  return `Request failed with status ${res.status}`;
}

export function errorMessage(e: unknown): string {
  if (e instanceof Error) return e.message || 'Unknown error';
  if (typeof e === 'string') return e || 'Unknown error';
  const detail = (e as { detail?: unknown } | null)?.detail;
  if (detail) {
    if (typeof detail === 'string') return detail;
    if (Array.isArray(detail)) {
      return detail.map((x) => (x && typeof x.msg === 'string' ? x.msg : String(x))).join('; ');
    }
    return JSON.stringify(detail);
  }
  return 'Unknown error while running inspection';
}

async function api<T>(url: string, init?: RequestInit): Promise<T> {
  const res = await fetch(url, init);
  if (!res.ok) throw new Error(await parseError(res));
  return res.json() as Promise<T>;
}

function jsonInit(method: string, payload: unknown): RequestInit {
  return { method, body: JSON.stringify(payload), headers: { 'Content-Type': 'application/json' } };
}

async function uploadImage(url: string, file: File): Promise<ImageInfo> {
  const form = new FormData();
  form.append('file', file, file.name);
  const res = await fetch(url, { method: 'POST', body: form });
  if (!res.ok) throw new Error(await parseError(res));
  return res.json();
}

export function health() {
  return api<{ status: string }>('/api/v1/health');
}

export function uploadReference(file: File) {
  return uploadImage('/api/v1/reference', file);
}

export function uploadTest(file: File) {
  return uploadImage('/api/v1/test', file);
}

export function referenceImageUrl(id: number) {
  return `/api/v1/reference/${id}/image`;
}

export function testImageUrl(id: number) {
  return `/api/v1/test/${id}/image`;
}

export function getAnnotations(id: number) {
  return api<Annotation[]>(`/api/v1/reference/${id}/annotations`);
}

export function saveAnnotations(
  id: number,
  annotations: { name: string; x: number; y: number; width: number; height: number }[]
) {
  return api<Annotation[]>(`/api/v1/reference/${id}/annotations`, jsonInit('POST', { annotations }));
}

export function runInspection(payload: { reference_image_id: number; test_image_ids: number[] }): Promise<InspectionDetail> {
  return api<RawInspection>('/api/v1/inspection', jsonInit('POST', payload)).then(toInspectionDetail);
}

export function getInspection(id: number): Promise<InspectionDetail> {
  return api<RawInspection>(`/api/v1/inspection/${id}`).then(toInspectionDetail);
}

interface RawInspection {
  id: number;
  status: ImageStatus;
  reference_image_id: number;
  test_images: Array<{
    test_image_id: number;
    status: ImageStatus;
    results: ComponentResult[];
    image: ImageInfo;
  }>;
}

/** Map the backend's snake_case inspection response to the camelCase frontend type. */
function toInspectionDetail(raw: RawInspection): InspectionDetail {
  return {
    id: raw.id,
    status: raw.status,
    referenceImageId: raw.reference_image_id,
    testImages: (raw.test_images || []).map((t) => ({
      testImageId: t.test_image_id,
      status: t.status,
      results: t.results,
      image: t.image,
    })),
  };
}

export function getSettings() {
  return api<SettingsData>('/api/v1/settings');
}

export function updateSettings(thresholds: Record<string, number>) {
  return api<SettingsData>('/api/v1/settings', jsonInit('PUT', { thresholds }));
}

export function getLatestReference() {
  return api<ImageInfo>('/api/v1/reference/latest');
}

export function getTestImage(id: number) {
  return api<ImageInfo>(`/api/v1/test/${id}`);
}

export function loadDemoDataset() {
  return api<DatasetLoadOut>('/api/v1/dataset/load');
}

export async function downloadExport(inspectionId: number, format: 'json' | 'csv') {
  const res = await fetch(`/api/v1/inspection/${inspectionId}/export?format=${format}`);
  if (!res.ok) throw new Error(await parseError(res));
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `inspection_${inspectionId}_results.${format}`;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}
