import { useState } from 'react';
import { useConfigStore } from '../stores/configStore';
import {
  useProfiles,
  useSaveProfile,
  useActivateProfile,
  useDeleteProfile,
  useGameRules,
  useGameRulesStatus,
  useSaveGameRules,
} from '../hooks/useApi';
import type { GameRules, PickableProcess } from '../api/client';
import { TextField, CheckboxField, SelectField, SettingCard } from '../components/ui';
import { ProcessPicker } from '../components/ProcessPicker';
import { CreateFromGameDialog } from '../components/CreateFromGameDialog';

type ProfileGames = { process: string[]; steam_appid: string[] };

type PickerMode =
  | { kind: 'add'; profile: string }
  | { kind: 'create' };

function formatUpdated(iso: string | null): string {
  if (!iso) return '';
  try {
    return new Date(iso).toLocaleString();
  } catch {
    return iso;
  }
}

function suggestProfileName(match: string, label?: string): string {
  const source = (label && label.trim()) || match;
  const base = source.replace(/\.exe$/i, '').replace(/[_-]+/g, ' ').trim();
  return base || match || 'Game';
}

function gamesForProfile(
  rules: GameRules | undefined,
  profileName: string,
  overrides: Record<string, ProfileGames>
): ProfileGames {
  if (overrides[profileName]) return overrides[profileName];
  const rule = rules?.rules.find((r) => r.profile === profileName);
  return {
    process: [...(rule?.match.process ?? [])],
    steam_appid: [...(rule?.match.steam_appid ?? [])],
  };
}

function addGameTo(
  games: ProfileGames,
  picked: PickableProcess
): ProfileGames {
  // Steam/Proton titles (Elden Ring, etc.): appid is the stable identity.
  // Prefer it over flaky helper exe names when present.
  if (picked.steam_appid || picked.kind === 'steam') {
    const steam_appid =
      picked.steam_appid && !games.steam_appid.includes(picked.steam_appid)
        ? [...games.steam_appid, picked.steam_appid]
        : games.steam_appid;
    return { process: games.process, steam_appid };
  }
  const process =
    picked.match && !games.process.includes(picked.match)
      ? [...games.process, picked.match]
      : games.process;
  return { process, steam_appid: games.steam_appid };
}

