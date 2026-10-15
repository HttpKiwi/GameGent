import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { TabLayout } from './components/TabLayout';
import { DashboardTab } from './tabs/DashboardTab';
import { ProfilesTab } from './tabs/ProfilesTab';
import { LightingTab } from './tabs/LightingTab';
import { TriggersTab } from './tabs/TriggersTab';
import { SticksTab } from './tabs/SticksTab';
import { GyroTab } from './tabs/GyroTab';
import { ButtonsTab } from './tabs/ButtonsTab';
import { RumbleTab } from './tabs/RumbleTab';
import { CombosTab } from './tabs/CombosTab';
import { MacrosTab } from './tabs/MacrosTab';
import { TurboTab } from './tabs/TurboTab';
import {
  useConfig,
  useAutoSave,
  useDeviceStatus,
  useDeviceMappingsPoll,
  useProfiles,
  useActivateProfile,
  useGameRulesStatus,
} from './hooks/useApi';
import { useConfigStore } from './stores/configStore';
import type { AutoSaveState } from './hooks/useApi';
import { useEffect, useState, type ChangeEvent } from 'react';
import './App.css';

const queryClient = new QueryClient();

const TABS = [
  { id: 'dashboard', label: 'Dashboard', group: 'overview', content: <DashboardTab /> },
  { id: 'profiles', label: 'Profiles', group: 'overview', content: <ProfilesTab /> },
  { id: 'lighting', label: 'Lighting', group: 'appearance', content: <LightingTab /> },
  { id: 'rumble', label: 'Rumble', group: 'appearance', content: <RumbleTab /> },
  { id: 'triggers', label: 'Triggers', group: 'controls', content: <TriggersTab /> },
  { id: 'sticks', label: 'Sticks', group: 'controls', content: <SticksTab /> },
  { id: 'gyro', label: 'Gyro', group: 'controls', content: <GyroTab /> },
  { id: 'buttons', label: 'Buttons', group: 'controls', content: <ButtonsTab /> },
  { id: 'combos', label: 'Combos', group: 'advanced', content: <CombosTab /> },
  { id: 'macros', label: 'Macros', group: 'advanced', content: <MacrosTab /> },
  { id: 'turbo', label: 'Turbo', group: 'advanced', content: <TurboTab /> },
];

function ConnectionIndicator() {
  const { data, isError, isPending } = useDeviceStatus();
  const connected = data?.connected === true;
  useDeviceMappingsPoll(connected);

  let label = 'Checking…';
  let state: 'pending' | 'connected' | 'disconnected' = 'pending';
  if (isError) {
    label = 'Disconnected';
    state = 'disconnected';
  } else if (!isPending) {
    label = connected ? 'Connected' : 'Disconnected';
    state = connected ? 'connected' : 'disconnected';
  }

  return (
    <div className={`connection-pill connection-pill--${state}`} title={data?.path ?? undefined}>
      <span className="connection-pill__dot" aria-hidden />
      <span>{label}</span>
    </div>
  );
}

function ProfileSwitcher() {
  const { data } = useProfiles();
  const activateProfile = useActivateProfile();
  const isDirty = useConfigStore((s) => s.isDirty);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const profiles = data?.profiles ?? [];
  const active = data?.active ?? '';

  if (profiles.length === 0) return null;

  const onChange = async (e: ChangeEvent<HTMLSelectElement>) => {
    const name = e.target.value;
    if (!name || name === active) return;
    if (isDirty && !window.confirm('Discard unsaved changes and switch profile?')) {
      e.target.value = active;
      return;
    }
    setErrorMsg(null);
    try {
      await activateProfile.mutateAsync({ name, apply: true });
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : 'Failed to switch profile');
      e.target.value = active;
    }
  };

  return (
    <div className="profile-switcher" title={errorMsg ?? undefined}>
      <label htmlFor="profile-switch">Profile</label>
      <select
        id="profile-switch"
        value={active}
        onChange={onChange}
        disabled={activateProfile.isPending}
      >
        {!active && <option value="">—</option>}
        {profiles.map((p) => (
          <option key={p.name} value={p.name}>
            {p.name}
          </option>
        ))}
      </select>
    </div>
  );
}

function SaveStatus({ state }: { state: AutoSaveState }) {
  if (state.status === 'saving') return <span className="save-status">Saving…</span>;
  if (state.status === 'error') {
    return <span className="save-status save-status--error">Not saved: {state.message}</span>;
  }
  if (state.status === 'saved') {
    const where = state.profile ? ` to profile “${state.profile}”` : '';
    return (
      <span className="save-status">
        Saved{where}
        {state.failed.length > 0 && (
          <span className="save-status--error"> · not applied to controller: {state.failed.join('; ')}</span>
        )}
      </span>
    );
  }
  return <span className="save-status">Changes save and apply automatically</span>;
}

function AppContent() {
  const { data: serverConfig } = useConfig();
  const setConfigFromServer = useConfigStore((s) => s.setConfigFromServer);
  const autoSave = useAutoSave();
  // Keep profiles/config in sync when game auto-switch activates a profile.
  useGameRulesStatus();

  useEffect(() => {
    if (serverConfig) {
      setConfigFromServer(serverConfig);
    }
  }, [serverConfig, setConfigFromServer]);

  return (
    <div className="app">
      <header className="app-header">
        <div className="app-header__brand">
          <div className="app-header__logo">GG</div>
          <div>
            <h1>GameGent</h1>
            <p>GameSir Tarantula Pro</p>
          </div>
        </div>
        <div className="app-header__status">
          <ProfileSwitcher />
          <ConnectionIndicator />
        </div>
      </header>

      <TabLayout tabs={TABS} />

      <footer className="app-footer">
        <SaveStatus state={autoSave} />
      </footer>
    </div>
  );
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <AppContent />
    </QueryClientProvider>
  );
}
