import { invoke } from '@tauri-apps/api/core';
import { open, save } from '@tauri-apps/plugin-dialog';

export type ParsedFile = {
  fileName: string;
  fileHash: string;
  text: string;
  textFormat: 'markdown';
  textLength: number;
};

export async function selectAndParsePdfs(): Promise<ParsedFile[]> {
  const selected = await open({
    multiple: true,
    filters: [{ name: 'PDF documents', extensions: ['pdf'] }],
  });
  const paths = Array.isArray(selected) ? selected : selected ? [selected] : [];
  return Promise.all(paths.map((path) => invoke<ParsedFile>('parse_pdf_to_markdown', { path })));
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
