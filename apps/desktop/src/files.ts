import { apiUpload } from './api';
import type { ParsedFile, SelectedPdf } from './domain';

export function selectPdfFiles(): Promise<SelectedPdf[]> {
  return new Promise((resolve) => {
    let settled = false;
    const finish = (files: SelectedPdf[]) => {
      if (settled) return;
      settled = true;
      resolve(files);
    };
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = 'application/pdf';
    input.multiple = true;
    input.onchange = () => {
      finish(
        Array.from(input.files ?? []).map((file) => ({
          file,
          fileName: file.name,
        })),
      );
    };
    input.addEventListener('cancel', () => finish([]));
    input.click();
  });
}

export async function parseFiles(token: string, files: SelectedPdf[]): Promise<ParsedFile[]> {
  return apiUpload<ParsedFile[]>('/files/parse', token, files.map((selected) => selected.file));
}
