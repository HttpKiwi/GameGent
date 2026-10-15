import { useResetConfig } from '../hooks/useApi';

/** Restores the official factory defaults for the given config sections. */
export function ResetButton({ sections, what }: { sections: string[]; what: string }) {
  const reset = useResetConfig();

  const onClick = () => {
    if (window.confirm(`Reset ${what} to the factory defaults? This also updates the active profile.`)) {
      reset.mutate(sections);
    }
  };

  return (
    <button className="reset-btn" onClick={onClick} disabled={reset.isPending}>
      {reset.isPending ? 'Resetting…' : `Reset ${what}`}
    </button>
  );
}
