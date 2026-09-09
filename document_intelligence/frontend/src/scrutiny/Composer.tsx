import { ArrowRight, Paperclip, X } from "lucide-react";
import { useRef, useState } from "react";

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import {
  formatStagedSize,
  readFileFormat,
  type StagedFile,
} from "./stagedFiles";

const ACCEPTED = ".pdf,.jpg,.jpeg,.png";

interface ComposerProps {
  staged: StagedFile[];
  onStage: (files: File[]) => void;
  onRemove: (id: string) => void;
  onVerify: () => void;
  busy: boolean;
  canVerify: boolean;
  verifyLabel: string;
}

/**
 * Pinned to the bottom of the workspace, as the prototype has it: the officer's
 * one place to put documents in and set the run going, always reachable however
 * far down the document list they have scrolled.
 *
 * Attaching stages a file, it does not upload. The verify press is what sends
 * them, so a wrong pick can be taken off the tray before it ever leaves the
 * machine — and before it costs a model call.
 */
export function Composer({
  staged,
  onStage,
  onRemove,
  onVerify,
  busy,
  canVerify,
  verifyLabel,
}: ComposerProps) {
  const fileInput = useRef<HTMLInputElement>(null);
  // The prototype's composer is a chat box. DI has no Q&A endpoint, so the text is
  // not sent anywhere — the arrow verifies the staged documents, DI's real action.
  // The field is kept because it is part of the prototype's shape the officer knows.
  const [message, setMessage] = useState("");

  return (
    <footer className="mx-auto flex w-full max-w-(--content-w) shrink-0 flex-col gap-2.5 px-4 pt-2 pb-4">
      <form
        onSubmit={(event) => {
          event.preventDefault();
          if (canVerify && !busy) {
            onVerify();
          }
        }}
        className={cn(
          "flex items-end gap-1.5 rounded-[var(--radius-l)] border border-line-strong bg-surface p-1.5 pl-2 shadow-(--shadow-float) transition-[box-shadow,border-color] duration-200",
          "focus-within:border-ai focus-within:shadow-[0_0_0_3px_color-mix(in_srgb,var(--ai-a)_10%,transparent),var(--shadow-float)]",
        )}
      >
        <input
          ref={fileInput}
          type="file"
          multiple
          hidden
          accept={ACCEPTED}
          // Distinct from the button that opens it: the button is what assistive
          // tech activates, this hidden input is the mechanism behind it.
          aria-label="Documents to attach"
          onChange={(event) => {
            onStage(Array.from(event.target.files ?? []));
            // Cleared so re-attaching the same file still fires a change.
            event.target.value = "";
          }}
        />
        <Button
          variant="ghost"
          size="icon"
          className="shrink-0"
          onClick={() => fileInput.current?.click()}
          disabled={busy}
          title="Attach documents"
          aria-label="Attach documents"
        >
          <Paperclip />
        </Button>

        <div className="flex min-w-0 flex-1 flex-col gap-1.5 py-1">
          {staged.length > 0 ? (
            <ul
              role="list"
              aria-label="Documents ready to verify"
              className="flex flex-wrap gap-1.5"
            >
              {staged.map((item) => (
                <li
                  key={item.id}
                  className="flex items-center gap-1.5 rounded-[var(--radius-s)] bg-surface-3 py-1 pr-1 pl-2 text-[12px]"
                >
                  <span className="max-w-52 truncate text-ink">{item.file.name}</span>
                  <span className="text-ink-3">
                    {readFileFormat(item.file.name)} ·{" "}
                    {formatStagedSize(item.file.size)}
                  </span>
                  <button
                    type="button"
                    onClick={() => onRemove(item.id)}
                    disabled={busy}
                    aria-label={`Remove ${item.file.name}`}
                    className="rounded-full p-0.5 text-ink-3 transition-colors hover:bg-surface hover:text-ink disabled:opacity-50"
                  >
                    <X className="size-3.5" aria-hidden="true" />
                  </button>
                </li>
              ))}
            </ul>
          ) : null}

          <textarea
            rows={1}
            value={message}
            onChange={(event) => setMessage(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Enter" && !event.shiftKey) {
                event.preventDefault();
                if (canVerify && !busy) {
                  onVerify();
                }
              }
            }}
            placeholder="Ask about the documents, or attach files"
            aria-label="Message"
            className="max-h-40 w-full resize-none bg-transparent px-1 py-[7px] text-[14px] leading-[1.45] text-ink outline-none placeholder:text-ink-3"
          />
        </div>

        {/* The prototype's dark send button: solid ink, arrow, dimmed (not
            recoloured) when there is nothing to send. */}
        <button
          type="submit"
          disabled={!canVerify || busy}
          title={verifyLabel}
          aria-label={verifyLabel}
          className="flex size-8 shrink-0 items-center justify-center rounded-[var(--radius-s)] bg-ink [color:var(--bg)] transition-[filter] hover:brightness-125 disabled:opacity-50"
        >
          <ArrowRight className="size-4" aria-hidden="true" />
        </button>
      </form>
    </footer>
  );
}
