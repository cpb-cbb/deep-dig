import { FileText, Play, RefreshCw } from 'lucide-react';
import { useState } from 'react';
import { apiFetch } from './api';
import { ParsedFile, selectAndParsePdfs } from './native';

type ExtractionMode = { id: string; name: string; description: string; ui_config: Record<string, unknown> };

export function App() {
  const [token, setToken] = useState('');
  const [modes, setModes] = useState<ExtractionMode[]>([]);
  const [modeId, setModeId] = useState('material_extraction');
  const [files, setFiles] = useState<ParsedFile[]>([]);
  const [status, setStatus] = useState('Ready');
  const [propertiesText, setPropertiesText] = useState('BET surface area\ntotal pore volume\nspecific capacitance');

  function requestedProperties() {
    return propertiesText
      .split(/[\n,，]/)
      .map((property) => property.trim())
      .filter(Boolean);
  }

  async function loadModes() {
    const data = await fetch(`${import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000'}/workflows`).then((r) => r.json());
    setModes(data);
    if (data.some((mode: ExtractionMode) => mode.id === 'material_extraction')) {
      setModeId('material_extraction');
    } else if (data[0]) {
      setModeId(data[0].id);
    }
  }

  async function selectFiles() {
    setStatus('Parsing PDFs locally...');
    try {
      const parsed = await selectAndParsePdfs();
      setFiles(parsed);
      setStatus(parsed.length ? `Parsed ${parsed.length} PDF(s).` : 'Ready');
    } catch (error) {
      setStatus(error instanceof Error ? error.message : String(error));
    }
  }

  async function submitJob() {
    setStatus('Submitting job...');
    const properties = requestedProperties();
    const config = modeId === 'material_extraction' ? { properties } : {};
    const result = await apiFetch<{ job_id: string }>('/jobs', token, {
      method: 'POST',
      body: JSON.stringify({ workflow_id: modeId, config, items: files.map((file) => ({ file_name: file.fileName, file_hash: file.fileHash, text: file.text })) }),
    });
    setStatus(`Queued job ${result.job_id}`);
  }

  const canSubmit = Boolean(token && files.length > 0 && (modeId !== 'material_extraction' || requestedProperties().length > 0));

  return (
    <main className="shell">
      <section className="toolbar">
        <div>
          <h1>Deep Dig</h1>
          <p>Extract structured materials data from local PDFs.</p>
        </div>
        <button onClick={loadModes} title="Refresh extraction modes"><RefreshCw size={18} /> Modes</button>
      </section>
      <section className="panel">
        <label>Bearer token</label>
        <textarea value={token} onChange={(event) => setToken(event.target.value)} placeholder="Supabase access token for development" />
        <label>Extraction mode</label>
        <select value={modeId} onChange={(event) => setModeId(event.target.value)}>
          {modes.length === 0 && <option value="material_extraction">Material Science Data Extraction</option>}
          {modes.map((mode) => <option key={mode.id} value={mode.id}>{mode.name}</option>)}
        </select>
        {modeId === 'material_extraction' && (
          <>
            <label>Properties to extract</label>
            <textarea
              className="properties"
              value={propertiesText}
              onChange={(event) => setPropertiesText(event.target.value)}
              placeholder="One property per line, or separate with commas"
            />
          </>
        )}
        <button className="drop" type="button" onClick={selectFiles}>
          <FileText size={24} />
          <span>Select PDFs</span>
        </button>
        <button disabled={!canSubmit} onClick={submitJob}><Play size={18} /> Start extraction</button>
      </section>
      <section className="panel">
        <strong>{status}</strong>
        <ul>{files.map((file) => <li key={file.fileHash}>{file.fileName} · {file.text.length.toLocaleString()} chars</li>)}</ul>
      </section>
    </main>
  );
}
