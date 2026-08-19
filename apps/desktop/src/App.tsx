import {
  Atom,
  Braces,
  CheckCircle2,
  ChevronDown,
  ChevronLeft,
  ChevronRight,
  ChevronUp,
  Clock3,
  Download,
  FileText,
  KeyRound,
  ListChecks,
  LogIn,
  LogOut,
  Network,
  Play,
  Plus,
  RefreshCw,
  Settings2,
  Trash2,
  X,
  XCircle,
} from 'lucide-react';
import { useEffect, useMemo, useRef, useState, type FormEvent } from 'react';
import { apiDownload, apiFetch } from './api';
import {
  MATERIAL_EXTRACTION_WORKFLOW_ID,
  calculateJobStats,
  errorMessage,
  formatDateTime,
  formatDuration,
  isTerminal,
  jobDurationMs,
  parseStatusLabel,
  progressPercent,
  resultLabel,
  resultCount,
  shortId,
  type CustomField,
  type JobItemOut,
  type JobOut,
  type JobResumeOut,
  type LlmProvider,
  type LlmSettings,
  type MeOut,
  type ParsedFile,
  type SelectedPdf,
  type WorkflowOut,
} from './domain';
import { parseFiles, selectPdfFiles } from './files';

const TOKEN_STORAGE_KEY = 'deep-dig-token';
const CUSTOM_SCHEMA_STORAGE_KEY = 'deep-dig-custom-schema-v1';
const CUSTOM_RECORD_WORKFLOW_ID = 'custom_record_extraction';
const ACTIVE_JOB_REFRESH_MS = 6_000;
const ACCOUNT_REFRESH_MS = 30_000;
const JOBS_PER_PAGE = 5;
type CustomLlmProvider = Exclude<LlmProvider, 'auto'>;
type RecentSchema = {
  jobId: string;
  createdAt: string;
  fields: CustomField[];
};

const DEFAULT_TAG_VALUES: Record<string, string> = {
  properties: 'BET surface area\ntotal pore volume\nspecific capacitance',
  entity_types: 'Person\nOrganization\nLocation',
  relation_types: 'AFFILIATED_WITH\nLOCATED_IN',
};

const DEFAULT_CUSTOM_FIELDS: CustomField[] = [
  { key: 'title', label: 'Title', type: 'text', description: 'Primary title or heading' },
  { key: 'effective_date', label: 'Effective date', type: 'date', description: 'Date the record takes effect' },
];

