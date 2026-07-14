import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { TabLayout } from './components/TabLayout';
import { DashboardTab } from './tabs/DashboardTab';
import { LightingTab } from './tabs/LightingTab';
import { FaceLEDsTab } from './tabs/FaceLEDsTab';
import { TriggersTab } from './tabs/TriggersTab';
import { SticksTab } from './tabs/SticksTab';
import { GyroTab } from './tabs/GyroTab';
import { ButtonsTab } from './tabs/ButtonsTab';
import { RumbleTab } from './tabs/RumbleTab';
import { CombosTab } from './tabs/CombosTab';
import { MacrosTab } from './tabs/MacrosTab';
import { useConfig, useSaveConfig, useDeviceStatus, useDeviceMappingsPoll } from './hooks/useApi';
import { useConfigStore } from './stores/configStore';
import { useEffect } from 'react';
import './App.css';

const queryClient = new QueryClient();

const TABS = [
  { id: 'dashboard', label: 'Dashboard', group: 'overview', content: <DashboardTab /> },
  { id: 'lighting', label: 'Lighting', group: 'appearance', content: <LightingTab /> },
  { id: 'face-leds', label: 'Face LEDs', group: 'appearance', content: <FaceLEDsTab /> },
  { id: 'rumble', label: 'Rumble', group: 'appearance', content: <RumbleTab /> },
  { id: 'triggers', label: 'Triggers', group: 'controls', content: <TriggersTab /> },
  { id: 'sticks', label: 'Sticks', group: 'controls', content: <SticksTab /> },
  { id: 'gyro', label: 'Gyro', group: 'controls', content: <GyroTab /> },
  { id: 'buttons', label: 'Buttons', group: 'controls', content: <ButtonsTab /> },
  { id: 'combos', label: 'Combos', group: 'advanced', content: <CombosTab /> },
  { id: 'macros', label: 'Macros', group: 'advanced', content: <MacrosTab /> },
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

function AppContent() {
  const { data: serverConfig } = useConfig();
  const setConfigFromServer = useConfigStore((s) => s.setConfigFromServer);
  const config = useConfigStore((s) => s.config);
  const isDirty = useConfigStore((s) => s.isDirty);
  const saveConfig = useSaveConfig();

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
        <ConnectionIndicator />
      </header>

      <TabLayout tabs={TABS} />

      <footer className="app-footer">
        <button
          className={`global-save-btn ${isDirty ? 'global-save-btn--dirty' : ''}`}
          onClick={() => saveConfig.mutate(config)}
          disabled={saveConfig.isPending}
        >
          {saveConfig.isPending ? 'Saving…' : isDirty ? 'Save Configuration •' : 'Save All Configuration'}
        </button>
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
