import type { Application } from "@/api/contracts";

const APPLICANT_NAME_KEY = "applicantName";
const VILLAGE_KEY = "village";
const PROPOSED_USE_KEY = "proposedUse";

export interface ApplicationHeadline {
  applicationId: string;
  applicantName: string;
  place: string;
}

const UNNAMED_APPLICANT = "Applicant not named";

export function readApplicationHeadline(
  application: Application,
): ApplicationHeadline {
  const fields = application.fieldValues;
  return {
    applicationId: application.applicationId,
    applicantName: fields[APPLICANT_NAME_KEY] || UNNAMED_APPLICANT,
    place: [fields[PROPOSED_USE_KEY], fields[VILLAGE_KEY]]
      .filter((part) => Boolean(part))
      .join(", "),
  };
}

/** Matches on what an officer would actually type: the id, the name, the place. */
export function matchesApplicationSearch(
  application: Application,
  term: string,
): boolean {
  const needle = term.trim().toLowerCase();
  if (needle.length === 0) {
    return true;
  }
  const headline = readApplicationHeadline(application);
  return [headline.applicationId, headline.applicantName, headline.place].some(
    (haystack) => haystack.toLowerCase().includes(needle),
  );
}
