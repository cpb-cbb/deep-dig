import { FileText, Play, RefreshCw } from 'lucide-react';
import { useState } from 'react';
import { apiFetch } from './api';
import { parsePdfText } from './pdf';

type Workflow = { id: string; name: string; description: string; ui_config: Record<string, unknown> };
type ParsedFile = { fileName: string; fileHash: string; text: string };

export function App() {
  const [token, setToken] = useState('');
  const [workflows, setWorkflows] = useState<Workflow[]>([]);
  const [workflowId, setWorkflowId] = useState('code_friendly');
  const [files, setFiles] = useState<ParsedFile[]>([]);
  const [status, setStatus] = useState('Ready');

  async function loadWorkflows() {
    const data = await fetch(`${import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000'}/workflows`).then((r) => r.json());
    setWorkflows(data);
    if (data[0]) setWorkflowId(data[0].id);
  }

  async function onFiles(selected: FileList | null) {
    if (!selected) return;
    setStatus('Parsing PDFs locally...');
    const parsed = await Promise.all(Array.from(selected).map(parsePdfText));
    setFiles(parsed);
    setStatus(`Parsed ${parsed.length} PDF(s).`);
  }

  async function submitJob() {
    setStatus('Submitting job...');
    const result = await apiFetch<{ job_id: string }>('/jobs', token, {
      method: 'POST',
      body: JSON.stringify({ workflow_id: workflowId, config: {}, items: files.map((file) => ({ file_name: file.fileName, file_hash: file.fileHash, text: file.text })) }),
    });
    setStatus(`Queued job ${result.job_id}`);
  }

  return (
    <main className="shell">
      <section className="toolbar">
        <div>
          <h1>Deep Dig</h1>
          <p>Local PDF parsing, backend-owned AI extraction.</p>
        </div>
        <button onClick={loadWorkflows} title="Load workflows"><RefreshCw size={18} /> Workflows</button>
      </section>
      <section className="panel">
        <label>Bearer token</label>
        <textarea value={token} onChange={(event) => setToken(event.target.value)} placeholder="Supabase access token for development" />
        <label>Workflow</label>
        <select value={workflowId} onChange={(event) => setWorkflowId(event.target.value)}>
          {workflows.length === 0 && <option value="code_friendly">code_friendly</option>}
          {workflows.map((workflow) => <option key={workflow.id} value={workflow.id}>{workflow.name}</option>)}
        </select>
        <label className="drop">
          <FileText size={24} />
          <span>Select PDFs</span>
          <input type="file" accept="application/pdf" multiple onChange={(event) => onFiles(event.target.files)} />
        </label>
        <button disabled={!token || files.length === 0} onClick={submitJob}><Play size={18} /> Start extraction</button>
      </section>
      <section className="panel">
        <strong>{status}</strong>
        <ul>{files.map((file) => <li key={file.fileHash}>{file.fileName} · {file.text.length.toLocaleString()} chars</li>)}</ul>
      </section>
    </main>
  );
}