export function App() {
  const [token, setToken] = useState('');
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [profile, setProfile] = useState<MeOut | null>(null);
  const [workflows, setWorkflows] = useState<WorkflowOut[]>([]);
  const [selectedWorkflowId, setSelectedWorkflowId] = useState(MATERIAL_EXTRACTION_WORKFLOW_ID);
  const [tagValues, setTagValues] = useState<Record<string, string>>(DEFAULT_TAG_VALUES);
  const [customFields, setCustomFields] = useState<CustomField[]>(loadSavedCustomFields);
  const [selectedFiles, setSelectedFiles] = useState<SelectedPdf[]>([]);
  const [files, setFiles] = useState<ParsedFile[]>([]);
  const [jobs, setJobs] = useState<JobOut[]>([]);
  const [jobPage, setJobPage] = useState(0);
  const [queueCollapsed, setQueueCollapsed] = useState(false);
  const [selectedJobId, setSelectedJobId] = useState<string | null>(null);
  const [items, setItems] = useState<JobItemOut[]>([]);
  const [status, setStatus] = useState('Ready');
  const [savedPath, setSavedPath] = useState('');
  const [isParsing, setIsParsing] = useState(false);
  const [parseProgress, setParseProgress] = useState(0);
  const [parseReusedCount, setParseReusedCount] = useState(0);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isLoadingJobs, setIsLoadingJobs] = useState(false);
  const [isAuthenticating, setIsAuthenticating] = useState(false);
  const [isSelectingFiles, setIsSelectingFiles] = useState(false);
  const [isAppVisible, setIsAppVisible] = useState(
    () => document.visibilityState === 'visible' && document.hasFocus(),
  );
  const [busyJobId, setBusyJobId] = useState<string | null>(null);
  const [detailsOpen, setDetailsOpen] = useState(false);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [llmSettings, setLlmSettings] = useState<LlmSettings | null>(null);
  const [llmMode, setLlmMode] = useState<'environment' | 'custom'>('environment');
  const [llmProvider, setLlmProvider] = useState<CustomLlmProvider>('openai_compatible');
  const [llmBaseUrl, setLlmBaseUrl] = useState('');
  const [llmModel, setLlmModel] = useState('');
  const [llmApiKey, setLlmApiKey] = useState('');
  const [llmTemperature, setLlmTemperature] = useState(0);
  const [clearLlmApiKey, setClearLlmApiKey] = useState(false);
  const [isLoadingSettings, setIsLoadingSettings] = useState(false);
  const [isSavingSettings, setIsSavingSettings] = useState(false);
  const accountRefreshInFlightRef = useRef(false);
  const refreshInFlightRef = useRef(false);
  const lastManualRefreshRef = useRef(0);
  const itemLoadsInFlightRef = useRef(new Set<string>());
  const submitInFlightRef = useRef(false);
  const pendingIdempotencyKeyRef = useRef<string | null>(null);
  const pendingSubmissionFingerprintRef = useRef<string | null>(null);
  const authInFlightRef = useRef(false);
  const parseInFlightRef = useRef(false);
  const fileDialogInFlightRef = useRef(false);
  const jobActionsInFlightRef = useRef(new Set<string>());

  const selectedJob = useMemo(
    () => jobs.find((job) => job.id === selectedJobId) ?? jobs[0] ?? null,
    [jobs, selectedJobId],
  );
  const selectedWorkflow = useMemo(
    () => workflows.find((workflow) => workflow.id === selectedWorkflowId) ?? workflows[0] ?? null,
    [workflows, selectedWorkflowId],
  );
  const filesTextLength = useMemo(() => files.reduce((sum, file) => sum + file.textLength, 0), [files]);
  const parsePercent = selectedFiles.length ? Math.round((parseProgress / selectedFiles.length) * 100) : 0;
  const canSubmit = Boolean(
    token.trim()
      && files.length > 0
      && !isParsing
      && !isSubmitting
      && selectedWorkflow
      && workflowConfigReady(selectedWorkflow, tagValues, customFields),
  );
  const selectedJobStats = useMemo(
    () => selectedJob ? calculateJobStats(selectedJob, items) : null,
    [selectedJob, items],
  );
  const hasActiveJobs = useMemo(
    () => jobs.some((job) => job.status === 'pending' || job.status === 'running'),
    [jobs],
  );
  const jobPageCount = Math.max(1, Math.ceil(jobs.length / JOBS_PER_PAGE));
  const visibleJobs = useMemo(
    () => jobs.slice(jobPage * JOBS_PER_PAGE, (jobPage + 1) * JOBS_PER_PAGE),
    [jobs, jobPage],
  );
  const recentSchemas = useMemo(() => recentCustomSchemas(jobs), [jobs]);

  useEffect(() => {
    const saved = localStorage.getItem(TOKEN_STORAGE_KEY);
    if (saved) setToken(saved);
    void loadWorkflows();
  }, []);

  useEffect(() => {
    try {
      localStorage.setItem(CUSTOM_SCHEMA_STORAGE_KEY, JSON.stringify(customFields));
    } catch {
      // Private browsing or a locked-down WebView can disable local storage.
    }
  }, [customFields]);

  useEffect(() => {
    setJobPage((current) => Math.min(current, jobPageCount - 1));
  }, [jobPageCount]);

  useEffect(() => {
    if (!token.trim()) {
      setProfile(null);
      setJobs([]);
      setItems([]);
      setSelectedJobId(null);
      return;
    }
    void loadAccount();
    void refreshJobs();
  }, [token]);

  useEffect(() => {
    const handleVisibilityChange = () => {
      setIsAppVisible(document.visibilityState === 'visible' && document.hasFocus());
    };
    const handleFocus = () => setIsAppVisible(document.visibilityState === 'visible');
    const handleBlur = () => setIsAppVisible(false);
    document.addEventListener('visibilitychange', handleVisibilityChange);
    window.addEventListener('focus', handleFocus);
    window.addEventListener('blur', handleBlur);
    return () => {
      document.removeEventListener('visibilitychange', handleVisibilityChange);
      window.removeEventListener('focus', handleFocus);
      window.removeEventListener('blur', handleBlur);
    };
  }, []);

  useEffect(() => {
    if (!token.trim() || !hasActiveJobs || !isAppVisible) return undefined;
    const interval = window.setInterval(() => {
      void refreshJobs(true);
      if (selectedJobId) void loadJobItems(selectedJobId, true);
    }, ACTIVE_JOB_REFRESH_MS);
    return () => window.clearInterval(interval);
  }, [token, selectedJobId, hasActiveJobs, isAppVisible]);

  useEffect(() => {
    if (!token.trim() || !isAppVisible) return undefined;
    void loadAccount(true);
    const interval = window.setInterval(() => {
      void loadAccount(true);
    }, ACCOUNT_REFRESH_MS);
    return () => window.clearInterval(interval);
  }, [token, isAppVisible]);

  useEffect(() => {
    if (!selectedJobId || !token.trim()) {
      setItems([]);
      return;
    }
    void loadJobItems(selectedJobId);
  }, [selectedJobId, token]);

  useEffect(() => {
    if (!detailsOpen && !settingsOpen) return undefined;
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        setDetailsOpen(false);
        setSettingsOpen(false);
      }
    };
    window.addEventListener('keydown', closeOnEscape);
    return () => window.removeEventListener('keydown', closeOnEscape);
  }, [detailsOpen, settingsOpen]);

  async function loadWorkflows() {
    try {
      const available = await apiFetch<WorkflowOut[]>('/workflows', '');
      setWorkflows(available);
      setSelectedWorkflowId((current) => available.some((workflow) => workflow.id === current)
        ? current
        : available[0]?.id ?? MATERIAL_EXTRACTION_WORKFLOW_ID);
    } catch (error) {
      setStatus(errorMessage(error));
    }
  }

  async function loadAccount(silent = false) {
    if (!token.trim() || accountRefreshInFlightRef.current) return;
    accountRefreshInFlightRef.current = true;
    try {
      setProfile(await apiFetch<MeOut>('/me', token));
    } catch (error) {
      if (!silent) setStatus(errorMessage(error));
    } finally {
      accountRefreshInFlightRef.current = false;
    }
  }

  async function refreshDashboard() {
    await Promise.all([refreshJobs(), loadAccount(true)]);
  }

  async function refreshJobs(silent = false) {
    if (!token.trim()) return;
    if (refreshInFlightRef.current) {
      if (!silent) setStatus('A task refresh is already in progress.');
      return;
    }
    const now = Date.now();
    if (!silent && now - lastManualRefreshRef.current < 1500) {
      setStatus('Task status was just refreshed.');
      return;
    }
    refreshInFlightRef.current = true;
    if (!silent) lastManualRefreshRef.current = now;
    try {
      setIsLoadingJobs(true);
      const data = await apiFetch<JobOut[]>('/jobs', token);
      setJobs(data);
      setSelectedJobId((current) => {
        if (current && data.some((job) => job.id === current)) return current;
        return data[0]?.id ?? null;
      });
    } catch (error) {
      if (!silent) setStatus(errorMessage(error));
    } finally {
      refreshInFlightRef.current = false;
      setIsLoadingJobs(false);
    }
  }

  async function loadJobItems(jobId: string, silent = false) {
    if (itemLoadsInFlightRef.current.has(jobId)) return;
    itemLoadsInFlightRef.current.add(jobId);
    try {
      setItems(await apiFetch<JobItemOut[]>(`/jobs/${jobId}/items`, token));
    } catch (error) {
      if (!silent) setStatus(errorMessage(error));
    } finally {
      itemLoadsInFlightRef.current.delete(jobId);
    }
  }

  async function submitAuth(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (authInFlightRef.current) return;
    authInFlightRef.current = true;
    setIsAuthenticating(true);
    try {
      await signIn();
    } finally {
      authInFlightRef.current = false;
      setIsAuthenticating(false);
    }
  }

  async function signIn() {
    setStatus('Signing in...');
    try {
      const { access_token } = await apiFetch<{ access_token: string }>('/auth/login', '', {
        method: 'POST',
        body: JSON.stringify({ username, password }),
      });
      setToken(access_token);
      localStorage.setItem(TOKEN_STORAGE_KEY, access_token);
      setStatus('Signed in.');
    } catch (error) {
      setStatus(errorMessage(error));
    }
  }

  async function signOut() {
    localStorage.removeItem(TOKEN_STORAGE_KEY);
    setStatus('Signed out.');
    setToken('');
    setProfile(null);
    setJobs([]);
    setItems([]);
    setSelectedJobId(null);
    setSettingsOpen(false);
  }

  async function openSettings() {
    if (!token.trim() || isLoadingSettings) return;
    setSettingsOpen(true);
    setIsLoadingSettings(true);
    try {
      const current = await apiFetch<LlmSettings>('/me/llm-settings', token);
      setLlmSettings(current);
      setLlmMode(current.source);
      setLlmProvider(current.provider === 'auto' ? 'openai_compatible' : current.provider);
      setLlmBaseUrl(current.base_url);
      setLlmModel(current.model);
      setLlmTemperature(current.temperature);
      setLlmApiKey('');
      setClearLlmApiKey(false);
    } catch (error) {
      setStatus(errorMessage(error));
      setSettingsOpen(false);
    } finally {
      setIsLoadingSettings(false);
    }
  }

  async function saveLlmSettings(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (isSavingSettings) return;
    setIsSavingSettings(true);
    try {
      const updated = await apiFetch<LlmSettings>('/me/llm-settings', token, {
        method: 'PATCH',
        body: JSON.stringify(llmMode === 'environment' ? {
          mode: 'environment',
        } : {
          mode: 'custom',
          provider: llmProvider,
          base_url: llmBaseUrl,
          model: llmModel,
          temperature: llmTemperature,
          api_key: llmApiKey || null,
          clear_api_key: clearLlmApiKey,
        }),
      });
      setLlmSettings(updated);
      setLlmApiKey('');
      setClearLlmApiKey(false);
      setSettingsOpen(false);
      setStatus(
        updated.source === 'environment'
          ? 'LLM settings now follow backend environment variables.'
          : `Saved ${updated.provider} settings for new work items.`,
      );
    } catch (error) {
      setStatus(errorMessage(error));
    } finally {
      setIsSavingSettings(false);
    }
  }

  async function selectFiles() {
    if (fileDialogInFlightRef.current) return;
    fileDialogInFlightRef.current = true;
    setIsSelectingFiles(true);
    setStatus('Selecting PDFs...');
    try {
      const selected = await selectPdfFiles();
      setSelectedFiles(selected);
      setFiles([]);
      setParseProgress(0);
      setParseReusedCount(0);
      setStatus(selected.length ? `Selected ${selected.length} PDF(s). Confirm parsing when ready.` : 'Ready');
    } catch (error) {
      setStatus(errorMessage(error));
    } finally {
      fileDialogInFlightRef.current = false;
      setIsSelectingFiles(false);
    }
  }

  async function parseSelectedFiles() {
    if (selectedFiles.length === 0 || parseInFlightRef.current) return;
    parseInFlightRef.current = true;
    setIsParsing(true);
    setFiles([]);
    setParseProgress(0);
    setParseReusedCount(0);
    setStatus('Parsing PDFs on the server...');
    try {
      const parsed = await parseFiles(token, selectedFiles);
      setFiles(parsed);
      setParseProgress(parsed.length);
      setParseReusedCount(parsed.filter((result) => result.reused).length);
      setStatus(`Parsed ${parsed.length} PDF(s). Review the summary, then start extraction.`);
    } catch (error) {
      setStatus(errorMessage(error));
    } finally {
      parseInFlightRef.current = false;
      setIsParsing(false);
    }
  }

  async function submitJob() {
    if (!canSubmit || !selectedWorkflow || submitInFlightRef.current) return;
    submitInFlightRef.current = true;
    setIsSubmitting(true);
    setStatus('Submitting job...');
    try {
      const config = buildWorkflowConfig(selectedWorkflow, tagValues, customFields);
      const submissionFingerprint = JSON.stringify({
        workflow_id: selectedWorkflow.id,
        config,
        files: files.map((file) => file.fileHash),
      });
      if (pendingSubmissionFingerprintRef.current !== submissionFingerprint) {
        pendingSubmissionFingerprintRef.current = submissionFingerprint;
        pendingIdempotencyKeyRef.current = crypto.randomUUID();
      }
      const idempotencyKey = pendingIdempotencyKeyRef.current ?? crypto.randomUUID();
      pendingIdempotencyKeyRef.current = idempotencyKey;
      const result = await apiFetch<{ job_id: string; queued_items: number; reused: boolean }>('/jobs', token, {
        method: 'POST',
        headers: { 'Idempotency-Key': idempotencyKey },
        body: JSON.stringify({
          workflow_id: selectedWorkflow.id,
          config,
          items: files.map((file) => ({
            file_name: file.fileName,
            file_hash: file.fileHash,
            text: file.text,
          })),
        }),
      });
      setStatus(
        result.reused
          ? `Reused existing job ${shortId(result.job_id)}.`
          : `Queued job ${shortId(result.job_id)} with ${result.queued_items} item(s).`,
      );
      pendingIdempotencyKeyRef.current = null;
      pendingSubmissionFingerprintRef.current = null;
      setJobPage(0);
      setSelectedJobId(result.job_id);
      await Promise.all([refreshJobs(true), loadAccount(true)]);
    } catch (error) {
      setStatus(errorMessage(error));
    } finally {
      submitInFlightRef.current = false;
      setIsSubmitting(false);
    }
  }

  async function cancelJob(job: JobOut) {
    const actionKey = `cancel:${job.id}`;
    if (jobActionsInFlightRef.current.has(actionKey)) return;
    jobActionsInFlightRef.current.add(actionKey);
    setBusyJobId(job.id);
    try {
      await apiFetch<JobOut>(`/jobs/${job.id}/cancel`, token, { method: 'POST' });
      setStatus(`Cancelled job ${shortId(job.id)}.`);
      await Promise.all([refreshJobs(true), loadAccount(true)]);
    } catch (error) {
      setStatus(errorMessage(error));
    } finally {
      jobActionsInFlightRef.current.delete(actionKey);
      setBusyJobId(null);
    }
  }

  async function resumeJob(job: JobOut) {
    const actionKey = `resume:${job.id}`;
    if (jobActionsInFlightRef.current.has(actionKey)) return;
    const confirmed = window.confirm(
      'Requeue every unfinished document in this task? Use this after a worker or queue interruption.',
    );
    if (!confirmed) return;
    jobActionsInFlightRef.current.add(actionKey);
    setBusyJobId(job.id);
    try {
      const result = await apiFetch<JobResumeOut>(`/jobs/${job.id}/resume`, token, { method: 'POST' });
      setStatus(
        `Requeued ${result.queued_items} document(s)`
        + (result.unavailable_items ? `; ${result.unavailable_items} legacy item(s) lack source text.` : '.'),
      );
      await Promise.all([refreshJobs(true), loadJobItems(job.id, true)]);
    } catch (error) {
      setStatus(errorMessage(error));
    } finally {
      jobActionsInFlightRef.current.delete(actionKey);
      setBusyJobId(null);
    }
  }

  async function saveJobExport(job: JobOut) {
    const actionKey = `export:${job.id}`;
    if (jobActionsInFlightRef.current.has(actionKey)) return;
    jobActionsInFlightRef.current.add(actionKey);
    setBusyJobId(job.id);
    try {
      const content = await apiDownload(`/jobs/${job.id}/export.xlsx`, token);
      const filename = `deep-dig-${job.id}.xlsx`;
      downloadBytes(content, filename);
      setSavedPath(filename);
      setStatus(`Saved ${shortId(job.id)} export.`);
    } catch (error) {
      setStatus(errorMessage(error));
    } finally {
      jobActionsInFlightRef.current.delete(actionKey);
      setBusyJobId(null);
    }
  }

  function showJobDetails(jobId: string) {
    setSelectedJobId(jobId);
    setDetailsOpen(true);
  }

  return (
    <main className="shell">
      <header className="topbar">
        <div>
          <h1>Deep Dig</h1>
          <p>Turn domain documents into traceable structured data.</p>
        </div>
        <div className="topbar-actions">
          {profile && (
            <div className="account-pill">
              <span>{profile.email ?? profile.display_name ?? 'Signed in'}</span>
            </div>
          )}
          {token.trim() && (
            <>
              <button className="secondary-button" type="button" onClick={() => void openSettings()} title="LLM settings">
                <Settings2 size={18} />
                Settings
              </button>
              <button className="secondary-button" type="button" onClick={signOut} title="Sign out">
                <LogOut size={18} />
                Sign out
              </button>
            </>
          )}
        </div>
      </header>

      <section className="workspace">
        <section className="panel compose-panel">
          <div className="panel-title">
            <div>
              <h2>New extraction</h2>
              <span>{selectedFiles.length || files.length} PDFs selected · {files.length} parsed</span>
            </div>
          </div>

          {!token.trim() && (
            <form className="auth-form" onSubmit={(event) => void submitAuth(event)}>
              <label>Username</label>
              <input value={username} onChange={(event) => setUsername(event.target.value)} type="text" autoComplete="username" />
              <label>Password</label>
              <input
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                type="password"
                autoComplete="current-password"
              />
              <button type="submit" disabled={isAuthenticating || !username || !password}>
                <LogIn size={18} />
                {isAuthenticating ? 'Please wait…' : 'Sign in'}
              </button>
            </form>
          )}

          <div className="workflow-section">
            <div className="workflow-heading">
              <div>
                <span className="eyebrow">Extraction blueprint</span>
                <h3>Choose how to read these documents</h3>
              </div>
              {selectedWorkflow && <span className="workflow-version">v{selectedWorkflow.version}</span>}
            </div>
            <div className="workflow-picker" role="radiogroup" aria-label="Extraction workflow">
              {workflows.map((workflow) => (
                <button
                  aria-checked={workflow.id === selectedWorkflow?.id}
                  className={`workflow-option ${workflow.id === selectedWorkflow?.id ? 'selected' : ''} ${workflow.ui_config.color ?? ''}`}
                  key={workflow.id}
                  onClick={() => setSelectedWorkflowId(workflow.id)}
                  role="radio"
                  type="button"
                >
                  <span className="workflow-icon">{workflowIcon(workflow.ui_config.icon)}</span>
                  <span className="workflow-copy">
                    <strong>{workflow.name}</strong>
                    <small>{workflow.description}</small>
                  </span>
                  <span className="workflow-badge">{workflow.ui_config.badge ?? workflow.domain}</span>
                </button>
              ))}
              {workflows.length === 0 && <p className="empty">Loading extraction blueprints…</p>}
            </div>
          </div>

          {selectedWorkflow && (
            <WorkflowConfigFields
              customFields={customFields}
              onCustomFieldsChange={setCustomFields}
              recentSchemas={recentSchemas}
              onTagValueChange={(key, value) => setTagValues((current) => ({ ...current, [key]: value }))}
              tagValues={tagValues}
              workflow={selectedWorkflow}
            />
          )}

          <button className="drop" type="button" disabled={isSelectingFiles} onClick={selectFiles}>
            <FileText size={24} />
            <span>{isSelectingFiles ? 'Opening file picker…' : 'Select PDFs'}</span>
          </button>

          {(selectedFiles.length > 0 || files.length > 0) && (
            <div className="parse-summary">
              <div className="summary-grid">
                <Metric label="Selected" value={selectedFiles.length || files.length} />
                <Metric label="Parsed" value={files.length} />
                <Metric label="Reused" value={parseReusedCount} />
                <Metric label="Text chars" value={filesTextLength.toLocaleString()} />
              </div>
              <div className="parse-progress">
                <div className="progress-track" aria-label={`${parsePercent} percent parsed`}>
                  <span style={{ width: `${parsePercent}%` }} />
                </div>
                <span>{isParsing ? `${parseProgress}/${selectedFiles.length} parsed` : parseStatusLabel(files.length, selectedFiles.length)}</span>
              </div>
            </div>
          )}

          <div className="compose-actions">
            <button className="secondary-button" disabled={selectedFiles.length === 0 || isParsing} onClick={() => void parseSelectedFiles()} type="button">
              <RefreshCw size={18} />
              {isParsing ? 'Parsing' : 'Parse'}
            </button>
            <button disabled={!canSubmit} onClick={submitJob} type="button">
              <Play size={18} />
              {isSubmitting ? 'Submitting' : 'Start extraction'}
            </button>
          </div>
        </section>

        <section className={`panel queue-panel ${queueCollapsed ? 'collapsed' : ''}`}>
          <div className="panel-title">
            <div>
              <h2>Task queue</h2>
              <span>{jobs.length} recent jobs{jobs.length > JOBS_PER_PAGE ? ` · ${JOBS_PER_PAGE} per page` : ''}</span>
            </div>
            <div className="queue-title-actions">
              <button className="icon-button" type="button" disabled={isLoadingJobs} onClick={() => void refreshDashboard()} title="Refresh jobs and account">
                <RefreshCw className={isLoadingJobs ? 'spinning' : ''} size={18} />
              </button>
              <button
                aria-expanded={!queueCollapsed}
                aria-label={queueCollapsed ? 'Expand task queue' : 'Collapse task queue'}
                className="icon-button"
                onClick={() => setQueueCollapsed((current) => !current)}
                title={queueCollapsed ? 'Expand task queue' : 'Collapse task queue'}
                type="button"
              >
                {queueCollapsed ? <ChevronDown size={18} /> : <ChevronUp size={18} />}
              </button>
            </div>
          </div>

          {!queueCollapsed && (!token.trim() ? (
            <p className="empty">Sign in to load tasks.</p>
          ) : jobs.length === 0 ? (
            <p className="empty">{isLoadingJobs ? 'Loading tasks...' : 'No tasks yet.'}</p>
          ) : (
            <>
              <div className="job-list">
                {visibleJobs.map((job) => (
                  <article className={job.id === selectedJob?.id ? 'job-row selected' : 'job-row'} key={job.id}>
                  <div className="job-main">
                    <div className="job-heading">
                      {statusIcon(job.status)}
                      <strong>{shortId(job.id)}</strong>
                      <span className={`status-badge ${job.status}`}>{job.status}</span>
                    </div>
                    <span>{workflowName(workflows, job.workflow_id)}</span>
                    <div className="progress-track" aria-label={`${progressPercent(job)} percent complete`}>
                      <span style={{ width: `${progressPercent(job)}%` }} />
                    </div>
                    <div className="job-facts">
                      <span>{job.completed_items} succeeded</span>
                      <span>{job.failed_items} failed</span>
                      <span>{formatDuration(jobDurationMs(job))}</span>
                    </div>
                    <small>{new Date(job.created_at).toLocaleString()}</small>
                  </div>
                  <div className="job-actions">
                    <button className="secondary-button" type="button" onClick={() => showJobDetails(job.id)} title="Show details">
                      <ListChecks size={16} />
                      Details
                    </button>
                    {!isTerminal(job.status) && (
                      <>
                        <button className="secondary-button" type="button" disabled={busyJobId === job.id} onClick={() => void resumeJob(job)} title="Requeue unfinished documents after an interruption">
                          <RefreshCw size={16} />
                          Continue
                        </button>
                        <button className="danger-button" type="button" disabled={busyJobId === job.id} onClick={() => void cancelJob(job)} title="Cancel job">
                          <XCircle size={16} />
                          Cancel
                        </button>
                      </>
                    )}
                    <button
                      className="secondary-button"
                      type="button"
                      disabled={!isTerminal(job.status) || busyJobId === job.id}
                      onClick={() => void saveJobExport(job)}
                      title="Save Excel export"
                    >
                      <Download size={16} />
                      Excel
                    </button>
                  </div>
                  </article>
                ))}
              </div>
              {jobPageCount > 1 && (
                <nav className="queue-pagination" aria-label="Task queue pages">
                  <button
                    className="secondary-button"
                    disabled={jobPage === 0}
                    onClick={() => setJobPage((current) => Math.max(0, current - 1))}
                    type="button"
                  >
                    <ChevronLeft size={16} /> Previous
                  </button>
                  <span>Page <strong>{jobPage + 1}</strong> of {jobPageCount}</span>
                  <button
                    className="secondary-button"
                    disabled={jobPage >= jobPageCount - 1}
                    onClick={() => setJobPage((current) => Math.min(jobPageCount - 1, current + 1))}
                    type="button"
                  >
                    Next <ChevronRight size={16} />
                  </button>
                </nav>
              )}
            </>
          ))}
        </section>
      </section>

      <footer className="status-line panel">
        <strong>{status}</strong>
        {savedPath && <span>Last saved: {savedPath}</span>}
      </footer>

      {settingsOpen && (
        <div className="details-backdrop" role="presentation" onMouseDown={() => setSettingsOpen(false)}>
          <section
            aria-labelledby="llm-settings-title"
            aria-modal="true"
            className="settings-drawer"
            onMouseDown={(event) => event.stopPropagation()}
            role="dialog"
          >
            <header className="settings-header">
              <div>
                <span className="eyebrow">Runtime configuration</span>
                <h2 id="llm-settings-title">Model connection</h2>
                <p>Environment defaults or an encrypted, instance-local override.</p>
              </div>
              <button className="close-button" type="button" onClick={() => setSettingsOpen(false)} aria-label="Close settings">
                <X size={20} />
              </button>
            </header>

            {isLoadingSettings || !llmSettings ? (
              <p className="empty settings-loading">Loading provider settings…</p>
            ) : (
              <form className="settings-form" onSubmit={(event) => void saveLlmSettings(event)}>
                <div className="settings-mode" role="group" aria-label="Configuration source">
                  <button className={llmMode === 'environment' ? 'selected' : ''} type="button" onClick={() => setLlmMode('environment')}>
                    <Settings2 size={17} />
                    Environment
                  </button>
                  <button className={llmMode === 'custom' ? 'selected' : ''} type="button" onClick={() => setLlmMode('custom')}>
                    <KeyRound size={17} />
                    Custom
                  </button>
                </div>

                {llmMode === 'environment' ? (
                  <div className="environment-summary">
                    <span>Effective provider</span>
                    <strong>{llmSettings.provider}</strong>
                    <dl>
                      <div><dt>Base URL</dt><dd>{llmSettings.base_url || 'Provider default'}</dd></div>
                      <div><dt>Model</dt><dd>{llmSettings.model || 'Not configured'}</dd></div>
                      <div><dt>Temperature</dt><dd>{llmSettings.temperature.toFixed(2)}</dd></div>
                      <div><dt>API key</dt><dd>{llmSettings.api_key_configured ? 'Configured in environment' : 'Not configured'}</dd></div>
                    </dl>
                    <p>Saving this mode removes the database override. New work items read values from the backend environment.</p>
                  </div>
                ) : (
                  <div className="settings-fields">
                    <label>
                      <span>Provider protocol</span>
                      <select value={llmProvider} onChange={(event) => setLlmProvider(event.target.value as CustomLlmProvider)}>
                        <option value="openai_compatible">OpenAI compatible</option>
                        <option value="openrouter">OpenRouter</option>
                        <option value="anthropic">Anthropic</option>
                        <option value="fake">Fake / local test</option>
                      </select>
                    </label>
                    <label>
                      <span>Base URL</span>
                      <input value={llmBaseUrl} onChange={(event) => setLlmBaseUrl(event.target.value)} placeholder="https://api.example.com/v1" required={llmProvider === 'openai_compatible'} />
                    </label>
                    <label>
                      <span>Model</span>
                      <input value={llmModel} onChange={(event) => setLlmModel(event.target.value)} placeholder="Model identifier" />
                    </label>
                    <label>
                      <span>API key</span>
                      <input value={llmApiKey} onChange={(event) => setLlmApiKey(event.target.value)} type="password" autoComplete="off" placeholder={llmSettings.api_key_configured ? '••••••••  Leave blank to keep current key' : 'Enter provider API key'} />
                    </label>
                    <label className="temperature-field">
                      <span>Temperature</span>
                      <div>
                        <input min="0" max="2" step="0.05" type="range" value={llmTemperature} onChange={(event) => setLlmTemperature(Number(event.target.value))} />
                        <input min="0" max="2" step="0.05" type="number" value={llmTemperature} onChange={(event) => setLlmTemperature(Number(event.target.value))} />
                      </div>
                    </label>
                    {llmSettings.api_key_configured && (
                      <label className="clear-key-field">
                        <input type="checkbox" checked={clearLlmApiKey} onChange={(event) => setClearLlmApiKey(event.target.checked)} />
                        <span>Remove the saved key and fall back to the matching environment key</span>
                      </label>
                    )}
                    <p className="settings-security-note"><KeyRound size={15} /> The API key is encrypted on the backend and is never returned to this browser.</p>
                  </div>
                )}

                <div className="settings-actions">
                  <button className="secondary-button" type="button" onClick={() => setSettingsOpen(false)}>Cancel</button>
                  <button type="submit" disabled={isSavingSettings}>{isSavingSettings ? 'Saving…' : 'Save settings'}</button>
                </div>
              </form>
            )}
          </section>
        </div>
      )}

      {detailsOpen && selectedJob && selectedJobStats && (
        <div className="details-backdrop" role="presentation" onMouseDown={() => setDetailsOpen(false)}>
          <section
            aria-labelledby="task-details-title"
            aria-modal="true"
            className="details-drawer"
            onMouseDown={(event) => event.stopPropagation()}
            role="dialog"
          >
            <header className="details-header">
              <div>
                <span className="eyebrow">Extraction report / {shortId(selectedJob.id)}</span>
                <h2 id="task-details-title">Task details</h2>
                <p>{workflowName(workflows, selectedJob.workflow_id)} · v{selectedJob.workflow_version} · started {formatDateTime(selectedJob.started_at ?? selectedJob.created_at)}</p>
              </div>
              <div className="details-actions">
                <button
                  className="secondary-button"
                  type="button"
                  disabled={!isTerminal(selectedJob.status) || busyJobId === selectedJob.id}
                  onClick={() => void saveJobExport(selectedJob)}
                >
                  <Download size={17} />
                  Export Excel
                </button>
                <button className="close-button" type="button" onClick={() => setDetailsOpen(false)} aria-label="Close task details">
                  <X size={20} />
                </button>
              </div>
            </header>

            <div className="report-status">
              <span className={`status-badge ${selectedJob.status}`}>{selectedJob.status}</span>
              <div className="progress-track" aria-label={`${progressPercent(selectedJob)} percent complete`}>
                <span style={{ width: `${progressPercent(selectedJob)}%` }} />
              </div>
              <strong>{progressPercent(selectedJob)}%</strong>
            </div>

            <div className="detail-grid">
              <ReportMetric label="Processing time" value={formatDuration(selectedJobStats.elapsedMs)} hint="Wall-clock duration" />
              <ReportMetric label="Average time" value={formatDuration(selectedJobStats.averageItemMs)} hint={`Across ${selectedJobStats.timedItems} measured files`} />
              <ReportMetric label="Succeeded" value={selectedJob.completed_items} hint={`${selectedJobStats.successRate}% of processed files`} tone="success" />
              <ReportMetric label="Failed" value={selectedJob.failed_items} hint={selectedJob.failed_items ? 'Review errors below' : 'No extraction errors'} tone={selectedJob.failed_items ? 'danger' : undefined} />
              <ReportMetric label="Extracted items" value={selectedJobStats.extractedCount} hint={`From ${selectedJobStats.filesWithResults} files`} tone="accent" />
              <ReportMetric label="Processed" value={`${selectedJobStats.processed}/${selectedJob.total_items}`} hint={`${selectedJobStats.remaining} remaining`} />
            </div>

            <div className="results-heading">
              <div>
                <span className="eyebrow">Per-file results</span>
                <h3>Documents</h3>
              </div>
              <span>{items.length} files · {selectedJobStats.totalCharacters.toLocaleString()} text chars</span>
            </div>

            <div className="item-table">
              <div className="item-header">
                <span>File</span>
                <span>Status</span>
                <span>Time</span>
                <span>Items</span>
                <span>Result</span>
              </div>
              {items.length === 0 ? (
                <p className="empty table-empty">Loading item details…</p>
              ) : items.map((item) => (
                <div className="item-row" key={item.id}>
                  <span title={item.file_name}>{item.file_name}</span>
                  <span className={`status-badge ${item.status}`}>{item.status}</span>
                  <span>{formatDuration(item.duration_ms)}</span>
                  <strong>{resultCount(item)}</strong>
                  <span title={item.error_message ?? item.parsed_result?.error ?? resultLabel(item)}>
                    {item.error_message ?? item.parsed_result?.error ?? resultLabel(item)}
                  </span>
                </div>
              ))}
            </div>
          </section>
        </div>
      )}
    </main>
  );
}

