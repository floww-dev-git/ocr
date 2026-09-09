const MS_PER_MINUTE = 60_000;
const MINUTES_PER_HOUR = 60;
const HOURS_PER_DAY = 24;

/**
 * How long ago something happened, in the prototype's words: "just now", then
 * minutes, then hours, then days. Ported verbatim from index.html's `relTime` so
 * the rail reads the same.
 */
export function readRelativeTime(timestamp: number, now: number = Date.now()): string {
  const minutes = Math.round((now - timestamp) / MS_PER_MINUTE);
  if (minutes < 1) {
    return "just now";
  }
  if (minutes < MINUTES_PER_HOUR) {
    return `${minutes} min ago`;
  }
  const hours = Math.round(minutes / MINUTES_PER_HOUR);
  if (hours < HOURS_PER_DAY) {
    return `${hours} h ago`;
  }
  return `${Math.round(hours / HOURS_PER_DAY)} d ago`;
}
