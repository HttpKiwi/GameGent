import { useConfigStore } from '../stores/configStore';
import { useTriggers, useSaveConfig } from '../hooks/useApi';
import { SelectField, RangeSlider, SettingCard } from '../components/ui';

const HAIR_MODES = [
  { value: 'off', label: 'Off' },
  { value: 'adaptive', label: 'Adaptive' },
  { value: 'fixed', label: 'Fixed' },
];

const CURVE_OPTIONS = [
  { value: 'linear', label: 'Linear' },
  { value: 'expo', label: 'Expo' },
  { value: 's-curve', label: 'S-Curve' },
];

type Side = 'left' | 'right';

export function TriggersTab() {
  const config = useConfigStore((s) => s.config);
  const setConfig = useConfigStore((s) => s.setConfig);
  const triggers = useTriggers();
  const saveConfig = useSaveConfig();

  const tl = config.trigger_left ?? {};
  const tr = config.trigger_right ?? {};

  const handleApply = async () => {
    await triggers.mutateAsync({
      hair: tl.hair_mode,
      hair_begin: tl.hair_trigger_begin,
      hair_end: tl.hair_trigger_end,
      dz_begin: tl.deadzone_begin,
      dz_end: tl.deadzone_end,
      anti_begin: tl.antideadzone_begin,
      anti_end: tl.antideadzone_end,
      curve: tl.curve_preset,
      curve_intensity: tl.curve_intensity,
      left_hair: tr.hair_mode,
      left_hair_begin: tr.hair_trigger_begin,
      left_hair_end: tr.hair_trigger_end,
      left_dz_begin: tr.deadzone_begin,
      left_dz_end: tr.deadzone_end,
      left_anti_begin: tr.antideadzone_begin,
      left_anti_end: tr.antideadzone_end,
      left_curve: tr.curve_preset,
      left_intensity: tr.curve_intensity,
    });
    await saveConfig.mutateAsync(config);
  };

  return (
    <div>
      <h2>Triggers</h2>
      <TriggerSection label="Left Trigger" side="left" config={config} setConfig={setConfig} />
      <TriggerSection label="Right Trigger" side="right" config={config} setConfig={setConfig} />
      <button className="save-btn" onClick={handleApply}>
        Apply Triggers
      </button>
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

        <SettingCard title="Curve">
          <SelectField
            label="Preset"
            value={(t.curve_preset as string) ?? 'linear'}
            options={CURVE_OPTIONS}
            onChange={(v) => set({ curve_preset: v })}
          />
          <RangeSlider
            label="Intensity"
            value={(t.curve_intensity as number) ?? 50}
            min={0}
            max={100}
            onChange={(v) => set({ curve_intensity: v })}
          />
        </SettingCard>
      </div>
    </div>
  );
}
