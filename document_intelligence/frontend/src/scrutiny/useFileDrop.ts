import { useCallback, useRef, useState } from "react";

/**
 * Tracks a drag across the whole workspace.
 *
 * dragenter and dragleave both fire as the pointer crosses child elements, so a
 * depth counter is what keeps the overlay from flickering off the moment the
 * cursor passes over a document card.
 */
export function useFileDrop(onFiles: (files: File[]) => void) {
  const [dragging, setDragging] = useState(false);
  const depth = useRef(0);

  const onDragEnter = useCallback((event: React.DragEvent) => {
    event.preventDefault();
    depth.current += 1;
    setDragging(true);
  }, []);

  const onDragOver = useCallback((event: React.DragEvent) => {
    // Without this the browser navigates to the file instead of dropping it.
    event.preventDefault();
  }, []);

  const onDragLeave = useCallback((event: React.DragEvent) => {
    event.preventDefault();
    depth.current = Math.max(0, depth.current - 1);
    if (depth.current === 0) {
      setDragging(false);
    }
  }, []);

  const onDrop = useCallback(
    (event: React.DragEvent) => {
      event.preventDefault();
      depth.current = 0;
      setDragging(false);
      const files = Array.from(event.dataTransfer.files);
      if (files.length > 0) {
        onFiles(files);
      }
    },
    [onFiles],
  );

  return {
    dragging,
    handlers: { onDragEnter, onDragOver, onDragLeave, onDrop },
  };
}
