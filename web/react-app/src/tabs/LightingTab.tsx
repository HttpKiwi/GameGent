import { useConfigStore } from '../stores/configStore';
import { useLighting, useLED, useSaveConfig } from '../hooks/useApi';
import { SelectField, RangeSlider, ColorWheel, SettingCard } from '../components/ui';

const LIGHTING_MODES = [
  { value: 'off', label: 'Off' },
  { value: 'static', label: 'Static' },
  { value: 'breathing', label: 'Breathing' },
  { value: 'colorful', label: 'Colorful' },
  { value: 'rainbow', label: 'Rainbow' },
  { value: 'radar', label: 'Radar' },
];

const LED_TARGETS = [
  { value: 'panel', label: 'Panel' },
  { value: 'home', label: 'Home' },
];

export function LightingTab() {
  const config = useConfigStore((s) => s.config);
  const setConfig = useConfigStore((s) => s.setConfig);
  const lighting = useLighting();
  const led = useLED();
  const saveConfig = useSaveConfig();

  const mode = config.lighting_mode ?? 'static';
  const brightness = config.brightness ?? 100;
  const speed = config.lighting_speed ?? 100;
  const target = config.lighting_zone === 1 ? 'panel' : 'home';
  const hue = config.color_hue ?? 0;
  const saturation = config.color_saturation ?? 100;
  const lightness = config.color_lightness ?? 50;

  const handleApply = async () => {
    await lighting.mutateAsync({ mode, brightness, speed });
    await led.mutateAsync({ target, hue, saturation, lightness });

    const updated = {
      ...config,
      lighting_mode: mode,
      brightness,
      lighting_speed: speed,
      color_hue: hue,
      color_saturation: saturation,
      color_lightness: lightness,
      lighting_zone: target === 'panel' ? 1 : 0,
    };
    await saveConfig.mutateAsync(updated);
  };

  return (
    <div>
      <h2>Lighting</h2>
      <div className="setting-grid">
        <SettingCard title="Behavior">
          <SelectField
            label="Lighting Mode"
            value={mode}
            options={LIGHTING_MODES}
            onChange={(v) => setConfig({ ...config, lighting_mode: v })}
          />
          <div className="card-row">
            <RangeSlider
              label="Brightness"
              value={brightness}
              min={0}
              max={100}
              onChange={(v) => setConfig({ ...config, brightness: v })}
            />
            <RangeSlider
              label="Speed"
              value={speed}
              min={0}
              max={100}
              onChange={(v) => setConfig({ ...config, lighting_speed: v })}
            />
          </div>
        </SettingCard>

        <SettingCard title="Target">
          <SelectField
            label="Target LED"
            value={target}
            options={LED_TARGETS}
            onChange={(v) =>
              setConfig({ ...config, lighting_zone: v === 'panel' ? 1 : 0 })
            }
          />
        </SettingCard>

        <SettingCard title="Color" span={2}>
          <ColorWheel
            hue={hue}
            saturation={saturation}
            lightness={lightness}
            onColorChange={({ h, s, l }) =>
              setConfig({
                ...config,
                color_hue: h,
                color_saturation: s,
                color_lightness: l,
              })
            }
          />
          <RangeSlider
            label="Hue"
            value={hue}
            min={0}
            max={360}
            suffix="°"
            onChange={(v) => setConfig({ ...config, color_hue: v })}
          />
          <div className="card-row">
            <RangeSlider
              label="Saturation"
              value={saturation}
              min={0}
              max={100}
              onChange={(v) => setConfig({ ...config, color_saturation: v })}
            />
            <RangeSlider
              label="Lightness"
              value={lightness}
              min={0}
              max={100}
              onChange={(v) => setConfig({ ...config, color_lightness: v })}
            />
          </div>
        </SettingCard>
      </div>
      <button className="save-btn" onClick={handleApply}>
        Apply Lighting
      </button>
    </div>
  );
}
