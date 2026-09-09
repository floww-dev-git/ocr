import { describe, expect, it } from "vitest";

import {
  CHECK_STATUSES,
  DOCUMENT_STAGES,
  DOCUMENT_STATUSES,
  THREAD_STATUSES,
} from "@/api/contracts";
import {
  readCheckStatus,
  readDocumentStatus,
  readStageLabel,
  readThreadStatus,
} from "./statusVocabulary";

describe("the status vocabulary", () => {
  it("has words for every check status the backend can send", () => {
    for (const status of CHECK_STATUSES) {
      expect(readCheckStatus(status).label.length).toBeGreaterThan(0);
    }
  });

  it("has words for every document status the backend can send", () => {
    for (const status of DOCUMENT_STATUSES) {
      expect(readDocumentStatus(status).label.length).toBeGreaterThan(0);
    }
  });

  it("has words for every thread status the backend can send", () => {
    for (const status of THREAD_STATUSES) {
      expect(readThreadStatus(status).label.length).toBeGreaterThan(0);
    }
  });

  it("has words for every stage a document passes through", () => {
    for (const stage of DOCUMENT_STAGES) {
      expect(readStageLabel(stage).length).toBeGreaterThan(0);
    }
  });

  it("gives each check status its own wording, so two verdicts never read alike", () => {
    const labels = CHECK_STATUSES.map((status) => readCheckStatus(status).label);

    expect(new Set(labels).size).toBe(labels.length);
  });

  it("never dresses a failure as anything softer", () => {
    expect(readCheckStatus("fail").tone).toBe("fail");
    expect(readDocumentStatus("failed").tone).toBe("fail");
  });

  it("keeps 'could not check' distinct from 'not checked yet'", () => {
    // An unreachable department is not the same as work still queued, and an
    // officer must be able to tell which one they are looking at.
    expect(readCheckStatus("unavailable").label).not.toBe(
      readCheckStatus("pending").label,
    );
  });
});
