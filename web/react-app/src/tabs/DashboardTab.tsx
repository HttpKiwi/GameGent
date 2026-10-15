import { useConfigStore } from '../stores/configStore';
import { SelectField, RangeSlider, SettingCard } from '../components/ui';

const LIGHTING_MODES = [
  { value: 'off', label: 'Off' },
  { value: 'static', label: 'Static' },
  { value: 'breathing', label: 'Breathing' },
  { value: 'colorful', label: 'Colorful' },
  { value: 'rainbow', label: 'Rainbow' },
  { value: 'radar', label: 'Radar' },
];

const LAYOUT_OPTIONS = [
  { value: 'xbox', label: 'Xbox' },
  { value: 'switch', label: 'Switch' },
];

const STICK_MODE_OPTIONS = [
  { value: 'native', label: 'Native' },
  { value: 'mouse', label: 'Mouse' },
  { value: 'keyboard', label: 'Keyboard' },
  { value: 'clone', label: 'Clone' },
];

const GYRO_MODE_OPTIONS = [
  { value: 'mouse', label: 'Mouse' },
  { value: 'left_stick', label: 'Left Stick' },
  { value: 'right_stick', label: 'Right Stick' },
  { value: 'keyboard', label: 'Keyboard' },
];

export function DashboardTab() {
  const config = useConfigStore((s) => s.config);
  const setConfig = useConfigStore((s) => s.setConfig);

  const lighting_mode = config.lighting_mode ?? 'static';
  const brightness = config.brightness ?? 100;
  const abxyLayout = config.layout ?? 'xbox';
  const leftStickMode = config.stick_left?.mode ?? 'native';
  const rightStickMode = config.stick_right?.mode ?? 'native';
  const gyroMode = config.gyro?.output_mode ?? 'mouse';


  return (
    <div>
      <h2>Dashboard</h2>
      <div className="setting-grid">
        <SettingCard title="Lighting Mode">
          <SelectField
            value={lighting_mode}
            options={LIGHTING_MODES}
            onChange={(v) => setConfig({ ...config, lighting_mode: v })}
          />
        </SettingCard>
        <SettingCard title="Brightness">
          <RangeSlider
            value={brightness}
            min={0}
            max={100}
            onChange={(v) => setConfig({ ...config, brightness: v })}
          />
        </SettingCard>
        <SettingCard title="ABXY Layout">
          <SelectField
            value={abxyLayout}
            options={LAYOUT_OPTIONS}
            onChange={(v) => setConfig({ ...config, layout: v })}
          />
        </SettingCard>
        <SettingCard title="Left Stick Mode">
          <SelectField
            value={leftStickMode}
            options={STICK_MODE_OPTIONS}
            onChange={(v) =>
              setConfig({
                ...config,
                stick_left: { ...config.stick_left, mode: v },
              })
            }
          />
        </SettingCard>
        <SettingCard title="Right Stick Mode">
          <SelectField
            value={rightStickMode}
            options={STICK_MODE_OPTIONS}
            onChange={(v) =>
              setConfig({
                ...config,
                stick_right: { ...config.stick_right, mode: v },
              })
            }
          />
        </SettingCard>
        <SettingCard title="Gyro Output">
          <SelectField
            value={gyroMode}
            options={GYRO_MODE_OPTIONS}
            onChange={(v) =>
              setConfig({
                ...config,
                gyro: { ...config.gyro, output_mode: v },
              })
            }
          />
        </SettingCard>
      </div>
    </div>
  );
}
