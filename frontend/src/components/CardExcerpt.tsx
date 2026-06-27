import { useLayoutEffect, useRef, useState, type ReactElement } from "react";

import {
  buildExcerptPreview,
  normalizeExcerptText,
} from "../lib/recommendationExcerpt";

interface CardExcerptProps {
  text: string;
}

/** Render a review excerpt that fills three lines before showing a preview marker. */
export function CardExcerpt({ text }: CardExcerptProps): ReactElement {
  const ref = useRef<HTMLParagraphElement>(null);
  const [preview, setPreview] = useState(() => normalizeExcerptText(text));

  useLayoutEffect(() => {
    const element = ref.current;
    if (element === null) {
      return;
    }

    const updatePreview = (): void => {
      const normalized = normalizeExcerptText(text);
      if (normalized.length === 0) {
        setPreview("");
        return;
      }

      const fits = (candidate: string): boolean => {
        element.textContent = candidate;
        return element.scrollHeight <= element.clientHeight + 1;
      };

      setPreview(buildExcerptPreview(normalized, fits));
    };

    updatePreview();
    const observer = new ResizeObserver(updatePreview);
    observer.observe(element);
    return () => observer.disconnect();
  }, [text]);

  return (
    <p className="excerpt" ref={ref}>
      {preview}
    </p>
  );
}
