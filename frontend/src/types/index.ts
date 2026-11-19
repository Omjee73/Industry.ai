/** Types shared between the frontend and the FastAPI backend. */

export type ComponentStatus = 'present' | 'missing' | 'review';
export type ImageStatus = 'ok' | 'missing' | 'review';

export interface ImageInfo {
  id: number;
  kind: string;
  width: number;
  height: number;
  url: string;
}

export interface Annotation {
  id: number;
  name: string;
  x: number;
  y: number;
  width: number;
  height: number;
}

export interface BBox {
  x: number;
  y: number;
  width: number;
  height: number;
}

export interface ComponentResult {
  name: string;
  status: ComponentStatus;
  confidence: number;
  explanation: string;
  bbox: BBox;
}

export interface TestImageResults {
  testImageId: number;
  status: ImageStatus;
  results: ComponentResult[];
  image: ImageInfo;
}

export interface InspectionDetail {
  id: number;
  status: ImageStatus;
  referenceImageId: number;
  testImages: TestImageResults[];
}

export interface SettingsData {
  thresholds: Record<string, number>;
  defaults: Record<string, number>;
}

export interface DatasetLoadOut {
  reference_id: number;
  reference_url: string;
  annotations: Annotation[];
  test_ids: number[];
  message: string;
}
