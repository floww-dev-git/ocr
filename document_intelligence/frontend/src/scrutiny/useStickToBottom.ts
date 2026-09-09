import { useCallback, useEffect, useRef } from "react";

/** How far from the bottom still counts as "following along". */
const NEAR_BOTTOM_PX = 120;

/**
 * Keeps the newest entry in view while a run streams, but only if the officer was
 * already at the bottom. Scrolling up to re-read an earlier document is a
 * deliberate act, and yanking the view away from it would be the wrong call.
 */
export function useStickToBottom(dependency: unknown) {
  const scroller = useRef<HTMLElement | null>(null);
  const wasNearBottom = useRef(true);

  const onScroll = useCallback(() => {
    const element = scroller.current;
    if (element === null) {
      return;
    }
    wasNearBottom.current =
      element.scrollHeight - element.scrollTop - element.clientHeight <
      NEAR_BOTTOM_PX;
  }, []);

  useEffect(() => {
    const element = scroller.current;
    if (element === null || !wasNearBottom.current) {
      return;
    }
    element.scrollTop = element.scrollHeight;
  }, [dependency]);

  return { scroller, onScroll };
}
