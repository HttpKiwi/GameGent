import { useMemo, useRef, useEffect, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { fetchRunningProcesses, type PickableProcess } from '../api/client';

interface ProcessPickerProps {
  open: boolean;
  onClose: () => void;
  onPick: (process: PickableProcess) => void;
}

export function ProcessPicker({ open, onClose, onPick }: ProcessPickerProps) {
  const [filter, setFilter] = useState('');
  const dialogRef = useRef<HTMLDialogElement>(null);

  const query = useQuery({
    queryKey: ['running-processes'],
    queryFn: fetchRunningProcesses,
    enabled: open,
    staleTime: 0,
  });

  useEffect(() => {
    const dialog = dialogRef.current;
    if (!dialog) return;
    if (open) {
      if (!dialog.open) dialog.showModal();
    } else if (dialog.open) {
      dialog.close();
    }
  }, [open]);

  const { steamGames, plainProcesses } = useMemo(() => {
    const processes = query.data?.processes ?? [];
    const q = filter.trim().toLowerCase();
    const filtered = !q
      ? processes
      : processes.filter(
          (p) =>
            p.label.toLowerCase().includes(q) ||
            p.match.toLowerCase().includes(q) ||
            p.comm.toLowerCase().includes(q) ||
            p.cmdline.toLowerCase().includes(q) ||
            (p.steam_appid ?? '').includes(q)
        );
    return {
      steamGames: filtered.filter((p) => p.kind === 'steam' || (!p.match && p.steam_appid)),
      plainProcesses: filtered.filter((p) => p.kind !== 'steam' && p.match),
    };
  }, [query.data?.processes, filter]);

  const renderItem = (p: PickableProcess) => (
    <li key={`${p.kind ?? 'p'}-${p.pid}-${p.match}-${p.steam_appid ?? ''}`}>
      <button
        type="button"
        className="process-picker__item"
        onClick={() => {
          onPick(p);
          onClose();
        }}
      >
        <span className="process-picker__match">
          {p.kind === 'steam' ? p.label : p.match || p.label}
        </span>
        <span className="process-picker__meta">
          {p.kind === 'steam'
            ? `Steam ${p.steam_appid}`
            : `pid ${p.pid}${p.steam_appid ? ` · steam ${p.steam_appid}` : ''}`}
        </span>
        <span className="process-picker__cmdline" title={p.cmdline}>
          {p.kind === 'steam'
            ? 'Binds by Steam AppId (best for Proton / Easy Anti-Cheat)'
            : p.cmdline || p.comm}
        </span>
      </button>
    </li>
  );

  return (
    <dialog
      ref={dialogRef}
      className="process-picker"
      onClose={onClose}
      onCancel={onClose}
      onClick={(e) => {
        if (e.target === dialogRef.current) onClose();
      }}
    >
      <div className="process-picker__panel">
        <header className="process-picker__header">
          <h3>Pick a running game</h3>
          <button type="button" className="form-btn-secondary" onClick={onClose}>
            Close
          </button>
        </header>
        <p className="process-picker__hint">
          Prefer the Steam games list when you see it — titles like Elden Ring
          share one AppId across many helper processes. Process names are a
          fallback for non-Steam games.
        </p>
        <input
          className="process-picker__filter"
          type="search"
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
          placeholder="Filter by name or Steam id…"
          autoFocus
        />
        {query.isFetching && <p className="profiles-hint">Scanning processes…</p>}
        {query.isError && (
          <p className="profiles-feedback profiles-feedback--error">
            {query.error instanceof Error ? query.error.message : 'Failed to list processes'}
          </p>
        )}
        {!query.isFetching && !query.isError && steamGames.length === 0 && plainProcesses.length === 0 && (
          <p className="mappings-empty">No matching processes.</p>
        )}
        {steamGames.length > 0 && (
          <>
            <h4 className="process-picker__section">Steam games</h4>
            <ul className="process-picker__list">{steamGames.map(renderItem)}</ul>
          </>
        )}
        {plainProcesses.length > 0 && (
          <>
            <h4 className="process-picker__section">Processes</h4>
            <ul className="process-picker__list">{plainProcesses.map(renderItem)}</ul>
          </>
        )}
      </div>
    </dialog>
  );
}