function WorkflowConfigFields({
  workflow,
  tagValues,
  customFields,
  recentSchemas,
  onTagValueChange,
  onCustomFieldsChange,
}: {
  workflow: WorkflowOut;
  tagValues: Record<string, string>;
  customFields: CustomField[];
  recentSchemas: RecentSchema[];
  onTagValueChange: (key: string, value: string) => void;
  onCustomFieldsChange: (fields: CustomField[]) => void;
}) {
  function updateField(index: number, patch: Partial<CustomField>) {
    onCustomFieldsChange(customFields.map((field, current) => current === index ? { ...field, ...patch } : field));
  }

  return (
    <div className="workflow-config">
      {(workflow.ui_schema.controls ?? []).map((control) => (
        <div className="field" key={control.key}>
          <label>{control.label}</label>
          {control.help && <p className="field-help">{control.help}</p>}
          {control.control === 'field_builder' ? (
            <div className="field-builder">
              <p className="schema-persistence-note">
                Auto-saved in this browser. Every submitted task also keeps its own versioned schema snapshot.
              </p>
              <div className="recent-schema-picker">
                <div>
                  <strong>Recent schemas</strong>
                  <span>{recentSchemas.length ? 'Load fields from a recent task' : 'Recent custom tasks will appear here'}</span>
                </div>
                <select
                  aria-label="Choose a recent schema"
                  disabled={recentSchemas.length === 0}
                  onChange={(event) => {
                    const schema = recentSchemas.find((candidate) => candidate.jobId === event.target.value);
                    if (schema) onCustomFieldsChange(schema.fields.map((field) => ({ ...field })));
                  }}
                  value=""
                >
                  <option value="">Choose recent…</option>
                  {recentSchemas.map((schema) => (
                    <option key={schema.jobId} value={schema.jobId}>{recentSchemaLabel(schema)}</option>
                  ))}
                </select>
              </div>
              <div className="field-builder-head">
                <span>Key</span><span>Label & guidance</span><span>Type</span><span />
              </div>
              {customFields.map((field, index) => (
                <div className="field-definition" key={`field-${index}`}>
                  <input
                    aria-label={`Field ${index + 1} key`}
                    onChange={(event) => updateField(index, { key: normalizeFieldKey(event.target.value) })}
                    placeholder="effective_date"
                    value={field.key}
                  />
                  <div>
                    <input
                      aria-label={`Field ${index + 1} label`}
                      onChange={(event) => updateField(index, { label: event.target.value })}
                      placeholder="Effective date"
                      value={field.label}
                    />
                    <input
                      aria-label={`Field ${index + 1} guidance`}
                      onChange={(event) => updateField(index, { description: event.target.value })}
                      placeholder="What this field means and where to find it"
                      value={field.description}
                    />
                  </div>
                  <select
                    aria-label={`Field ${index + 1} type`}
                    onChange={(event) => updateField(index, { type: event.target.value as CustomField['type'] })}
                    value={field.type}
                  >
                    <option value="text">Text</option>
                    <option value="number">Number</option>
                    <option value="date">Date</option>
                    <option value="boolean">Boolean</option>
                    <option value="list">List</option>
                  </select>
                  <button
                    aria-label={`Remove field ${field.label || index + 1}`}
                    className="remove-field"
                    disabled={customFields.length === 1}
                    onClick={() => onCustomFieldsChange(customFields.filter((_, current) => current !== index))}
                    type="button"
                  >
                    <Trash2 size={16} />
                  </button>
                </div>
              ))}
              <button
                className="add-field secondary-button"
                disabled={customFields.length >= 50}
                onClick={() => onCustomFieldsChange([
                  ...customFields,
                  { key: '', label: '', type: 'text', description: '' },
                ])}
                type="button"
              >
                <Plus size={16} /> Add field
              </button>
            </div>
          ) : (
            <textarea
              className="properties"
              onChange={(event) => onTagValueChange(control.key, event.target.value)}
              placeholder={control.placeholder ?? 'One value per line, or comma-separated'}
              value={tagValues[control.key] ?? ''}
            />
          )}
        </div>
      ))}
    </div>
  );
}

