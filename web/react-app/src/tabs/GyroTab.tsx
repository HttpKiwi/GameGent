import { useConfigStore } from '../stores/configStore';
import { useGyro, useSaveConfig } from '../hooks/useApi';
import { SelectField, RangeSlider, CheckboxField, TextField, SettingCard } from '../components/ui';
import { BUTTON_OPTIONS } from './buttonOptions';

const GYRO_OUTPUT_MODES = [
  { value: 'mouse', label: 'Mouse' },
  { value: 'left_stick', label: 'Left Stick' },
  { value: 'right_stick', label: 'Right Stick' },
  { value: 'keyboard', label: 'Keyboard' },
];

const MOTION_MODES = [
  { value: 'aim', label: 'Aim' },
  { value: 'tilt', label: 'Tilt' },
];

const METHODS = [
  { value: 'off', label: 'Off' },
  { value: 'hold', label: 'Hold' },
  { value: 'press', label: 'Press' },
  { value: 'always', label: 'Always' },
];

const AXIS_MODES = [
  { value: 'global', label: 'Global' },
  { value: 'yaw', label: 'Yaw' },
  { value: 'roll', label: 'Roll' },
];

const CURVE_OPTIONS = [
  { value: 'linear', label: 'Linear' },
  { value: 'expo', label: 'Expo' },
  { value: 's-curve', label: 'S-Curve' },
];

export function GyroTab() {
  const config = useConfigStore((s) => s.config);
  const setConfig = useConfigStore((s) => s.setConfig);
  const gyro = useGyro();
  const saveConfig = useSaveConfig();

  const g = (config.gyro ?? {}) as Record<string, unknown>;

  const set = (updates: Record<string, unknown>) => {
    setConfig({ ...config, gyro: { ...g, ...updates } });
  };

  const handleApply = async () => {
    await gyro.mutateAsync({
      mode: g.output_mode,
      motion: g.motion_mode,
      method: g.activate_method,
      axis: g.axis_mode,
      button: g.activate_button,
      x_sens: g.x_sensitivity,
      y_sens: g.y_sensitivity,
      overlap: g.overlap_percent,
      deadzone_min: g.deadzone_min,
      deadzone_max: g.deadzone_max,
      antideadzone_min: g.antideadzone_min,
      antideadzone_max: g.antideadzone_max,
      invert_x: g.invert_x,
      invert_y: g.invert_y,
      curve: g.curve_preset,
      curve_intensity: g.curve_intensity,
      kb_up: g.kb_up,
      kb_down: g.kb_down,
      kb_left: g.kb_left,
      kb_right: g.kb_right,
    });
    await saveConfig.mutateAsync(config);
  };

  return (
    <div>
      <h2>Gyro / Motion Aim</h2>
      <div className="setting-grid">
        <SettingCard title="Activation" span={2}>
          <div className="card-row">
            <SelectField
              label="Output Mode"
              value={(g.output_mode as string) ?? 'mouse'}
              options={GYRO_OUTPUT_MODES}
              onChange={(v) => set({ output_mode: v })}
            />
            <SelectField
              label="Motion Mode"
              value={(g.motion_mode as string) ?? 'aim'}
              options={MOTION_MODES}
              onChange={(v) => set({ motion_mode: v })}
            />
          </div>
          <div className="card-row">
            <SelectField
              label="Activation Method"
              value={(g.activate_method as string) ?? 'hold'}
              options={METHODS}
              onChange={(v) => set({ activate_method: v })}
            />
            <SelectField
              label="Axis Mode"
              value={(g.axis_mode as string) ?? 'global'}
              options={AXIS_MODES}
              onChange={(v) => set({ axis_mode: v })}
            />
          </div>
          <SelectField
            label="Activate Button"
            value={(g.activate_button as string) ?? 'c1'}
            options={BUTTON_OPTIONS}
            onChange={(v) => set({ activate_button: v })}
          />
        </SettingCard>

        <SettingCard title="Sensitivity" span={2}>
          <div className="card-row">
            <RangeSlider
              label="X Sensitivity"
              value={(g.x_sensitivity as number) ?? 50}
              min={0}
              max={100}
              onChange={(v) => set({ x_sensitivity: v })}
            />
            <RangeSlider
              label="Y Sensitivity"
              value={(g.y_sensitivity as number) ?? 50}
              min={0}
              max={100}
              onChange={(v) => set({ y_sensitivity: v })}
            />
          </div>
          <RangeSlider
            label="Overlap"
            value={(g.overlap_percent as number) ?? 50}
            min={0}
            max={100}
            onChange={(v) => set({ overlap_percent: v })}
          />
        </SettingCard>

        <SettingCard title="Deadzone">
          <div className="card-row">
            <RangeSlider
              label="Min"
              value={(g.deadzone_min as number) ?? 0}
              min={0}
              max={100}
              onChange={(v) => set({ deadzone_min: v })}
            />
            <RangeSlider
              label="Max"
              value={(g.deadzone_max as number) ?? 100}
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
              value={(g.antideadzone_min as number) ?? 0}
              min={0}
              max={100}
              onChange={(v) => set({ antideadzone_min: v })}
            />
            <RangeSlider
              label="Max"
              value={(g.antideadzone_max as number) ?? 100}
              min={0}
              max={100}
              onChange={(v) => set({ antideadzone_max: v })}
            />
          </div>
        </SettingCard>

        <SettingCard title="Inversion">
          <div className="card-row">
            <CheckboxField
              label="Invert X"
              checked={(g.invert_x as boolean) ?? false}
              onChange={(v) => set({ invert_x: v })}
            />
            <CheckboxField
              label="Invert Y"
              checked={(g.invert_y as boolean) ?? false}
              onChange={(v) => set({ invert_y: v })}
            />
          </div>
        </SettingCard>

        <SettingCard title="Curve">
          <SelectField
            label="Preset"
            value={(g.curve_preset as string) ?? 'linear'}
            options={CURVE_OPTIONS}
            onChange={(v) => set({ curve_preset: v })}
          />
          <RangeSlider
            label="Intensity"
            value={(g.curve_intensity as number) ?? 50}
            min={0}
            max={100}
            onChange={(v) => set({ curve_intensity: v })}
          />
        </SettingCard>

        {(g.output_mode as string) === 'keyboard' && (
          <SettingCard title="Keyboard Targets" span={2}>
            <div className="keyboard-targets">
              <TextField
                label="Up"
                value={(g.kb_up as string) ?? 'key:w'}
                onChange={(v) => set({ kb_up: v })}
              />
              <TextField
                label="Down"
                value={(g.kb_down as string) ?? 'key:s'}
                onChange={(v) => set({ kb_down: v })}
              />
              <TextField
                label="Left"
                value={(g.kb_left as string) ?? 'key:a'}
                onChange={(v) => set({ kb_left: v })}
              />
              <TextField
                label="Right"
                value={(g.kb_right as string) ?? 'key:d'}
                onChange={(v) => set({ kb_right: v })}
              />
            </div>
          </SettingCard>
        )}
      </div>
      <button className="save-btn" onClick={handleApply}>
        Apply Gyro
      </button>
    </div>
  );
}
