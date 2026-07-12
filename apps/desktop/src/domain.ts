export const MATERIAL_EXTRACTION_WORKFLOW_ID = 'material_extraction';
export const MATERIAL_EXTRACTION_WORKFLOW_NAME = 'Material Science Data Extraction';

export type JobOut = {
  id: string;
  workflow_id: string;
  status: string;
  total_items: number;
  completed_items: number;
  failed_items: number;
  created_at: string;
  started_at: string | null;
  finished_at: string | null;
};

export type ParsedResult = {
  success?: boolean;
  samples?: Array<{ name?: string; properties?: Record<string, unknown> }>;
  error?: string | null;
};

export type JobItemOut = {
  id: string;
  ordinal: number;
  file_name: string;
  file_hash: string;
  text_length: number;
  status: string;
  parsed_result: ParsedResult | null;
  error_code: string | null;
  error_message: string | null;
  duration_ms: number | null;
  finished_at: string | null;
};

export type MeOut = {
  email: string | null;
  display_name: string | null;
  plan: string;
  quota: {
    limit: number;
    used: number;
    reset_at?: string;
  };
};

export function progressPercent(job: JobOut) {
  if (!job.total_items) return 0;
  return Math.round(((job.completed_items + job.failed_items) / job.total_items) * 100);
}

export function isTerminal(status: string) {
  return ['completed', 'failed', 'cancelled'].includes(status);
}

export function shortId(id: string) {
  return id.slice(0, 8);
}

export function sampleCount(item: JobItemOut) {
  return item.parsed_result?.samples?.length ?? 0;
}

export function calculateJobStats(job: JobOut, items: JobItemOut[]) {
  const durations = items
    .map((item) => item.duration_ms)
    .filter((duration): duration is number => duration !== null && duration >= 0);
  const processed = job.completed_items + job.failed_items;
  return {
    elapsedMs: jobDurationMs(job),
    averageItemMs: durations.length
      ? Math.round(durations.reduce((sum, duration) => sum + duration, 0) / durations.length)
      : null,
    timedItems: durations.length,
    processed,
    remaining: Math.max(0, job.total_items - processed),
    successRate: processed ? Math.round((job.completed_items / processed) * 100) : 0,
    sampleCount: items.reduce((sum, item) => sum + sampleCount(item), 0),
    filesWithSamples: items.filter((item) => sampleCount(item) > 0).length,
    totalCharacters: items.reduce((sum, item) => sum + item.text_length, 0),
  };
}

export function jobDurationMs(job: JobOut) {
  if (!job.started_at) return null;
  const started = new Date(job.started_at).getTime();
  const finished = job.finished_at ? new Date(job.finished_at).getTime() : Date.now();
  return Math.max(0, finished - started);
}

export function formatDuration(milliseconds: number | null) {
  if (milliseconds === null || !Number.isFinite(milliseconds)) return '—';
  if (milliseconds < 1000) return '<1s';
  const totalSeconds = Math.round(milliseconds / 1000);
  const hours = Math.floor(totalSeconds / 3600);
  const minutes = Math.floor((totalSeconds % 3600) / 60);
  const seconds = totalSeconds % 60;
  if (hours) return `${hours}h ${minutes}m ${seconds}s`;
  if (minutes) return `${minutes}m ${seconds}s`;
  return `${seconds}s`;
}

export function formatDateTime(value: string | null) {
  return value ? new Date(value).toLocaleString() : '—';
}

export function resultLabel(item: JobItemOut) {
  if (item.status === 'done') return `${sampleCount(item)} sample(s) parsed`;
  if (item.status === 'running') return 'Processing';
  if (item.status === 'pending') return 'Queued';
  return 'No parsed result';
}

export function parseStatusLabel(parsedCount: number, selectedCount: number) {
  if (selectedCount === 0) return 'No PDFs selected';
  if (parsedCount === selectedCount) return 'Ready to submit';
  if (parsedCount > 0) return `${parsedCount}/${selectedCount} parsed`;
  return 'Waiting for local parsing';
}

export function errorMessage(error: unknown) {
  if (error instanceof Error) return error.message;
  if (typeof error === 'object' && error && 'message' in error) {
    return String((error as { message?: unknown }).message ?? 'Request failed');
  }
  return String(error);
}
