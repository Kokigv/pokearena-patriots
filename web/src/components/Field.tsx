import type { ReactNode } from "react";

interface Props {
  label: string;
  error?: string;
  hint?: string;
  children: ReactNode;
}

export function Field({ label, error, hint, children }: Props) {
  return (
    <label className={`field${error ? " field--error" : ""}`}>
      <span className="field__label">{label}</span>
      {children}
      {error ? (
        <span className="field__error">{error}</span>
      ) : (
        hint && <span className="field__hint">{hint}</span>
      )}
    </label>
  );
}

export function ErrorBanner({ message }: { message: string | null }) {
  return message ? <div className="banner banner--error">{message}</div> : null;
}
