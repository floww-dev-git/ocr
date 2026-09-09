import { useEffect, useState } from "react";

import type { Application } from "@/api/contracts";
import { scrutinyApi } from "@/api/scrutinyApi";

const LOAD_FAILED_MESSAGE = "The application list could not be loaded.";

export function useApplications() {
  const [applications, setApplications] = useState<Application[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    scrutinyApi
      .getApplications(controller.signal)
      .then(setApplications)
      .catch((error: unknown) => {
        if (!controller.signal.aborted) {
          setLoadError(LOAD_FAILED_MESSAGE);
          console.error(error);
        }
      })
      .finally(() => {
        if (!controller.signal.aborted) {
          setLoading(false);
        }
      });
    return () => controller.abort();
  }, []);

  return { applications, loading, loadError };
}
