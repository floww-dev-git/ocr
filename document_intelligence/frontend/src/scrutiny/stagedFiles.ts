const BYTES_PER_KILOBYTE = 1024;

export interface StagedFile {
  /** Stable across re-renders so removing one chip cannot shuffle the others. */
  id: string;
  file: File;
}

let nextStagedId = 0;

export function stageFiles(current: StagedFile[], files: File[]): StagedFile[] {
  return [
    ...current,
    ...files.map((file) => ({ id: `staged_${nextStagedId++}`, file })),
  ];
}

export function removeStaged(current: StagedFile[], id: string): StagedFile[] {
  return current.filter((staged) => staged.id !== id);
}

export function readFileFormat(filename: string): string {
  const at = filename.lastIndexOf(".");
  return at === -1 ? "" : filename.slice(at + 1).toUpperCase();
}

export function formatStagedSize(bytes: number): string {
  if (bytes < BYTES_PER_KILOBYTE) {
    return `${bytes} B`;
  }
  const kilobytes = bytes / BYTES_PER_KILOBYTE;
  if (kilobytes < BYTES_PER_KILOBYTE) {
    return `${Math.round(kilobytes)} KB`;
  }
  return `${(kilobytes / BYTES_PER_KILOBYTE).toFixed(1)} MB`;
}
