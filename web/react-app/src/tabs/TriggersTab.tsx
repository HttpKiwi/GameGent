import { useConfigStore } from '../stores/configStore';
import { ResetButton } from '../components/ResetButton';
import { CurveCard } from '../components/CurveCard';
import { SelectField, RangeSlider, SettingCard } from '../components/ui';

const HAIR_MODES = [
  { value: 'off', label: 'Off' },
  { value: 'adaptive', label: 'Adaptive' },
  { value: 'fixed', label: 'Fixed' },
];

type Side = 'left' | 'right';

export function TriggersTab() {
  const config = useConfigStore((s) => s.config);
  const setConfig = useConfigStore((s) => s.setConfig);



  return (
    <div>
      <h2>Triggers</h2>
      <ResetButton sections={['triggers']} what="triggers" />
      <TriggerSection label="Left Trigger" side="left" config={config} setConfig={setConfig} />
      <TriggerSection label="Right Trigger" side="right" config={config} setConfig={setConfig} />
    </div>
  );
}

function TriggerSection({
  label,
  side,
  config,
  setConfig,
}: {
  label: string;
  side: Side;
  config: ReturnType<typeof useConfigStore.getState>['config'];
  setConfig: (c: typeof config) => void;
}) {
  const t = (side === 'left' ? config.trigger_left : config.trigger_right) ?? {};

  const set = (updates: Record<string, unknown>) => {
    const key = side === 'left' ? 'trigger_left' : 'trigger_right';
    setConfig({ ...config, [key]: { ...t, ...updates } });
  };

  return (
    <div style={{ marginBottom: '24px' }}>
      <h3 style={{ margin: '20px 0 14px 0', fontSize: '1.2rem' }}>{label}</h3>
      <div className="setting-grid">
        <SettingCard title="Hair Trigger">
          <SelectField
            label="Mode"
            value={(t.hair_mode as string) ?? 'off'}
            options={HAIR_MODES}
            onChange={(v) => set({ hair_mode: v })}
          />
          <div className="card-row">
            <RangeSlider
              label="Begin"
              value={(t.hair_trigger_begin as number) ?? 0}
              min={0}
              max={100}
              onChange={(v) => set({ hair_trigger_begin: v })}
            />
            <RangeSlider
              label="End"
              value={(t.hair_trigger_end as number) ?? 100}
              min={0}
              max={100}
              onChange={(v) => set({ hair_trigger_end: v })}
            />
          </div>
        </SettingCard>

        <SettingCard title="Deadzone">
          <div className="card-row">
            <RangeSlider
              label="Begin"
              value={(t.deadzone_begin as number) ?? 0}
              min={0}
              max={100}
              onChange={(v) => set({ deadzone_begin: v })}
            />
            <RangeSlider
              label="End"
              value={(t.deadzone_end as number) ?? 100}
              min={0}
              max={100}
              onChange={(v) => set({ deadzone_end: v })}
            />
          </div>
        </SettingCard>

        <SettingCard title="Anti-Deadzone">
          <div className="card-row">
            <RangeSlider
              label="Begin"
              value={(t.antideadzone_begin as number) ?? 0}
              min={0}
              max={100}
              onChange={(v) => set({ antideadzone_begin: v })}
            />
            <RangeSlider
              label="End"
              value={(t.antideadzone_end as number) ?? 100}
              min={0}
              max={100}
              onChange={(v) => set({ antideadzone_end: v })}
            />
          </div>
        </SettingCard>

        <CurveCard value={t} onChange={set} />
      </div>
    </div>
  );
}
