import { useState } from 'react';
import { useConfigStore } from '../stores/configStore';
import {
  useProfiles,
  useSaveProfile,
  useActivateProfile,
  useDeleteProfile,
  useApplyConfig,
} from '../hooks/useApi';
import { TextField, CheckboxField, SettingCard } from '../components/ui';

function formatUpdated(iso: string | null): string {
  if (!iso) return '';
  try {
    return new Date(iso).toLocaleString();
  } catch {
    return iso;
  }
}

export function ProfilesTab() {
  const config = useConfigStore((s) => s.config);
  const isDirty = useConfigStore((s) => s.isDirty);
  const { data, isPending, isError, error } = useProfiles();
  const saveProfile = useSaveProfile();
  const activateProfile = useActivateProfile();
  const deleteProfile = useDeleteProfile();
  const applyConfig = useApplyConfig();

  const [newName, setNewName] = useState('');
  const [applyOnActivate, setApplyOnActivate] = useState(true);
  const [message, setMessage] = useState<string | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const profiles = data?.profiles ?? [];
  const active = data?.active ?? null;
  const busy =
    saveProfile.isPending ||
    activateProfile.isPending ||
    deleteProfile.isPending ||
    applyConfig.isPending;

  const clearFeedback = () => {
    setMessage(null);
    setErrorMsg(null);
  };

  const handleSaveNew = async () => {
    clearFeedback();
    const name = newName.trim();
    if (!name) {
      setErrorMsg('Enter a profile name');
      return;
    }
    try {
      await saveProfile.mutateAsync({ name, config });
      setNewName('');
      setMessage(`Saved profile “${name}”`);
    } catch (e) {
      setErrorMsg(e instanceof Error ? e.message : 'Failed to save profile');
    }
  };

  const handleOverwrite = async (name: string) => {
    clearFeedback();
    try {
      await saveProfile.mutateAsync({ name, config });
      setMessage(`Updated profile “${name}”`);
    } catch (e) {
      setErrorMsg(e instanceof Error ? e.message : 'Failed to update profile');
    }
  };

  const handleActivate = async (name: string) => {
    clearFeedback();
    try {
      const result = await activateProfile.mutateAsync({
        name,
        apply: applyOnActivate,
      });
      const appliedNote = applyOnActivate
        ? ' and applied to controller'
        : ' (config only)';
      setMessage(`Loaded “${result.name}”${appliedNote}`);
    } catch (e) {
      setErrorMsg(e instanceof Error ? e.message : 'Failed to activate profile');
    }
  };

  const handleDelete = async (name: string) => {
    clearFeedback();
    if (!window.confirm(`Delete profile “${name}”?`)) return;
    try {
      await deleteProfile.mutateAsync(name);
      setMessage(`Deleted “${name}”`);
    } catch (e) {
      setErrorMsg(e instanceof Error ? e.message : 'Failed to delete profile');
    }
  };

  const handleApplyCurrent = async () => {
    clearFeedback();
    try {
      const result = await applyConfig.mutateAsync(config);
      const failed = Object.entries(result.applied).filter(([, v]) => v !== 'ok' && v !== 'skipped');
      if (failed.length) {
        setMessage(`Applied with warnings: ${failed.map(([k, v]) => `${k}=${v}`).join('; ')}`);
      } else {
        setMessage('Pushed working config to controller');
      }
    } catch (e) {
      setErrorMsg(e instanceof Error ? e.message : 'Failed to apply config');
    }
  };

  return (
    <div>
      <h2>Profiles</h2>
      <p className="profiles-intro">
        Software profiles store your full GameGent config locally
        (~/.config/gamegent/profiles). Activate one to load it, and optionally
        push it to the controller.
      </p>

      {(message || errorMsg) && (
        <p className={`profiles-feedback ${errorMsg ? 'profiles-feedback--error' : ''}`}>
          {errorMsg ?? message}
        </p>
      )}

      <div className="setting-grid">
        <SettingCard title="Save current" span={2}>
          <TextField
            label="New profile name"
            value={newName}
            onChange={setNewName}
            placeholder="e.g. FPS, Racing, Default"
          />
          <div className="button-row">
            <button
              type="button"
              className="form-btn"
              onClick={handleSaveNew}
              disabled={busy || !newName.trim()}
            >
              {saveProfile.isPending ? 'Saving…' : 'Save as profile'}
            </button>
            <button
              type="button"
              className="form-btn-secondary"
              onClick={handleApplyCurrent}
              disabled={busy}
            >
              Apply to controller
            </button>
          </div>
          {isDirty && (
            <p className="profiles-hint">Unsaved edits in the UI will be included when you save a profile.</p>
          )}
          {active && (
            <p className="profiles-hint">
              Active profile: <strong>{active}</strong>
            </p>
          )}
        </SettingCard>

        <SettingCard title="Saved profiles" span={2}>
          <CheckboxField
            label="Apply to controller when activating"
            checked={applyOnActivate}
            onChange={setApplyOnActivate}
          />

          {isPending && <p className="profiles-hint">Loading profiles…</p>}
          {isError && (
            <p className="profiles-feedback profiles-feedback--error">
              {error instanceof Error ? error.message : 'Failed to load profiles'}
            </p>
          )}
          {!isPending && profiles.length === 0 && (
            <p className="mappings-empty">No profiles yet. Save your current config above.</p>
          )}

          <div className="profiles-list">
            {profiles.map((p) => (
              <div
                key={p.name}
                className={`profile-row ${p.active ? 'profile-row--active' : ''}`}
              >
                <div className="profile-row__meta">
                  <span className="profile-row__name">{p.name}</span>
                  {p.active && <span className="profile-row__badge">Active</span>}
                  {p.updated_at && (
                    <span className="profile-row__updated">{formatUpdated(p.updated_at)}</span>
                  )}
                </div>
                <div className="profile-row__actions">
                  <button
                    type="button"
                    className="form-btn"
                    onClick={() => handleActivate(p.name)}
                    disabled={busy}
                  >
                    Activate
                  </button>
                  <button
                    type="button"
                    className="form-btn-secondary"
                    onClick={() => handleOverwrite(p.name)}
                    disabled={busy}
                  >
                    Overwrite
                  </button>
                  <button
                    type="button"
                    className="form-btn form-btn-danger"
                    onClick={() => handleDelete(p.name)}
                    disabled={busy}
                  >
                    Delete
                  </button>
                </div>
              </div>
            ))}
          </div>
        </SettingCard>
      </div>
    </div>
  );
}
