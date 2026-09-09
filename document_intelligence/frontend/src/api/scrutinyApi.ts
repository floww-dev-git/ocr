import type {
  AadhaarSpecimenScenario,
  Application,
  CheckChange,
  CheckResolution,
  DocumentCatalog,
  DocumentChange,
  DocumentState,
  ScrutinyNote,
  ScrutinyThread,
} from "./contracts";
import { request } from "./httpClient";

const UPLOAD_FIELD_NAME = "files";

export const scrutinyApi = {
  getCatalog(signal?: AbortSignal): Promise<DocumentCatalog> {
    return request<DocumentCatalog>("/api/catalog", { signal });
  },

  async getApplications(signal?: AbortSignal): Promise<Application[]> {
    const { applications } = await request<{ applications: Application[] }>(
      "/api/applications",
      { signal },
    );
    return applications;
  },

  createThread(applicationId: string): Promise<ScrutinyThread> {
    return request<ScrutinyThread>("/api/threads", {
      method: "POST",
      body: { applicationId },
    });
  },

  getThread(threadId: string, signal?: AbortSignal): Promise<ScrutinyThread> {
    return request<ScrutinyThread>(`/api/threads/${threadId}`, { signal });
  },

  async listAadhaarSpecimens(
    signal?: AbortSignal,
  ): Promise<AadhaarSpecimenScenario[]> {
    const { scenarios } = await request<{ scenarios: AadhaarSpecimenScenario[] }>(
      "/api/demo/aadhaar-specimens",
      { signal },
    );
    return scenarios;
  },

  async fetchAadhaarSpecimen(filename: string): Promise<File> {
    // Fetched straight from the demo endpoint (same origin behind the Vite proxy)
    // and wrapped as a File so it rides the ordinary attach-and-verify flow.
    const response = await fetch(
      `/api/demo/aadhaar-specimens/${encodeURIComponent(filename)}`,
    );
    if (!response.ok) {
      throw new Error(`Could not load specimen ${filename}`);
    }
    const blob = await response.blob();
    return new File([blob], filename, { type: "application/pdf" });
  },

  async addDocuments(threadId: string, files: File[]): Promise<DocumentState[]> {
    const formData = new FormData();
    for (const file of files) {
      formData.append(UPLOAD_FIELD_NAME, file);
    }
    const { documents } = await request<{ documents: DocumentState[] }>(
      `/api/threads/${threadId}/documents`,
      { method: "POST", formData },
    );
    return documents;
  },

  updateField(args: {
    threadId: string;
    documentId: string;
    fieldKey: string;
    value: string;
  }): Promise<DocumentChange> {
    const { threadId, documentId, fieldKey, value } = args;
    return request<DocumentChange>(
      `/api/threads/${threadId}/documents/${documentId}/fields/${encodeURIComponent(fieldKey)}`,
      { method: "PATCH", body: { value } },
    );
  },

  confirmFields(args: {
    threadId: string;
    documentId: string;
  }): Promise<DocumentChange> {
    return request<DocumentChange>(
      `/api/threads/${args.threadId}/documents/${args.documentId}/confirm`,
      { method: "POST" },
    );
  },

  resolveCheck(args: {
    threadId: string;
    checkId: string;
    action: CheckResolution;
  }): Promise<CheckChange> {
    return request<CheckChange>(
      `/api/threads/${args.threadId}/checks/${encodeURIComponent(args.checkId)}/resolve`,
      { method: "POST", body: { action: args.action } },
    );
  },

  retryVerification(args: {
    threadId: string;
    documentId: string;
  }): Promise<CheckChange> {
    return request<CheckChange>(
      `/api/threads/${args.threadId}/documents/${args.documentId}/retry-verification`,
      { method: "POST" },
    );
  },

  updateServiceOverrides(args: {
    threadId: string;
    serviceOverrides: Record<string, string>;
  }): Promise<ScrutinyThread> {
    return request<ScrutinyThread>(`/api/threads/${args.threadId}/service-overrides`, {
      method: "PUT",
      body: { serviceOverrides: args.serviceOverrides },
    });
  },

  getNote(threadId: string, signal?: AbortSignal): Promise<ScrutinyNote> {
    return request<ScrutinyNote>(`/api/threads/${threadId}/note`, { signal });
  },

  analyzeUrl(threadId: string): string {
    return `/api/threads/${threadId}/analyze`;
  },
};
