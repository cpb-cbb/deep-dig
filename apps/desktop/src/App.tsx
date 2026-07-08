import { createClient } from '@supabase/supabase-js';
import {
  CheckCircle2,
  Clock3,
  Download,
  FileText,
  FolderOutput,
  KeyRound,
  ListChecks,
  LogIn,
  LogOut,
  Play,
  RefreshCw,
  UserPlus,
  XCircle,
} from 'lucide-react';
import { useEffect, useMemo, useState, type FormEvent } from 'react';
import { API_BASE, apiDownload, apiFetch } from './api';
import { chooseParsedOutputDir, parsePdfToMarkdown, pickExcelSavePath, saveBytesToPath, selectPdfFiles, type ParsedFile, type SelectedPdf } from './native';

type ExtractionMode = {
  id: string;
  name: string;
  description: string;
  ui_config: Record<string, unknown>;
};

type JobOut = {
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

type ParsedResult = {
  success?: boolean;
  samples?: Array<{ name?: string; properties?: Record<string, unknown> }>;
  error?: string | null;
};

type JobItemOut = {
  id: string;
  ordinal: number;
  file_name: string;
  file_hash: string;
  text_length: number;
  status: string;
  parsed_result: ParsedResult | null;
  error_code: string | null;
  error_message: string | null;
  finished_at: string | null;
};

type MeOut = {
  email: string | null;
  display_name: string | null;
  plan: string;
  quota: {
    limit: number;
    used: number;
    reset_at?: string;
  };
};

type AuthMode = 'sign-in' | 'sign-up' | 'reset-password';

const SUPABASE_URL = import.meta.env.VITE_SUPABASE_URL as string | undefined;
const SUPABASE_ANON_KEY = import.meta.env.VITE_SUPABASE_ANON_KEY as string | undefined;
const DEV_TOKEN = (import.meta.env.VITE_DEV_AUTH_TOKEN as string | undefined) ?? (import.meta.env.DEV ? 'dev' : '');
const isDevAuth = !SUPABASE_URL || !SUPABASE_ANON_KEY;

function createSupabaseAuthClient() {
  if (!SUPABASE_URL || !SUPABASE_ANON_KEY) return null;
  return createClient(SUPABASE_URL, SUPABASE_ANON_KEY);
}

const supabase = createSupabaseAuthClient();

export function App() {
  const [token, setToken] = useState('');
  const [authMode, setAuthMode] = useState<AuthMode>('sign-in');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [profile, setProfile] = useState<MeOut | null>(null);
  const [modes, setModes] = useState<ExtractionMode[]>([]);
  const [modeId, setModeId] = useState('material_extraction');
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
  const [parsedOutputDir, setParsedOutputDir] = useState('');
  const [parseReusedCount, setParseReusedCount] = useState(0);
  const [parsedStorageDir, setParsedStorageDir] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isLoadingJobs, setIsLoadingJobs] = useState(false);
  const [busyJobId, setBusyJobId] = useState<string | null>(null);

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
      && (modeId !== 'material_extraction' || requestedProperties().length > 0),
  );

  useEffect(() => {
    void loadModes();
  }, []);

  useEffect(() => {
    if (!supabase) return undefined;

    void supabase.auth.getSession().then(({ data }) => {
      if (data.session?.access_token) setToken(data.session.access_token);
    });
    const { data } = supabase.auth.onAuthStateChange((_event, session) => {
      setToken(session?.access_token ?? '');
    });
    return () => data.subscription.unsubscribe();
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
    if (!token.trim()) return undefined;
    const interval = window.setInterval(() => {
      void refreshJobs(true);
      if (selectedJobId) void loadJobItems(selectedJobId, true);
    }, 2500);
    return () => window.clearInterval(interval);
  }, [token, selectedJobId]);

  useEffect(() => {
    if (!selectedJobId || !token.trim()) {
      setItems([]);
      return;
    }
    void loadJobItems(selectedJobId);
  }, [selectedJobId, token]);

  function requestedProperties() {
    return propertiesText
      .split(/[\n,，]/)
      .map((property) => property.trim())
      .filter(Boolean);
  }

  async function loadModes() {
    try {
      const response = await fetch(`${API_BASE}/workflows`);
      if (!response.ok) throw new Error(response.statusText || 'Failed to load workflows');
      const data = (await response.json()) as ExtractionMode[];
      setModes(data);
      if (data.some((mode) => mode.id === 'material_extraction')) {
        setModeId('material_extraction');
      } else if (data[0]) {
        setModeId(data[0].id);
      }
    } catch (error) {
      setStatus(errorMessage(error));
    }
  }

  async function loadAccount() {
    try {
      setProfile(await apiFetch<MeOut>('/me', token));
    } catch (error) {
      setStatus(errorMessage(error));
    }
  }

  async function refreshJobs(silent = false) {
    if (!token.trim()) return;
    try {
      if (!silent) setIsLoadingJobs(true);
      const data = await apiFetch<JobOut[]>('/jobs', token);
      setJobs(data);
      setSelectedJobId((current) => {
        if (current && data.some((job) => job.id === current)) return current;
        return data[0]?.id ?? null;
      });
    } catch (error) {
      if (!silent) setStatus(errorMessage(error));
    } finally {
      if (!silent) setIsLoadingJobs(false);
    }
  }

  async function loadJobItems(jobId: string, silent = false) {
    try {
      setItems(await apiFetch<JobItemOut[]>(`/jobs/${jobId}/items`, token));
    } catch (error) {
      if (!silent) setStatus(errorMessage(error));
    }
  }

  async function submitAuth(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (authMode === 'sign-up') {
      await signUp();
      return;
    }
    if (authMode === 'reset-password') {
      await sendPasswordReset();
      return;
    }
    await signIn();
  }

  async function signIn() {
    if (!supabase) {
      setToken(DEV_TOKEN);
      setStatus('Signed in with local dev auth.');
      return;
    }
    setStatus('Signing in...');
    const { data, error } = await supabase.auth.signInWithPassword({ email, password });
    if (error) {
      setStatus(error.message);
      return;
    }
    setToken(data.session?.access_token ?? '');
    setStatus('Signed in.');
  }

  async function signUp() {
    if (!supabase) {
      setToken(DEV_TOKEN);
      setStatus('Signed in with local dev auth.');
      return;
    }
    setStatus('Creating account...');
    const { data, error } = await supabase.auth.signUp({ email, password });
    if (error) {
      setStatus(error.message);
      return;
    }
    if (data.session?.access_token) {
      setToken(data.session.access_token);
      setStatus('Account created.');
      return;
    }
    setStatus('Account created. Check your email to confirm it, then sign in.');
    setAuthMode('sign-in');
  }

  async function sendPasswordReset() {
    if (!supabase) {
      setStatus('Password reset is not available in local dev auth.');
      return;
    }
    setStatus('Sending password reset email...');
    const { error } = await supabase.auth.resetPasswordForEmail(email);
    if (error) {
      setStatus(error.message);
      return;
    }
    setStatus('Password reset email sent.');
    setAuthMode('sign-in');
  }

  async function signOut() {
    if (supabase) {
      await supabase.auth.signOut();
    } else {
      setStatus('Signed out.');
    }
    setToken('');
    setProfile(null);
    setJobs([]);
    setItems([]);
    setSelectedJobId(null);
  }

  async function selectFiles() {
    setStatus('Selecting PDFs...');
    try {
      const selected = await selectPdfFiles();
      setSelectedFiles(selected);
      setFiles([]);
      setParseProgress(0);
      setParseReusedCount(0);
      setParsedStorageDir('');
      setStatus(selected.length ? `Selected ${selected.length} PDF(s). Confirm local parsing when ready.` : 'Ready');
    } catch (error) {
      setStatus(errorMessage(error));
    }
  }

  async function selectParsedOutputDir() {
    try {
      const selected = await chooseParsedOutputDir();
      if (selected) {
        setParsedOutputDir(selected);
        setStatus(`Parsed text will be saved under ${selected}`);
      }
    } catch (error) {
      setStatus(errorMessage(error));
    }
  }

  async function parseSelectedFiles() {
    if (selectedFiles.length === 0 || isParsing) return;
    if (!parsedOutputDir) {
      setStatus('Choose a parsed text folder before parsing PDFs.');
      return;
    }
    setIsParsing(true);
    setFiles([]);
    setParseProgress(0);
    setParseReusedCount(0);
    setParsedStorageDir('');
    setStatus('Parsing PDFs locally...');
    const parsed: ParsedFile[] = [];
    let reusedCount = 0;
    try {
      for (const [index, file] of selectedFiles.entries()) {
        setStatus(`Parsing ${index + 1}/${selectedFiles.length}: ${file.fileName}`);
        const result = await parsePdfToMarkdown(file.path, parsedOutputDir);
        parsed.push(result);
        if (result.reused) reusedCount += 1;
        setFiles([...parsed]);
        setParseReusedCount(reusedCount);
        setParseProgress(index + 1);
        if (result.storagePath) setParsedStorageDir(result.storagePath.replace(/[/\\][^/\\]+$/, ''));
      }
      setStatus(`Parsed ${parsed.length} PDF(s). Review the summary, then start extraction.`);
    } catch (error) {
      setStatus(errorMessage(error));
    } finally {
      setIsParsing(false);
    }
  }

  async function submitJob() {
    if (!canSubmit) return;
    setIsSubmitting(true);
    setStatus('Submitting job...');
    try {
      const properties = requestedProperties();
      const config = modeId === 'material_extraction' ? { properties } : {};
      const result = await apiFetch<{ job_id: string; queued_items: number }>('/jobs', token, {
        method: 'POST',
        body: JSON.stringify({
          workflow_id: modeId,
          config,
          items: files.map((file) => ({
            file_name: file.fileName,
            file_hash: file.fileHash,
            text: file.text,
          })),
        }),
      });
      setStatus(`Queued job ${shortId(result.job_id)} with ${result.queued_items} item(s).`);
      setSelectedJobId(result.job_id);
      await refreshJobs(true);
    } catch (error) {
      setStatus(errorMessage(error));
    } finally {
      setIsSubmitting(false);
    }
  }

  async function cancelJob(job: JobOut) {
    setBusyJobId(job.id);
    try {
      await apiFetch<JobOut>(`/jobs/${job.id}/cancel`, token, { method: 'POST' });
      setStatus(`Cancelled job ${shortId(job.id)}.`);
      await refreshJobs(true);
    } catch (error) {
      setStatus(errorMessage(error));
    } finally {
      setBusyJobId(null);
    }
  }

  async function saveJobExport(job: JobOut) {
    setBusyJobId(job.id);
    try {
      const target = await pickExcelSavePath(`deep-dig-${job.id}.xlsx`);
      if (!target) return;
      const content = await apiDownload(`/jobs/${job.id}/export.xlsx`, token);
      await saveBytesToPath(target, new Uint8Array(content));
      setSavedPath(target);
      setStatus(`Saved ${shortId(job.id)} export.`);
    } catch (error) {
      setStatus(errorMessage(error));
    } finally {
      setBusyJobId(null);
    }
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
          <button className="secondary-button" type="button" onClick={loadModes} title="Refresh extraction modes">
            <RefreshCw size={18} />
            Modes
          </button>
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
              {!isDevAuth && (
                <div className="auth-tabs" aria-label="Account action">
                  <button className={authMode === 'sign-in' ? 'selected' : ''} type="button" onClick={() => setAuthMode('sign-in')}>
                    <LogIn size={16} />
                    Sign in
                  </button>
                  <button className={authMode === 'sign-up' ? 'selected' : ''} type="button" onClick={() => setAuthMode('sign-up')}>
                    <UserPlus size={16} />
                    Register
                  </button>
                  <button className={authMode === 'reset-password' ? 'selected' : ''} type="button" onClick={() => setAuthMode('reset-password')}>
                    <KeyRound size={16} />
                    Reset
                  </button>
                </div>
              )}
              <label>Email</label>
              <input value={email} onChange={(event) => setEmail(event.target.value)} type="email" autoComplete="email" placeholder={isDevAuth ? 'dev@deepdig.local' : undefined} />
              {authMode !== 'reset-password' && (
                <>
                  <label>Password</label>
                  <input
                    value={password}
                    onChange={(event) => setPassword(event.target.value)}
                    type="password"
                    autoComplete={authMode === 'sign-up' ? 'new-password' : 'current-password'}
                    placeholder={isDevAuth ? 'Any password in dev mode' : undefined}
                  />
                </>
              )}
              <button type="submit" disabled={supabase ? !email || (authMode !== 'reset-password' && !password) : false}>
                {authModeIcon(authMode)}
                {authButtonLabel(authMode, isDevAuth)}
              </button>
            </form>
          )}

          <div className="field">
            <label>Extraction mode</label>
            <select value={modeId} onChange={(event) => setModeId(event.target.value)}>
              {modes.length === 0 && <option value="material_extraction">Material Science Data Extraction</option>}
              {modes.map((mode) => <option key={mode.id} value={mode.id}>{mode.name}</option>)}
            </select>
          </div>

          {modeId === 'material_extraction' && (
            <div className="field">
              <label>Properties to extract</label>
              <textarea
                className="properties"
                value={propertiesText}
                onChange={(event) => setPropertiesText(event.target.value)}
                placeholder="One property per line, or separate with commas"
              />
            </div>
          )}

          <button className="drop" type="button" onClick={selectFiles}>
            <FileText size={24} />
            <span>Select PDFs</span>
          </button>

          <button className="secondary-button" type="button" onClick={() => void selectParsedOutputDir()}>
            <FolderOutput size={18} />
            {parsedOutputDir ? 'Change parsed text folder' : 'Choose parsed text folder'}
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
              {parsedOutputDir && <span className="storage-path">Output: {parsedOutputDir}</span>}
              {parsedStorageDir && <span className="storage-path">Parsed files: {parsedStorageDir}</span>}
            </div>
          )}

          <div className="compose-actions">
            <button className="secondary-button" disabled={selectedFiles.length === 0 || !parsedOutputDir || isParsing} onClick={() => void parseSelectedFiles()} type="button">
              <RefreshCw size={18} />
              {isParsing ? 'Parsing' : 'Parse locally'}
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
            <button className="icon-button" type="button" onClick={() => void refreshJobs()} title="Refresh jobs">
              <RefreshCw size={18} />
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
                    <span>{workflowName(job.workflow_id, modes)}</span>
                    <div className="progress-track" aria-label={`${progressPercent(job)} percent complete`}>
                      <span style={{ width: `${progressPercent(job)}%` }} />
                    </div>
                    <small>
                      {job.completed_items + job.failed_items}/{job.total_items} processed · {new Date(job.created_at).toLocaleString()}
                    </small>
                  </div>
                  <div className="job-actions">
                    <button className="secondary-button" type="button" onClick={() => setSelectedJobId(job.id)} title="Show details">
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

      <section className="panel details-panel">
        <div className="panel-title">
          <div>
            <h2>Task details</h2>
            <span>{selectedJob ? `${shortId(selectedJob.id)} · ${selectedJob.status}` : 'No task selected'}</span>
          </div>
          {selectedJob && (
            <button
              className="secondary-button"
              type="button"
              disabled={!isTerminal(selectedJob.status) || busyJobId === selectedJob.id}
              onClick={() => void saveJobExport(selectedJob)}
              title="Choose save path"
            >
              <FolderOutput size={18} />
              Save as
            </button>
          )}
        </div>

        {selectedJob ? (
          <>
            <div className="detail-grid">
              <Metric label="Total" value={selectedJob.total_items} />
              <Metric label="Completed" value={selectedJob.completed_items} />
              <Metric label="Failed" value={selectedJob.failed_items} />
              <Metric label="Progress" value={`${progressPercent(selectedJob)}%`} />
            </div>

            <div className="item-table">
              <div className="item-header">
                <span>File</span>
                <span>Status</span>
                <span>Samples</span>
                <span>Result</span>
              </div>
              {items.length === 0 ? (
                <p className="empty">No item details loaded.</p>
              ) : items.map((item) => (
                <div className="item-row" key={item.id}>
                  <span>{item.file_name}</span>
                  <span className={`status-badge ${item.status}`}>{item.status}</span>
                  <span>{sampleCount(item)}</span>
                  <span>{item.error_message ?? item.parsed_result?.error ?? resultLabel(item)}</span>
                </div>
              ))}
            </div>
          </>
        ) : (
          <p className="empty">Select a task to inspect its item results.</p>
        )}

        <footer className="status-line">
          <strong>{status}</strong>
          {savedPath && <span>Last saved: {savedPath}</span>}
        </footer>
      </section>
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

