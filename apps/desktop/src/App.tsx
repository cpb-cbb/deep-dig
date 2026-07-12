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
  X,
  XCircle,
} from 'lucide-react';
import { useEffect, useMemo, useRef, useState, type FormEvent } from 'react';
import { apiDownload, apiFetch, apiPublicFetch } from './api';
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
  duration_ms: number | null;
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
const ACTIVE_JOB_REFRESH_MS = 6_000;

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
  const [isLoadingModes, setIsLoadingModes] = useState(false);
  const [isAuthenticating, setIsAuthenticating] = useState(false);
  const [isSelectingFiles, setIsSelectingFiles] = useState(false);
  const [isSelectingOutput, setIsSelectingOutput] = useState(false);
  const [isAppVisible, setIsAppVisible] = useState(
    () => document.visibilityState === 'visible' && document.hasFocus(),
  );
  const [busyJobId, setBusyJobId] = useState<string | null>(null);
  const [detailsOpen, setDetailsOpen] = useState(false);
  const refreshInFlightRef = useRef(false);
  const lastManualRefreshRef = useRef(0);
  const modesInFlightRef = useRef(false);
  const lastModesRefreshRef = useRef(0);
  const itemLoadsInFlightRef = useRef(new Set<string>());
  const submitInFlightRef = useRef(false);
  const pendingIdempotencyKeyRef = useRef<string | null>(null);
  const pendingSubmissionFingerprintRef = useRef<string | null>(null);
  const authInFlightRef = useRef(false);
  const parseInFlightRef = useRef(false);
  const fileDialogInFlightRef = useRef(false);
  const outputDialogInFlightRef = useRef(false);
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
      && (modeId !== 'material_extraction' || requestedProperties().length > 0),
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

  async function loadModes(manual = false) {
    const now = Date.now();
    if (modesInFlightRef.current) return;
    if (manual && now - lastModesRefreshRef.current < 3000) {
      setStatus('Extraction modes were just refreshed.');
      return;
    }
    modesInFlightRef.current = true;
    if (manual) lastModesRefreshRef.current = now;
    setIsLoadingModes(true);
    try {
      const data = await apiPublicFetch<ExtractionMode[]>('/workflows');
      setModes(data);
      if (data.some((mode) => mode.id === 'material_extraction')) {
        setModeId('material_extraction');
      } else if (data[0]) {
        setModeId(data[0].id);
      }
    } catch (error) {
      setStatus(errorMessage(error));
    } finally {
      modesInFlightRef.current = false;
      setIsLoadingModes(false);
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
      if (authMode === 'sign-up') {
        await signUp();
        return;
      }
      if (authMode === 'reset-password') {
        await sendPasswordReset();
        return;
      }
      await signIn();
    } finally {
      authInFlightRef.current = false;
      setIsAuthenticating(false);
    }
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
      setParsedStorageDir('');
      setStatus(selected.length ? `Selected ${selected.length} PDF(s). Confirm local parsing when ready.` : 'Ready');
    } catch (error) {
      setStatus(errorMessage(error));
    } finally {
      fileDialogInFlightRef.current = false;
      setIsSelectingFiles(false);
    }
  }

  async function selectParsedOutputDir() {
    if (outputDialogInFlightRef.current) return;
    outputDialogInFlightRef.current = true;
    setIsSelectingOutput(true);
    try {
      const selected = await chooseParsedOutputDir();
      if (selected) {
        setParsedOutputDir(selected);
        setStatus(`Parsed text will be saved under ${selected}`);
      }
    } catch (error) {
      setStatus(errorMessage(error));
    } finally {
      outputDialogInFlightRef.current = false;
      setIsSelectingOutput(false);
    }
  }

  async function parseSelectedFiles() {
    if (selectedFiles.length === 0 || parseInFlightRef.current) return;
    if (!parsedOutputDir) {
      setStatus('Choose a parsed text folder before parsing PDFs.');
      return;
    }
    parseInFlightRef.current = true;
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
      const config = modeId === 'material_extraction' ? { properties } : {};
      const submissionFingerprint = JSON.stringify({
        modeId,
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
          workflow_id: modeId,
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
      setSelectedJobId(result.job_id);
      await refreshJobs(true);
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
      await refreshJobs(true);
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
      const target = await pickExcelSavePath(`deep-dig-${job.id}.xlsx`);
      if (!target) return;
      const content = await apiDownload(`/jobs/${job.id}/export.xlsx`, token);
      await saveBytesToPath(target, new Uint8Array(content));
      setSavedPath(target);
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
          <button className="secondary-button" type="button" disabled={isLoadingModes} onClick={() => void loadModes(true)} title="Refresh extraction modes">
            <RefreshCw className={isLoadingModes ? 'spinning' : ''} size={18} />
            {isLoadingModes ? 'Loading' : 'Modes'}
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
              <button type="submit" disabled={isAuthenticating || (supabase ? !email || (authMode !== 'reset-password' && !password) : false)}>
                {authModeIcon(authMode)}
                {isAuthenticating ? 'Please wait…' : authButtonLabel(authMode, isDevAuth)}
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

          <button className="drop" type="button" disabled={isSelectingFiles} onClick={selectFiles}>
            <FileText size={24} />
            <span>{isSelectingFiles ? 'Opening file picker…' : 'Select PDFs'}</span>
          </button>

          <button className="secondary-button" type="button" disabled={isSelectingOutput} onClick={() => void selectParsedOutputDir()}>
            <FolderOutput size={18} />
            {isSelectingOutput ? 'Opening folder picker…' : parsedOutputDir ? 'Change parsed text folder' : 'Choose parsed text folder'}
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
            <button className="icon-button" type="button" disabled={isLoadingJobs} onClick={() => void refreshJobs()} title="Refresh jobs">
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
                    <span>{workflowName(job.workflow_id, modes)}</span>
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
                <p>{workflowName(selectedJob.workflow_id, modes)} · started {formatDateTime(selectedJob.started_at ?? selectedJob.created_at)}</p>
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

function calculateJobStats(job: JobOut, items: JobItemOut[]) {
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

function jobDurationMs(job: JobOut) {
  if (!job.started_at) return null;
  const started = new Date(job.started_at).getTime();
  const finished = job.finished_at ? new Date(job.finished_at).getTime() : Date.now();
  return Math.max(0, finished - started);
}

function formatDuration(milliseconds: number | null) {
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

function formatDateTime(value: string | null) {
  return value ? new Date(value).toLocaleString() : '—';
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
