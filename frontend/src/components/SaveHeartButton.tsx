import type { ReactElement } from "react";

interface SaveHeartButtonProps {
  className?: string;
  disabled?: boolean;
  isSaved: boolean;
  isToggling?: boolean;
  onToggle: () => void;
}

/** Bookmark button used on recommendation cards. */
export function SaveHeartButton({
  className = "card-save-heart",
  disabled = false,
  isSaved,
  isToggling = false,
  onToggle,
}: SaveHeartButtonProps): ReactElement {
  const isDisabled = disabled || isToggling;
  const label = isSaved ? "Vormerkung entfernen" : "Vormerken";
  const title = isSaved
    ? "Aus deiner Merkliste entfernen"
    : "Für später vormerken";

  return (
    <button
      aria-busy={isToggling}
      aria-label={label}
      aria-pressed={isSaved}
      className={`${className}${isSaved ? " card-save-heart-saved" : ""}`}
      disabled={isDisabled}
      onClick={(event) => {
        event.preventDefault();
        event.stopPropagation();
        onToggle();
      }}
      title={title}
      type="button"
    >
      <svg aria-hidden="true" className="card-save-heart-icon" viewBox="0 0 24 24">
        <path d="M12 20.25s-6.9-4.35-9.33-7.58C.86 10.03 1.1 6.88 3.45 5.1 5.8 3.32 8.9 4.04 12 6.7c3.1-2.66 6.2-3.38 8.55-1.6 2.35 1.78 2.59 4.93.78 7.57C18.9 15.9 12 20.25 12 20.25z" />
      </svg>
    </button>
  );
}