function workflowName(workflowId: string, modes: ExtractionMode[]) {
  return modes.find((mode) => mode.id === workflowId)?.name ?? workflowId;
}

function progressPercent(job: JobOut) {
  if (!job.total_items) return 0;
  return Math.round(((job.completed_items + job.failed_items) / job.total_items) * 100);
}

function isTerminal(status: string) {
  return ['completed', 'failed', 'cancelled'].includes(status);
}

function shortId(id: string) {
  return id.slice(0, 8);
}

function sampleCount(item: JobItemOut) {
  return item.parsed_result?.samples?.length ?? 0;
}

function resultLabel(item: JobItemOut) {
  if (item.status === 'done') return `${sampleCount(item)} sample(s) parsed`;
  if (item.status === 'running') return 'Processing';
  if (item.status === 'pending') return 'Queued';
  return 'No parsed result';
}

function parseStatusLabel(parsedCount: number, selectedCount: number) {
  if (selectedCount === 0) return 'No PDFs selected';
  if (parsedCount === selectedCount) return 'Ready to submit';
  if (parsedCount > 0) return `${parsedCount}/${selectedCount} parsed`;
  return 'Waiting for local parsing';
}

function statusIcon(status: string) {
  if (status === 'completed' || status === 'done') return <CheckCircle2 size={18} />;
  if (status === 'failed' || status === 'cancelled') return <XCircle size={18} />;
  return <Clock3 size={18} />;
}

function authModeIcon(mode: AuthMode) {
  if (mode === 'sign-up') return <UserPlus size={18} />;
  if (mode === 'reset-password') return <KeyRound size={18} />;
  return <LogIn size={18} />;
}

function authButtonLabel(mode: AuthMode, devAuth: boolean) {
  if (devAuth) return 'Sign in with dev auth';
  if (mode === 'sign-up') return 'Create account';
  if (mode === 'reset-password') return 'Send reset email';
  return 'Sign in';
}

function errorMessage(error: unknown) {
  if (error instanceof Error) return error.message;
  if (typeof error === 'object' && error && 'message' in error) {
    return String((error as { message?: unknown }).message ?? 'Request failed');
  }
  return String(error);
}
