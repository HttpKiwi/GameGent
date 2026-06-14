import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { TabLayout } from './components/TabLayout';
import { DashboardTab } from './tabs/DashboardTab';
import { LightingTab } from './tabs/LightingTab';
import { FaceLEDsTab } from './tabs/FaceLEDsTab';
import { TriggersTab } from './tabs/TriggersTab';
import { SticksTab } from './tabs/SticksTab';
import { GyroTab } from './tabs/GyroTab';
import { RemappingTab } from './tabs/RemappingTab';
import { TurboTab } from './tabs/TurboTab';
import { RumbleTab } from './tabs/RumbleTab';
import { CombosTab } from './tabs/CombosTab';
import { MacrosTab } from './tabs/MacrosTab';
import { useConfig, useSaveConfig } from './hooks/useApi';
import { useConfigStore } from './stores/configStore';
import { useEffect } from 'react';
import './App.css';

const queryClient = new QueryClient();

const TABS = [
  { id: 'dashboard', label: 'Dashboard', content: <DashboardTab /> },
  { id: 'lighting', label: 'Lighting', content: <LightingTab /> },
  { id: 'face-leds', label: 'Face LEDs', content: <FaceLEDsTab /> },
  { id: 'triggers', label: 'Triggers', content: <TriggersTab /> },
  { id: 'sticks', label: 'Sticks', content: <SticksTab /> },
  { id: 'gyro', label: 'Gyro', content: <GyroTab /> },
  { id: 'remapping', label: 'Remapping', content: <RemappingTab /> },
  { id: 'turbo', label: 'Turbo', content: <TurboTab /> },
  { id: 'rumble', label: 'Rumble', content: <RumbleTab /> },
  { id: 'combos', label: 'Combos', content: <CombosTab /> },
  { id: 'macros', label: 'Macros', content: <MacrosTab /> },
];

function AppContent() {
  const { data: serverConfig } = useConfig();
  const setConfig = useConfigStore((s) => s.setConfig);
  const config = useConfigStore((s) => s.config);
  const saveConfig = useSaveConfig();

  useEffect(() => {
    if (serverConfig) {
      setConfig(serverConfig as Record<string, unknown>);
    }
  }, [serverConfig, setConfig]);

  return (
    <div className="container">
      <header>
        <h1>GameGent</h1>
        <p>GameSir Tarantula Pro Configuration</p>
      </header>

      <TabLayout tabs={TABS} />

      <footer>
        <button className="global-save-btn" onClick={() => saveConfig.mutate(config)}>
          Save All Configuration
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