function loadSavedCustomFields(): CustomField[] {
  try {
    const saved = localStorage.getItem(CUSTOM_SCHEMA_STORAGE_KEY);
    if (!saved) return DEFAULT_CUSTOM_FIELDS;
    return parseCustomFields(JSON.parse(saved)) ?? DEFAULT_CUSTOM_FIELDS;
  } catch {
    return DEFAULT_CUSTOM_FIELDS;
  }
}

function recentCustomSchemas(jobs: JobOut[]): RecentSchema[] {
  const seen = new Set<string>();
  const schemas: RecentSchema[] = [];
  for (const job of jobs) {
    if (job.workflow_id !== CUSTOM_RECORD_WORKFLOW_ID) continue;
    const fields = parseCustomFields(job.config.fields);
    if (!fields) continue;
    const fingerprint = JSON.stringify(fields);
    if (seen.has(fingerprint)) continue;
    seen.add(fingerprint);
    schemas.push({ jobId: job.id, createdAt: job.created_at, fields });
    if (schemas.length === 8) break;
  }
  return schemas;
}

function parseCustomFields(value: unknown): CustomField[] | null {
  if (!Array.isArray(value) || value.length === 0 || value.length > 50) return null;
  const allowedTypes = new Set<CustomField['type']>(['text', 'number', 'date', 'boolean', 'list']);
  if (!value.every((field): field is CustomField => (
    typeof field === 'object'
    && field !== null
    && typeof field.key === 'string'
    && typeof field.label === 'string'
    && typeof field.description === 'string'
    && 'type' in field
    && allowedTypes.has(field.type as CustomField['type'])
  ))) return null;
  return value;
}

