interface DropOverlayProps {
  visible: boolean;
}

/**
 * Covers the whole workspace while a drag is in flight, as the prototype does,
 * so the officer can let go anywhere rather than hunting for a small target.
 */
export function DropOverlay({ visible }: DropOverlayProps) {
  if (!visible) {
    return null;
  }
  return (
    <div
      aria-hidden="true"
      className="absolute inset-0 z-30 flex items-center justify-center bg-ai/8"
    >
      <div className="absolute inset-3 rounded-[var(--radius-l)] border-2 border-dashed border-ai" />
      <p className="rounded-[var(--radius-m)] bg-surface px-5 py-3.5 font-medium text-ink shadow-(--shadow-float)">
        Drop documents to add them to this scrutiny
      </p>
    </div>
  );
}
