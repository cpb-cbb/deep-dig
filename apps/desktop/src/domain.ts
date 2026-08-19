export const MATERIAL_EXTRACTION_WORKFLOW_ID = 'material_extraction';
export const MATERIAL_EXTRACTION_WORKFLOW_NAME = 'Material Science Data Extraction';

export type WorkflowOut = {
  id: string;
  name: string;
  description: string;
  version: string;
  domain: string;
  task_type: string;
  result_type: 'material_property_table' | 'records' | 'entity_relation' | string;
  config_schema: Record<string, unknown>;
  output_schema: Record<string, unknown>;
  ui_schema: {
    controls?: Array<{
      key: string;
      control: 'tag_list' | 'field_builder' | string;
      label: string;
      help?: string;
      placeholder?: string;
    }>;
  };
  ui_config: {
    order?: number;
    color?: string;
    icon?: string;
    badge?: string;
    speed?: string;
  };
};

export type CustomField = {
  key: string;
  label: string;
  type: 'text' | 'number' | 'date' | 'boolean' | 'list';
  description: string;
};

export type JobOut = {
  id: string;
  workflow_id: string;
  workflow_version: string;
  config: Record<string, unknown>;
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
  result_type?: string;
  data?: {
    samples?: Array<{ name?: string; properties?: Record<string, unknown> }>;
    records?: Array<{ values?: Record<string, unknown> }>;
    entities?: Array<{ id?: string; name?: string; type?: string }>;
    relations?: Array<{ source?: string; target?: string; type?: string }>;
  };
  warnings?: string[];
  // Legacy results created before the versioned workflow envelope.
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

export type ParsedFile = {
  fileName: string;
  fileHash: string;
  text: string;
  textFormat: 'markdown';
  textLength: number;
  reused: boolean;
};

export type SelectedPdf = {
  file: File;
  fileName: string;
};

export type MeOut = {
  email: string | null;
  display_name: string | null;
};

export type LlmProvider = 'auto' | 'openrouter' | 'anthropic' | 'openai_compatible' | 'fake';

export type LlmSettings = {
  source: 'environment' | 'custom';
  provider: LlmProvider;
  base_url: string;
  model: string;
  temperature: number;
  api_key_configured: boolean;
};

export type JobResumeOut = {
  job_id: string;
  queued_items: number;
  unavailable_items: number;
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

export function resultCount(item: JobItemOut) {
  const result = item.parsed_result;
  if (!result) return 0;
  const data = result.data ?? { samples: result.samples };
  if (result.result_type === 'records') return data.records?.length ?? 0;
  if (result.result_type === 'entity_relation') return data.entities?.length ?? 0;
  return data.samples?.length ?? 0;
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
    extractedCount: items.reduce((sum, item) => sum + resultCount(item), 0),
    filesWithResults: items.filter((item) => resultCount(item) > 0).length,
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
  if (item.status === 'done') {
    const type = item.parsed_result?.result_type;
    const noun = type === 'records' ? 'record(s)' : type === 'entity_relation' ? 'entity(s)' : 'sample(s)';
    return `${resultCount(item)} ${noun} parsed`;
  }
  if (item.status === 'running') return 'Processing';
  if (item.status === 'pending') return 'Queued';
  return 'No parsed result';
}

export function parseStatusLabel(parsedCount: number, selectedCount: number) {
  if (selectedCount === 0) return 'No PDFs selected';
  if (parsedCount === selectedCount) return 'Ready to submit';
  if (parsedCount > 0) return `${parsedCount}/${selectedCount} parsed`;
  return 'Waiting for parsing';
}

export function errorMessage(error: unknown) {
  if (error instanceof Error) return error.message;
  if (typeof error === 'object' && error && 'message' in error) {
    return String((error as { message?: unknown }).message ?? 'Request failed');
  }
  return String(error);
}