function recentSchemaLabel(schema: RecentSchema) {
  const date = new Date(schema.createdAt).toLocaleString([], {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
  const keys = schema.fields.slice(0, 3).map((field) => field.key).join(', ');
  const remainder = schema.fields.length > 3 ? ` +${schema.fields.length - 3}` : '';
  return `${date} · ${keys}${remainder}`;
}

function buildWorkflowConfig(
  workflow: WorkflowOut,
  tagValues: Record<string, string>,
  customFields: CustomField[],
) {
  return Object.fromEntries((workflow.ui_schema.controls ?? []).map((control) => [
    control.key,
    control.control === 'field_builder'
      ? customFields.map((field) => ({
        ...field,
        key: field.key.trim(),
        label: field.label.trim(),
        description: field.description.trim(),
      }))
      : parseTagList(tagValues[control.key] ?? ''),
  ]));
}

function workflowConfigReady(
  workflow: WorkflowOut,
  tagValues: Record<string, string>,
  customFields: CustomField[],
) {
  const schema = workflow.config_schema as {
    required?: string[];
    properties?: Record<string, { minItems?: number; maxItems?: number }>;
  };
  return (workflow.ui_schema.controls ?? []).every((control) => {
    if (control.control === 'field_builder') {
      const keys = customFields.map((field) => field.key);
      return customFields.length > 0
        && new Set(keys).size === keys.length
        && customFields.every((field) => field.key && field.label && field.description);
    }
    const minimum = schema.properties?.[control.key]?.minItems ?? 0;
    const maximum = schema.properties?.[control.key]?.maxItems ?? Number.POSITIVE_INFINITY;
    const count = parseTagList(tagValues[control.key] ?? '').length;
    return (!schema.required?.includes(control.key) || count >= minimum) && count <= maximum;
  });
}

function parseTagList(value: string) {
  return [...new Set(value.split(/[\n,，]/).map((entry) => entry.trim()).filter(Boolean))];
}

function normalizeFieldKey(value: string) {
  return value.trimStart().replace(/[^A-Za-z0-9_]/g, '_').replace(/^[^A-Za-z]+/, '');
}

function workflowName(workflows: WorkflowOut[], workflowId: string) {
  return workflows.find((workflow) => workflow.id === workflowId)?.name ?? workflowId;
}

function workflowIcon(icon?: string) {
  if (icon === 'network') return <Network size={19} />;
  if (icon === 'table-properties') return <Braces size={19} />;
  return <Atom size={19} />;
}

function Metric({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="metric">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function ReportMetric({
  label,
  value,
  hint,
  tone,
}: {
  label: string;
  value: string | number;
  hint: string;
  tone?: 'success' | 'danger' | 'accent';
}) {
  return (
    <div className={`report-metric${tone ? ` ${tone}` : ''}`}>
      <span>{label}</span>
      <strong>{value}</strong>
      <small>{hint}</small>
    </div>
  );
}

function statusIcon(status: string) {
  if (status === 'completed' || status === 'done') return <CheckCircle2 size={18} />;
  if (status === 'failed' || status === 'cancelled') return <XCircle size={18} />;
  return <Clock3 size={18} />;
}

function downloadBytes(content: ArrayBuffer, filename: string) {
  const blob = new Blob([content], {
    type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
  });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = filename;
  anchor.click();
  URL.revokeObjectURL(url);
}
