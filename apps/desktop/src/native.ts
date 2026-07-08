import { invoke } from '@tauri-apps/api/core';
import { open, save } from '@tauri-apps/plugin-dialog';

export type ParsedFile = {
  fileName: string;
  fileHash: string;
  text: string;
  textFormat: 'markdown';
  textLength: number;
  reused: boolean;
  storagePath?: string;
};

export type SelectedPdf = {
  path: string;
  fileName: string;
};

export async function selectPdfFiles(): Promise<SelectedPdf[]> {
  const selected = await open({
    multiple: true,
    filters: [{ name: 'PDF documents', extensions: ['pdf'] }],
  });
  const paths = Array.isArray(selected) ? selected : selected ? [selected] : [];
  return paths.map((path) => ({
    path,
    fileName: path.split(/[\\/]/).pop() ?? path,
  }));
}

export async function chooseParsedOutputDir(): Promise<string | null> {
  const selected = await open({
    directory: true,
    multiple: false,
    title: 'Choose parsed text output folder',
  });
  return typeof selected === 'string' ? selected : null;
}

export async function parsePdfToMarkdown(path: string, outputDir: string): Promise<ParsedFile> {
  return invoke<ParsedFile>('parse_pdf_to_markdown', { path, outputDir });
}

export async function pickExcelSavePath(defaultName: string): Promise<string | null> {
  return save({
    defaultPath: defaultName,
    filters: [{ name: 'Excel workbook', extensions: ['xlsx'] }],
  });
}

export async function saveBytesToPath(path: string, bytes: Uint8Array): Promise<void> {
  await invoke('write_binary_file', { path, bytes: Array.from(bytes) });
}
