import {
  CheckCircle2,
  Clock3,
  Download,
  FileText,
  ListChecks,
  LogIn,
  LogOut,
  Play,
  RefreshCw,
  X,
  XCircle,
} from 'lucide-react';
import { useEffect, useMemo, useRef, useState, type FormEvent } from 'react';
import { apiDownload, apiFetch } from './api';
import {
  MATERIAL_EXTRACTION_WORKFLOW_ID,
  MATERIAL_EXTRACTION_WORKFLOW_NAME,
  calculateJobStats,
  errorMessage,
  formatDateTime,
  formatDuration,
  isTerminal,
  jobDurationMs,
  parseStatusLabel,
  progressPercent,
  resultLabel,
  sampleCount,
  shortId,
  type JobItemOut,
  type JobOut,
  type MeOut,
  type ParsedFile,
  type SelectedPdf,
} from './domain';
import { parseFiles, selectPdfFiles } from './files';

const TOKEN_STORAGE_KEY = 'deep-dig-token';
const ACTIVE_JOB_REFRESH_MS = 6_000;
const ACCOUNT_REFRESH_MS = 30_000;

export function App() {
  const [token, setToken] = useState('');
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [profile, setProfile] = useState<MeOut | null>(null);
  const [selectedFiles, setSelectedFiles] = useState<SelectedPdf[]>([]);
  const [files, setFiles] = useState<ParsedFile[]>([]);
  const [jobs, setJobs] = useState<JobOut[]>([]);
  const [selectedJobId, setSelectedJobId] = useState<string | null>(null);
  const [items, setItems] = useState<JobItemOut[]>([]);
  const [status, setStatus] = useState('Ready');
  const [savedPath, setSavedPath] = useState('');
  const [propertiesText, setPropertiesText] = useState('BET surface area\ntotal pore volume\nspecific capacitance');
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
  const filesTextLength = useMemo(() => files.reduce((sum, file) => sum + file.textLength, 0), [files]);
  const parsePercent = selectedFiles.length ? Math.round((parseProgress / selectedFiles.length) * 100) : 0;
  const canSubmit = Boolean(
    token.trim()
      && files.length > 0
      && !isParsing
      && !isSubmitting
      && requestedProperties().length > 0,
  );
  const selectedJobStats = useMemo(
    () => selectedJob ? calculateJobStats(selectedJob, items) : null,
    [selectedJob, items],
  );
  const hasActiveJobs = useMemo(
    () => jobs.some((job) => job.status === 'pending' || job.status === 'running'),
    [jobs],
  );

  useEffect(() => {
    const saved = localStorage.getItem(TOKEN_STORAGE_KEY);
    if (saved) setToken(saved);
  }, []);

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
    if (!detailsOpen) return undefined;
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === 'Escape') setDetailsOpen(false);
    };
    window.addEventListener('keydown', closeOnEscape);
    return () => window.removeEventListener('keydown', closeOnEscape);
  }, [detailsOpen]);

  function requestedProperties() {
    return propertiesText
      .split(/[\n,，]/)
      .map((property) => property.trim())
      .filter(Boolean);
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
    if (!canSubmit || submitInFlightRef.current) return;
    submitInFlightRef.current = true;
    setIsSubmitting(true);
    setStatus('Submitting job...');
    try {
      const properties = requestedProperties();
      const submissionFingerprint = JSON.stringify({
        properties,
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
          workflow_id: MATERIAL_EXTRACTION_WORKFLOW_ID,
          config: { properties },
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
          <p>Extract structured materials data from local PDFs.</p>
        </div>
        <div className="topbar-actions">
          {profile && (
            <div className="account-pill">
              <span>{profile.email ?? profile.display_name ?? 'Signed in'}</span>
              <strong>{profile.quota.used}/{profile.quota.limit}</strong>
            </div>
          )}
          {token.trim() && (
            <button className="secondary-button" type="button" onClick={signOut} title="Sign out">
              <LogOut size={18} />
              Sign out
            </button>
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

          <div className="field">
            <label>Properties to extract</label>
            <textarea
              className="properties"
              value={propertiesText}
              onChange={(event) => setPropertiesText(event.target.value)}
              placeholder="One property per line, or separate with commas"
            />
          </div>

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

        <section className="panel queue-panel">
          <div className="panel-title">
            <div>
              <h2>Task queue</h2>
              <span>{jobs.length} recent jobs</span>
            </div>
            <button className="icon-button" type="button" disabled={isLoadingJobs} onClick={() => void refreshDashboard()} title="Refresh jobs and account">
              <RefreshCw className={isLoadingJobs ? 'spinning' : ''} size={18} />
            </button>
          </div>

          {!token.trim() ? (
            <p className="empty">Sign in to load tasks.</p>
          ) : jobs.length === 0 ? (
            <p className="empty">{isLoadingJobs ? 'Loading tasks...' : 'No tasks yet.'}</p>
          ) : (
            <div className="job-list">
              {jobs.map((job) => (
                <article className={job.id === selectedJob?.id ? 'job-row selected' : 'job-row'} key={job.id}>
                  <div className="job-main">
                    <div className="job-heading">
                      {statusIcon(job.status)}
                      <strong>{shortId(job.id)}</strong>
                      <span className={`status-badge ${job.status}`}>{job.status}</span>
                    </div>
                    <span>{MATERIAL_EXTRACTION_WORKFLOW_NAME}</span>
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
                      <button className="danger-button" type="button" disabled={busyJobId === job.id} onClick={() => void cancelJob(job)} title="Cancel job">
                        <XCircle size={16} />
                        Cancel
                      </button>
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
          )}
        </section>
      </section>

      <footer className="status-line panel">
        <strong>{status}</strong>
        {savedPath && <span>Last saved: {savedPath}</span>}
      </footer>

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
                <p>{MATERIAL_EXTRACTION_WORKFLOW_NAME} · started {formatDateTime(selectedJob.started_at ?? selectedJob.created_at)}</p>
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
              <ReportMetric label="Samples found" value={selectedJobStats.sampleCount} hint={`From ${selectedJobStats.filesWithSamples} files`} tone="accent" />
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
                <span>Samples</span>
                <span>Result</span>
              </div>
              {items.length === 0 ? (
                <p className="empty table-empty">Loading item details…</p>
              ) : items.map((item) => (
                <div className="item-row" key={item.id}>
                  <span title={item.file_name}>{item.file_name}</span>
                  <span className={`status-badge ${item.status}`}>{item.status}</span>
                  <span>{formatDuration(item.duration_ms)}</span>
                  <strong>{sampleCount(item)}</strong>
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
