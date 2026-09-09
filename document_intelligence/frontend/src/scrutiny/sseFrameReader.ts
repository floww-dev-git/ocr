const FRAME_SEPARATOR = "\n\n";
const COMMENT_PREFIX = ":";
const EVENT_FIELD = "event";
const DATA_FIELD = "data";

export interface SseFrame {
  event: string;
  data: string;
}

/**
 * Turns a byte stream arriving in arbitrary chunks into whole SSE frames.
 *
 * A chunk boundary can fall anywhere, including inside a JSON payload, so the
 * tail of the buffer is held back until its terminating blank line arrives.
 * Parsing bytes the network happened to deliver together would silently drop
 * whichever document was mid-frame.
 */
export class SseFrameReader {
  private buffer = "";

  /** Frames completed by this chunk. Anything partial is kept for the next one. */
  read(chunk: string): SseFrame[] {
    this.buffer += chunk;
    // A proxy may rewrite the stream to CRLF, which would make the frame
    // separator "\r\n\r\n" and never match. Normalising here rather than at the
    // line level is what keeps the separator search correct. A lone trailing
    // "\r" is left alone: it may be the first half of a pair the next chunk
    // completes, and on its own it cannot terminate a frame.
    this.buffer = this.buffer.replace(/\r\n/g, "\n");
    const frames: SseFrame[] = [];
    let separatorAt = this.buffer.indexOf(FRAME_SEPARATOR);
    while (separatorAt !== -1) {
      const block = this.buffer.slice(0, separatorAt);
      this.buffer = this.buffer.slice(separatorAt + FRAME_SEPARATOR.length);
      const frame = parseFrameBlock(block);
      if (frame !== null) {
        frames.push(frame);
      }
      separatorAt = this.buffer.indexOf(FRAME_SEPARATOR);
    }
    return frames;
  }

  /**
   * A final frame the server did not terminate with a blank line. Called once
   * the stream closes, so a last frame is not lost to a missing newline.
   */
  flush(): SseFrame[] {
    const remaining = this.buffer;
    this.buffer = "";
    const frame = parseFrameBlock(remaining);
    return frame === null ? [] : [frame];
  }
}

function parseFrameBlock(block: string): SseFrame | null {
  let event = "";
  const dataLines: string[] = [];

  for (const rawLine of block.split("\n")) {
    const line = rawLine.replace(/\r$/, "");
    if (line.length === 0 || line.startsWith(COMMENT_PREFIX)) {
      continue;
    }
    const { field, value } = splitField(line);
    if (field === EVENT_FIELD) {
      event = value;
    } else if (field === DATA_FIELD) {
      dataLines.push(value);
    }
  }

  if (event.length === 0 && dataLines.length === 0) {
    return null;
  }
  // Multiple data lines join with newlines, per the SSE spec.
  return { event, data: dataLines.join("\n") };
}

function splitField(line: string): { field: string; value: string } {
  const colonAt = line.indexOf(":");
  if (colonAt === -1) {
    return { field: line, value: "" };
  }
  const value = line.slice(colonAt + 1);
  return {
    field: line.slice(0, colonAt),
    // A single leading space after the colon is separator, not content.
    value: value.startsWith(" ") ? value.slice(1) : value,
  };
}
