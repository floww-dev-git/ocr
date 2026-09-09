import { ClipboardCopy } from "lucide-react";
import { useCallback, useState } from "react";

import { Button } from "@/components/ui/button";

interface NoteEntryProps {
  text: string;
}

export function NoteEntryView({ text }: NoteEntryProps) {
  const [copied, setCopied] = useState(false);
  const [problem, setProblem] = useState<string | null>(null);

  const copy = useCallback(async () => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
    } catch {
      // Clipboard access can be refused; the note is on screen to copy by hand.
      setProblem("The note could not be copied. Select the text instead.");
    }
  }, [text]);

  return (
    <section
      aria-label="Scrutiny note"
      className="rounded-[var(--radius-l)] border border-line bg-surface p-3"
    >
      <div className="mb-2 flex items-center gap-2">
        <h2 className="mr-auto text-[13px] font-semibold text-ink">Scrutiny note</h2>
        <Button variant="ghost" size="sm" onClick={() => void copy()}>
          <ClipboardCopy />
          {copied ? "Copied" : "Copy"}
        </Button>
      </div>
      {problem ? (
        <p role="alert" className="mb-2 text-[13px] text-fail">
          {problem}
        </p>
      ) : null}
      <pre className="overflow-x-auto rounded-[var(--radius-m)] bg-surface-2 p-2.5 font-mono text-[12px] whitespace-pre-wrap text-ink">
        {text}
      </pre>
    </section>
  );
}
