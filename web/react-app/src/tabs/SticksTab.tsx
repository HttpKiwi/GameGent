import { useConfigStore } from '../stores/configStore';
import { useSticks, useSaveConfig } from '../hooks/useApi';
import { SelectField, RangeSlider, SettingCard } from '../components/ui';

const STICK_MODES = [
  { value: 'native', label: 'Native' },
  { value: 'mouse', label: 'Mouse' },
  { value: 'keyboard', label: 'Keyboard' },
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

export function SticksTab() {
  const config = useConfigStore((s) => s.config);
  const setConfig = useConfigStore((s) => s.setConfig);
  const sticks = useSticks();
  const saveConfig = useSaveConfig();

  const handleApply = async () => {
    const left = config.stick_left ?? {};
    const right = config.stick_right ?? {};

    const leftData = {
      mode: left.mode,
      x_sens: left.x_sensitivity,
      y_sens: left.y_sensitivity,
      overlap: left.overlap_percent,
      mouse_dpi: left.mouse_x_dpi,
      mouse_ydpi: left.mouse_y_dpi,
      square: left.is_circle === false,
      deadzone_min: left.deadzone_min,
      antideadzone_min: left.antideadzone_min,
      deadzone_max: left.deadzone_max,
      antideadzone_max: left.antideadzone_max,
      curve: left.curve_preset,
      curve_intensity: left.curve_intensity,
    };
    const rightData = {
      mode: right.mode,
      x_sens: right.x_sensitivity,
      y_sens: right.y_sensitivity,
      overlap: right.overlap_percent,
      mouse_dpi: right.mouse_x_dpi,
      mouse_ydpi: right.mouse_y_dpi,
      square: right.is_circle === false,
      deadzone_min: right.deadzone_min,
      antideadzone_min: right.antideadzone_min,
      deadzone_max: right.deadzone_max,
      antideadzone_max: right.antideadzone_max,
      curve: right.curve_preset,
      curve_intensity: right.curve_intensity,
    };

    await sticks.mutateAsync({ left: leftData, right: rightData });
    await saveConfig.mutateAsync(config);
  };

  return (
    <div>
      <h2>Sticks</h2>
      <StickSection label="Left Stick" side="left" config={config} setConfig={setConfig} />
      <StickSection label="Right Stick" side="right" config={config} setConfig={setConfig} />
      <button className="save-btn" onClick={handleApply}>
        Apply Sticks
      </button>
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

        <SettingCard title="Sensitivity" span={2}>
          <div className="card-row">
            <RangeSlider
              label="X Sensitivity"
              value={(s.x_sensitivity as number) ?? 50}
              min={0}
              max={100}
              onChange={(v) => set({ x_sensitivity: v })}
            />
            <RangeSlider
              label="Y Sensitivity"
              value={(s.y_sensitivity as number) ?? 50}
              min={0}
              max={100}
              onChange={(v) => set({ y_sensitivity: v })}
            />
          </div>
          <div className="card-row">
            <RangeSlider
              label="Mouse X DPI"
              value={(s.mouse_x_dpi as number) ?? 50}
              min={0}
              max={100}
              onChange={(v) => set({ mouse_x_dpi: v })}
            />
            <RangeSlider
              label="Mouse Y DPI"
              value={(s.mouse_y_dpi as number) ?? 50}
              min={0}
              max={100}
              onChange={(v) => set({ mouse_y_dpi: v })}
            />
          </div>
          <RangeSlider
            label="Overlap"
            value={(s.overlap_percent as number) ?? 50}
            min={0}
            max={100}
            onChange={(v) => set({ overlap_percent: v })}
          />
        </SettingCard>

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
