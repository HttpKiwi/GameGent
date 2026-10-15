import { useEffect, useRef } from 'react';
import type { PickableProcess } from '../api/client';
import { TextField, SelectField } from './ui';

interface CreateFromGameDialogProps {
  open: boolean;
  picked: PickableProcess | null;
  profileName: string;
  target: string;
  assignOptions: { value: string; label: string }[];
  busy?: boolean;
  onClose: () => void;
  onProfileNameChange: (value: string) => void;
  onTargetChange: (value: string) => void;
  onConfirm: () => void;
}

export function CreateFromGameDialog({
  open,
  picked,
  profileName,
  target,
  assignOptions,
  busy,
  onClose,
  onProfileNameChange,
  onTargetChange,
  onConfirm,
}: CreateFromGameDialogProps) {
  const dialogRef = useRef<HTMLDialogElement>(null);

  useEffect(() => {
    const dialog = dialogRef.current;
    if (!dialog) return;
    if (open) {
      if (!dialog.open) dialog.showModal();
    } else if (dialog.open) {
      dialog.close();
    }
  }, [open]);

  if (!picked) {
    return <dialog ref={dialogRef} className="process-picker" onClose={onClose} />;
  }

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
          <h3>Link game to a profile</h3>
          <button type="button" className="form-btn-secondary" onClick={onClose}>
            Cancel
          </button>
        </header>
        <p className="process-picker__hint">
          Selected <strong>{picked.label || picked.match}</strong>
          {picked.steam_appid ? ` (Steam ${picked.steam_appid})` : ''}.
          {picked.kind === 'steam' || picked.steam_appid
            ? ' This will bind the Steam AppId so helper processes still match.'
            : ' Create a new profile or add it to an existing one.'}{' '}
          e.g. one Souls profile for DS1, DS2, and DS3.
        </p>
        <SelectField
          label="Destination"
          value={target}
          options={assignOptions}
          onChange={onTargetChange}
        />
        {target === 'new' && (
          <TextField
            label="New profile name"
            value={profileName}
            onChange={onProfileNameChange}
            placeholder="e.g. Souls"
          />
        )}
        <div className="button-row" style={{ marginTop: 12 }}>
          <button
            type="button"
            className="form-btn"
            onClick={onConfirm}
            disabled={busy}
          >
            {target === 'new' ? 'Create profile & link game' : `Add to “${target}”`}
          </button>
        </div>
      </div>
    </dialog>
  );
}