export function ProfilesTab() {
  const config = useConfigStore((s) => s.config);
  const isDirty = useConfigStore((s) => s.isDirty);
  const { data, isPending, isError, error } = useProfiles();
  const saveProfile = useSaveProfile();
  const activateProfile = useActivateProfile();
  const deleteProfile = useDeleteProfile();
  const { data: gameRules, isPending: rulesPending } = useGameRules();
  const { data: gameStatus } = useGameRulesStatus();
  const saveGameRules = useSaveGameRules();

  const [message, setMessage] = useState<string | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [manualName, setManualName] = useState('');

  const [enabledOverride, setEnabledOverride] = useState<boolean | null>(null);
  const [defaultOverride, setDefaultOverride] = useState<string | null>(null);
  const [gamesOverrides, setGamesOverrides] = useState<Record<string, ProfileGames>>({});

  const [pickerMode, setPickerMode] = useState<PickerMode | null>(null);
  const [createDraft, setCreateDraft] = useState<{
    picked: PickableProcess;
    profileName: string;
    target: 'new' | string; // 'new' or existing profile name
  } | null>(null);

  const profiles = data?.profiles ?? [];
  const active = data?.active ?? null;
  const busy =
    saveProfile.isPending ||
    activateProfile.isPending ||
    deleteProfile.isPending ||
    saveGameRules.isPending;

  const autoEnabled = enabledOverride ?? !!gameRules?.enabled;
  const defaultProfile = defaultOverride ?? (gameRules?.default_profile ?? '');

  const clearFeedback = () => {
    setMessage(null);
    setErrorMsg(null);
  };

  const getGames = (profileName: string) =>
    gamesForProfile(gameRules, profileName, gamesOverrides);

  const buildRulesPayload = (
    overrides: Record<string, ProfileGames> = gamesOverrides,
    enabled = autoEnabled,
    defaultProf = defaultProfile
  ): GameRules => {
    const names = new Set([
      ...profiles.map((p) => p.name),
      ...Object.keys(overrides),
      ...(gameRules?.rules.map((r) => r.profile) ?? []),
    ]);
    const rules = [];
    for (const profileName of names) {
      const games = gamesForProfile(gameRules, profileName, overrides);
      if (!games.process.length && !games.steam_appid.length) continue;
      rules.push({
        name: profileName,
        profile: profileName,
        match: {
          process: games.process,
          steam_appid: games.steam_appid,
        },
      });
    }
    return {
      enabled,
      default_profile: defaultProf.trim() || null,
      poll_seconds: gameRules?.poll_seconds ?? 2,
      rules,
    };
  };

  const persistRules = async (
    overrides: Record<string, ProfileGames>,
    opts?: { enabled?: boolean; defaultProfile?: string; success?: string }
  ) => {
    const payload = buildRulesPayload(
      overrides,
      opts?.enabled ?? autoEnabled,
      opts?.defaultProfile ?? defaultProfile
    );
    await saveGameRules.mutateAsync(payload);
    setGamesOverrides({});
    setEnabledOverride(null);
    setDefaultOverride(null);
    if (opts?.success) setMessage(opts.success);
  };

  const handleToggleAuto = async (enabled: boolean) => {
    clearFeedback();
    setEnabledOverride(enabled);
    try {
      await persistRules(gamesOverrides, {
        enabled,
        success: enabled ? 'Auto-switch enabled' : 'Auto-switch disabled',
      });
    } catch (e) {
      setErrorMsg(e instanceof Error ? e.message : 'Failed to update auto-switch');
    }
  };

  const handleDefaultChange = async (value: string) => {
    clearFeedback();
    setDefaultOverride(value);
    try {
      await persistRules(gamesOverrides, {
        defaultProfile: value,
        success: 'Default profile updated',
      });
    } catch (e) {
      setErrorMsg(e instanceof Error ? e.message : 'Failed to update default profile');
    }
  };

  const handleCreateBlank = async () => {
    clearFeedback();
    const name = manualName.trim();
    if (!name) {
      setErrorMsg('Enter a profile name');
      return;
    }
    try {
      await saveProfile.mutateAsync({ name, config });
      setManualName('');
      setMessage(`Created profile “${name}” from current settings`);
    } catch (e) {
      setErrorMsg(e instanceof Error ? e.message : 'Failed to create profile');
    }
  };

  const handleActivate = async (name: string) => {
    clearFeedback();
    try {
      await activateProfile.mutateAsync({ name, apply: true });
      setMessage(`Activated “${name}” on controller`);
    } catch (e) {
      setErrorMsg(e instanceof Error ? e.message : 'Failed to activate profile');
    }
  };

  const handleUpdate = async (name: string) => {
    clearFeedback();
    try {
      await saveProfile.mutateAsync({ name, config });
      setMessage(`Updated “${name}” (includes lighting & face LEDs)`);
    } catch (e) {
      setErrorMsg(e instanceof Error ? e.message : 'Failed to update profile');
    }
  };

  const handleDelete = async (name: string) => {
    clearFeedback();
    if (!window.confirm(`Delete profile “${name}” and its game links?`)) return;
    try {
      const nextOverrides: Record<string, ProfileGames> = { ...gamesOverrides };
      nextOverrides[name] = { process: [], steam_appid: [] };
      // Remove from rules by empty games, then delete profile
      const payload = buildRulesPayload(nextOverrides);
      payload.rules = payload.rules.filter((r) => r.profile !== name);
      await saveGameRules.mutateAsync(payload);
      await deleteProfile.mutateAsync(name);
      setGamesOverrides({});
      setMessage(`Deleted “${name}”`);
    } catch (e) {
      setErrorMsg(e instanceof Error ? e.message : 'Failed to delete profile');
    }
  };

  const handleRemoveGame = async (
    profileName: string,
    kind: 'process' | 'steam_appid',
    value: string
  ) => {
    clearFeedback();
    const current = getGames(profileName);
    const next: ProfileGames = {
      process:
        kind === 'process'
          ? current.process.filter((p) => p !== value)
          : current.process,
      steam_appid:
        kind === 'steam_appid'
          ? current.steam_appid.filter((p) => p !== value)
          : current.steam_appid,
    };
    const overrides = { ...gamesOverrides, [profileName]: next };
    setGamesOverrides(overrides);
    try {
      await persistRules(overrides, { success: `Removed ${value} from “${profileName}”` });
    } catch (e) {
      setErrorMsg(e instanceof Error ? e.message : 'Failed to update games');
    }
  };

  const handlePickerPick = (picked: PickableProcess) => {
    if (!pickerMode) return;
    if (pickerMode.kind === 'add') {
      void (async () => {
        clearFeedback();
        const profileName = pickerMode.profile;
        const next = addGameTo(getGames(profileName), picked);
        const overrides = { ...gamesOverrides, [profileName]: next };
        setGamesOverrides(overrides);
        setPickerMode(null);
        try {
          await persistRules(overrides, {
            enabled: true,
            success: `Added ${picked.match} to “${profileName}”`,
          });
        } catch (e) {
          setErrorMsg(e instanceof Error ? e.message : 'Failed to add game');
        }
      })();
      return;
    }

    // create flow — ask for profile name / existing profile
    setPickerMode(null);
    setCreateDraft({
      picked,
      profileName: suggestProfileName(picked.match, picked.label),
      target: 'new',
    });
  };

  const handleConfirmCreate = async () => {
    if (!createDraft) return;
    clearFeedback();
    const picked = createDraft.picked;

    try {
      if (createDraft.target === 'new') {
        const name = createDraft.profileName.trim();
        if (!name) {
          setErrorMsg('Enter a profile name');
          return;
        }
        await saveProfile.mutateAsync({ name, config });
        const next = addGameTo({ process: [], steam_appid: [] }, picked);
        const overrides = { ...gamesOverrides, [name]: next };
        setGamesOverrides(overrides);
        await persistRules(overrides, {
          enabled: true,
          success: `Created “${name}” and linked ${picked.match}`,
        });
      } else {
        const name = createDraft.target;
        const next = addGameTo(getGames(name), picked);
        const overrides = { ...gamesOverrides, [name]: next };
        setGamesOverrides(overrides);
        await persistRules(overrides, {
          enabled: true,
          success: `Linked ${picked.match} to “${name}”`,
        });
      }
      setCreateDraft(null);
    } catch (e) {
      setErrorMsg(e instanceof Error ? e.message : 'Failed to create profile from game');
    }
  };

  const statusLine = (() => {
    if (!gameStatus) return null;
    if (gameStatus.last_error) return `Auto-switch error: ${gameStatus.last_error}`;
    if (gameStatus.active_game) {
      return `Playing: ${gameStatus.active_game} → “${gameStatus.active_profile ?? '—'}”`;
    }
    if (autoEnabled) return 'Auto-switch on — no linked game running';
    return 'Auto-switch off';
  })();

  const defaultOptions = [
    { value: '', label: 'None (keep last profile)' },
    ...profiles.map((p) => ({ value: p.name, label: p.name })),
  ];

  const assignOptions = [
    { value: 'new', label: 'Create a new profile' },
    ...profiles.map((p) => ({ value: p.name, label: `Add to “${p.name}”` })),
  ];

  return (
    <div>
      <h2>Profiles</h2>
      <p className="profiles-intro">
        A profile is a full controller setup — remaps, sticks, <strong>and lighting /
        face LED colors</strong>. Attach one or more games to it (e.g. a{' '}
        <strong>Souls</strong> profile for DS1–DS3). When a linked game runs,
        GameGent activates that profile automatically, colors included.
      </p>

      {(message || errorMsg) && (
        <p className={`profiles-feedback ${errorMsg ? 'profiles-feedback--error' : ''}`}>
          {errorMsg ?? message}
        </p>
      )}

      <div className="setting-grid">
        <SettingCard title="Auto-switch" span={2}>
          <CheckboxField
            label="When a linked game is running, activate its profile"
            checked={autoEnabled}
            onChange={(v) => void handleToggleAuto(v)}
          />
          <SelectField
            label="When no game matches"
            value={defaultProfile}
            options={defaultOptions}
            onChange={(v) => void handleDefaultChange(v)}
          />
          {statusLine && <p className="profiles-hint profiles-status">{statusLine}</p>}
        </SettingCard>

        <SettingCard title="New profile" span={2}>
          <div className="profiles-create-actions">
            <button
              type="button"
              className="form-btn"
              onClick={() => setPickerMode({ kind: 'create' })}
              disabled={busy || rulesPending}
            >
              New profile from running game…
            </button>
          </div>
          <p className="profiles-hint">
            Launch the game, pick its process, then name the profile (e.g. rename
            DarkSoulsIII to Souls). You can add more games to the same profile later.
          </p>
          <div className="profiles-manual-create">
            <TextField
              label="Or create from current settings"
              value={manualName}
              onChange={setManualName}
              placeholder="e.g. Souls, Control, Default"
            />
            <button
              type="button"
              className="form-btn-secondary"
              onClick={() => void handleCreateBlank()}
              disabled={busy || !manualName.trim()}
            >
              Create profile
            </button>
          </div>
          {isDirty && (
            <p className="profiles-hint">Current unsaved UI edits will be included in a new profile.</p>
          )}
          {active && (
            <p className="profiles-hint">
              Active now: <strong>{active}</strong>
            </p>
          )}
        </SettingCard>

        <SettingCard title="Your profiles" span={2}>
          {isPending && <p className="profiles-hint">Loading profiles…</p>}
          {isError && (
            <p className="profiles-feedback profiles-feedback--error">
              {error instanceof Error ? error.message : 'Failed to load profiles'}
            </p>
          )}
          {!isPending && profiles.length === 0 && (
            <p className="mappings-empty">
              No profiles yet. Start with “New profile from running game…”.
            </p>
          )}

          <div className="profiles-list">
            {profiles.map((p) => {
              const games = getGames(p.name);
              const gameCount = games.process.length + games.steam_appid.length;
              return (
                <div
                  key={p.name}
                  className={`profile-card ${p.active ? 'profile-card--active' : ''}`}
                >
                  <div className="profile-card__header">
                    <div className="profile-card__title">
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
                        onClick={() => void handleActivate(p.name)}
                        disabled={busy}
                      >
                        Activate
                      </button>
                      <button
                        type="button"
                        className="form-btn-secondary"
                        onClick={() => void handleUpdate(p.name)}
                        disabled={busy}
                        title="Overwrite this profile with the current working config (lighting, remaps, sticks, …)"
                      >
                        Save colors & settings
                      </button>
                      <button
                        type="button"
                        className="form-btn form-btn-danger"
                        onClick={() => void handleDelete(p.name)}
                        disabled={busy}
                      >
                        Delete
                      </button>
                    </div>
                  </div>

                  <div className="profile-card__appearance">
                    <h4>Look</h4>
                    {p.appearance ? (
                      <div className="profile-swatches" title={`${p.appearance.lighting_mode ?? 'static'} · brightness ${p.appearance.brightness ?? 100}`}>
                        <span
                          className="profile-swatch profile-swatch--panel"
                          style={{ background: p.appearance.panel ?? 'transparent' }}
                          title="Panel"
                        />
                        {(['a', 'b', 'x', 'y'] as const).map((btn) => (
                          <span
                            key={btn}
                            className="profile-swatch"
                            style={{
                              background: p.appearance?.face?.[btn] ?? 'var(--bg-primary)',
                            }}
                            title={`Face ${btn.toUpperCase()}`}
                          >
                            {btn.toUpperCase()}
                          </span>
                        ))}
                        {p.appearance.home && (
                          <span
                            className="profile-swatch profile-swatch--home"
                            style={{ background: p.appearance.home }}
                            title="Home LED"
                          />
                        )}
                      </div>
                    ) : (
                      <p className="profiles-hint">No lighting saved yet.</p>
                    )}
                    <p className="profiles-hint">
                      Set Lighting / Face LEDs in those tabs, then{' '}
                      <strong>Save colors & settings</strong> on this profile.
                    </p>
                  </div>

                  <div className="profile-card__games">
                    <div className="profile-card__games-head">
                      <h4>Games using this profile</h4>
                      <button
                        type="button"
                        className="form-btn-secondary profile-row__pick-btn"
                        onClick={() => setPickerMode({ kind: 'add', profile: p.name })}
                        disabled={busy}
                      >
                        Add game…
                      </button>
                    </div>
                    {gameCount === 0 ? (
                      <p className="profiles-hint">
                        No games linked. Add DS1 / DS2 / DS3 here to share one Souls setup.
                      </p>
                    ) : (
                      <ul className="game-chip-list">
                        {games.process.map((proc) => (
                          <li key={`p:${proc}`} className="game-chip">
                            <span className="game-chip__label">{proc}</span>
                            <button
                              type="button"
                              className="game-chip__remove"
                              aria-label={`Remove ${proc}`}
                              onClick={() => void handleRemoveGame(p.name, 'process', proc)}
                              disabled={busy}
                            >
                              ×
                            </button>
                          </li>
                        ))}
                        {games.steam_appid.map((id) => (
                          <li key={`s:${id}`} className="game-chip game-chip--steam">
                            <span className="game-chip__label">Steam {id}</span>
                            <button
                              type="button"
                              className="game-chip__remove"
                              aria-label={`Remove Steam ${id}`}
                              onClick={() => void handleRemoveGame(p.name, 'steam_appid', id)}
                              disabled={busy}
                            >
                              ×
                            </button>
                          </li>
                        ))}
                      </ul>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </SettingCard>
      </div>

      <ProcessPicker
        open={pickerMode !== null}
        onClose={() => setPickerMode(null)}
        onPick={handlePickerPick}
      />

      <CreateFromGameDialog
        open={createDraft !== null}
        picked={createDraft?.picked ?? null}
        profileName={createDraft?.profileName ?? ''}
        target={createDraft?.target ?? 'new'}
        assignOptions={assignOptions}
        busy={busy}
        onClose={() => setCreateDraft(null)}
        onProfileNameChange={(v) =>
          setCreateDraft((d) => (d ? { ...d, profileName: v } : d))
        }
        onTargetChange={(v) =>
          setCreateDraft((d) =>
            d
              ? {
                  ...d,
                  target: v,
                  profileName:
                    v === 'new'
                      ? suggestProfileName(d.picked.match, d.picked.label)
                      : d.profileName,
                }
              : d
          )
        }
        onConfirm={() => void handleConfirmCreate()}
      />
    </div>
  );
}
