/**
 * The backend answers a refusal with a machine-readable `errorCode` plus the
 * context that made it refuse. Keeping that intact means the UI can say what
 * actually happened instead of "something went wrong".
 */
export class ApiError extends Error {
  readonly status: number;
  readonly errorCode: string;
  readonly detail: Record<string, unknown>;

  constructor(args: {
    status: number;
    errorCode: string;
    detail?: Record<string, unknown>;
  }) {
    super(args.errorCode);
    this.name = "ApiError";
    this.status = args.status;
    this.errorCode = args.errorCode;
    this.detail = args.detail ?? {};
  }

  get isNotFound(): boolean {
    return this.status === 404;
  }

  /** The document is mid-analysis; the officer should wait rather than retry. */
  get isDocumentBusy(): boolean {
    return this.errorCode === "DOCUMENT_BUSY";
  }
}

export const UNKNOWN_ERROR_CODE = "UNKNOWN_ERROR";
