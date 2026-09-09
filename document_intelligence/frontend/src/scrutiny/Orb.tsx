import { cn } from "@/lib/utils";

interface OrbProps {
  /** Diameter in px. The prototype uses 22 (sm), 28 (default) and 72 (greeting). */
  size?: number;
  /** A working orb spins fast; otherwise it drifts slowly (or holds still). */
  working?: boolean;
  className?: string;
}

/**
 * The AI orb, ported from the prototype's `ORB()` helper. All of its look lives in
 * index.css under `.orb`; this only assembles the three masked layers and picks
 * the animation. Sized by font-size because the CSS is written in `em`.
 *
 * A resting orb at 48px or larger drifts, matching the prototype's rule that the
 * large greeting orb is never completely static.
 */
export function Orb({ size = 28, working = false, className }: OrbProps) {
  const animate = working || size >= 48;
  return (
    <span
      aria-hidden="true"
      style={{ fontSize: `${size}px` }}
      className={cn("orb", working ? "working" : animate ? "drift" : "", className)}
    >
      <i className="orb-glow" />
      <i className="orb-band">
        <b />
      </i>
      <i className="orb-hot">
        <b />
      </i>
    </span>
  );
}
