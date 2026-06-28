import { useLayoutEffect, useRef, useState, type ReactElement } from "react";

import { createExcerptFitChecker } from "../lib/excerptFitChecker";
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

    const checker = createExcerptFitChecker(element);
    let frameId = 0;

    const updatePreview = (): void => {
      const normalized = normalizeExcerptText(text);
      if (normalized.length === 0) {
        setPreview("");
        return;
      }

      if (element.clientWidth <= 0) {
        return;
      }

      setPreview(buildExcerptPreview(normalized, checker.fits));
    };

    const scheduleUpdate = (): void => {
      cancelAnimationFrame(frameId);
      frameId = requestAnimationFrame(updatePreview);
    };

    scheduleUpdate();
    const observer = new ResizeObserver(scheduleUpdate);
    observer.observe(element);

    return () => {
      cancelAnimationFrame(frameId);
      observer.disconnect();
      checker.destroy();
    };
  }, [text]);

  return (
    <p className="excerpt" ref={ref}>
      {preview}
    </p>
  );
}
