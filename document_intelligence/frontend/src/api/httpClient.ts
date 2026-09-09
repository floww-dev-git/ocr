import { ApiError, UNKNOWN_ERROR_CODE } from "./apiError";

const JSON_CONTENT_TYPE = "application/json";

type Query = Record<string, string | number | boolean | undefined>;

interface RequestOptions {
  method?: "GET" | "POST" | "PATCH" | "PUT" | "DELETE";
  body?: unknown;
  formData?: FormData;
  query?: Query;
  signal?: AbortSignal;
}

export function buildUrl(path: string, query?: Query): string {
  if (query === undefined) {
    return path;
  }
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(query)) {
    if (value !== undefined) {
      search.set(key, String(value));
    }
  }
  const rendered = search.toString();
  return rendered.length > 0 ? `${path}?${rendered}` : path;
}

export async function request<T>(
  path: string,
  options: RequestOptions = {},
): Promise<T> {
  const { method = "GET", body, formData, query, signal } = options;
  const response = await fetch(buildUrl(path, query), {
    method,
    signal,
    // FormData sets its own multipart boundary, so the header is left off there.
    headers: body === undefined ? undefined : { "Content-Type": JSON_CONTENT_TYPE },
    body: formData ?? (body === undefined ? undefined : JSON.stringify(body)),
  });

  if (!response.ok) {
    throw await buildApiError(response);
  }
  if (response.status === 204) {
    return undefined as T;
  }
  return (await response.json()) as T;
}

async function buildApiError(response: Response): Promise<ApiError> {
  const payload = await readJsonOrNull(response);
  const { errorCode, ...detail } = payload ?? {};
  return new ApiError({
    status: response.status,
    errorCode: typeof errorCode === "string" ? errorCode : UNKNOWN_ERROR_CODE,
    detail,
  });
}

async function readJsonOrNull(
  response: Response,
): Promise<Record<string, unknown> | null> {
  try {
    return (await response.json()) as Record<string, unknown>;
  } catch {
    // A proxy or crash can answer with something that is not JSON; the status
    // code is still worth reporting.
    return null;
  }
}
