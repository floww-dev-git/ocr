import { ApiError } from "@/api/apiError";

const GENERIC_REJECTION = "Those documents could not be attached.";

/**
 * The upload guard refuses with a reason and the filename that caused it. Naming
 * the file matters: an officer attaching six documents cannot act on "upload
 * failed".
 */
const MESSAGES_BY_CODE: Record<string, (filename: string) => string> = {
  unsupported_format: (filename) =>
    `${filename} is not a format this system can read. Attach a PDF, JPG or PNG.`,
  too_large: (filename) => `${filename} is larger than the upload limit.`,
  empty_file: (filename) => `${filename} is empty.`,
  THREAD_NOT_FOUND: () => "That scrutiny no longer exists. Open it again.",
  NO_FILES_ATTACHED: () => "No documents were attached.",
};

export function readUploadRejection(error: unknown): string {
  if (!(error instanceof ApiError)) {
    return GENERIC_REJECTION;
  }
  // The backend sends its own sentence for guard rejections; prefer it, since it
  // knows the actual limit that was breached.
  const supplied = error.detail.message;
  if (typeof supplied === "string" && supplied.length > 0) {
    return supplied;
  }
  const build = MESSAGES_BY_CODE[error.errorCode];
  if (build === undefined) {
    return GENERIC_REJECTION;
  }
  const filename =
    typeof error.detail.filename === "string" ? error.detail.filename : "That file";
  return build(filename);
}
