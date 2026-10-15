import { useConfigStore } from '../stores/configStore';
import { SelectField, RangeSlider, SettingCard, CheckboxField } from '../components/ui';

const STICK_MODES = [
  { value: 'native', label: 'Native' },
  { value: 'mouse', label: 'Mouse' },
  { value: 'wheel', label: 'Wheel' },
  { value: 'clone', label: 'Clone' },
];

const SHAPE_OPTIONS = [
  { value: 'circle', label: 'Circle' },
  { value: 'square', label: 'Square' },
];

const CURVE_OPTIONS = [
  { value: 'linear', label: 'Linear' },
  { value: 'expo', label: 'Expo' },
  { value: 's-curve', label: 'S-Curve' },
];

type Side = 'left' | 'right';

function getSensitivity(stick: Record<string, unknown>): number {
  if (stick.axis_ratio !== undefined) return stick.axis_ratio as number;
  if (stick.sensitivity !== undefined) return stick.sensitivity as number;
  if (stick.y_sensitivity !== undefined) return stick.y_sensitivity as number;
  return 50;
}

export function SticksTab() {
  const config = useConfigStore((s) => s.config);
  const setConfig = useConfigStore((s) => s.setConfig);


  return (
    <div>
      <h2>Sticks</h2>
      <StickSection label="Left Stick" side="left" config={config} setConfig={setConfig} />
      <StickSection label="Right Stick" side="right" config={config} setConfig={setConfig} />
    </div>
  );
}

function StickSection({
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
  const key = side === 'left' ? 'stick_left' : 'stick_right';
  const s = (config[key] ?? {}) as Record<string, unknown>;
  const shape = s.is_circle ? 'circle' : 'square';

  const set = (updates: Record<string, unknown>) => {
    setConfig({ ...config, [key]: { ...s, ...updates } });
  };

  return (
    <div style={{ marginBottom: '24px' }}>
      <h3 style={{ margin: '20px 0 14px 0', fontSize: '1.2rem' }}>{label}</h3>
      <div className="setting-grid">
        <SettingCard title="Mode &amp; Shape">
          <SelectField
            label="Mode"
            value={(s.mode as string) ?? 'native'}
            options={STICK_MODES}
            onChange={(v) => set({ mode: v })}
          />
          <SelectField
            label="Shape"
            value={shape}
            options={SHAPE_OPTIONS}
            onChange={(v) => set({ is_circle: v === 'circle' })}
          />
        </SettingCard>

        {(s.mode as string) !== 'mouse' && (
          <SettingCard title="Axes" span={2}>
            <RangeSlider
              label="X/Y Ratio (50 = equal)"
              value={getSensitivity(s)}
              min={0}
              max={100}
              onChange={(v) => set({ axis_ratio: v })}
            />
            <div className="card-row">
              <CheckboxField
                label="Invert X"
                checked={(s.invert_x as boolean) ?? false}
                onChange={(v) => set({ invert_x: v })}
              />
              <CheckboxField
                label="Invert Y"
                checked={(s.invert_y as boolean) ?? false}
                onChange={(v) => set({ invert_y: v })}
              />
            </div>
            {(s.mode as string) === 'wheel' && (
              <RangeSlider
                label="Diagonal Angle"
                value={(s.overlap_percent as number) ?? 50}
                min={0}
                max={100}
                onChange={(v) => set({ overlap_percent: v })}
              />
            )}
          </SettingCard>
        )}

        {(s.mode as string) === 'mouse' && (
          <SettingCard title="Mouse DPI" span={2}>
            <RangeSlider
              label="Mouse DPI"
              value={(s.mouse_dpi as number) ?? 50}
              min={0}
              max={100}
              onChange={(v) => set({ mouse_dpi: v })}
            />
          </SettingCard>
        )}
        <SettingCard title="Deadzone">
          <div className="card-row">
            <RangeSlider
              label="Min"
              value={(s.deadzone_min as number) ?? 5}
              min={0}
              max={100}
              onChange={(v) => set({ deadzone_min: v })}
            />
            <RangeSlider
              label="Max"
              value={(s.deadzone_max as number) ?? 100}
              min={0}
              max={100}
              onChange={(v) => set({ deadzone_max: v })}
            />
          </div>
        </SettingCard>

        <SettingCard title="Anti-Deadzone">
          <div className="card-row">
            <RangeSlider
              label="Min"
              value={(s.antideadzone_min as number) ?? 0}
              min={0}
              max={100}
              onChange={(v) => set({ antideadzone_min: v })}
            />
            <RangeSlider
              label="Max"
              value={(s.antideadzone_max as number) ?? 100}
              min={0}
              max={100}
              onChange={(v) => set({ antideadzone_max: v })}
            />
          </div>
        </SettingCard>

        <SettingCard title="Curve">
          <SelectField
            label="Preset"
            value={(s.curve_preset as string) ?? 'linear'}
            options={CURVE_OPTIONS}
            onChange={(v) => set({ curve_preset: v })}
          />
          <RangeSlider
            label="Intensity"
            value={(s.curve_intensity as number) ?? 50}
            min={0}
            max={100}
            onChange={(v) => set({ curve_intensity: v })}
          />
        </SettingCard>
      </div>
    </div>
  );
}
