import { useConfigStore } from '../stores/configStore';
import { useFaceColors, useLED, useSaveConfig } from '../hooks/useApi';
import { ColorWheel, RangeSlider, SettingCard } from '../components/ui';
import type { FaceLED } from '../types/config';

const FACE_BUTTONS = ['a', 'b', 'x', 'y', 'home'] as const;
type FaceButton = (typeof FACE_BUTTONS)[number];

function getButtonHSL(
  config: ReturnType<typeof useConfigStore.getState>['config'],
  btn: FaceButton
): { h: number; s: number; l: number } {
  if (btn === 'home' && config.home_led) {
    return {
      h: Math.round((config.home_led[0] / 255) * 360),
      s: config.home_led[1],
      l: config.home_led[2],
    };
  }
  if (config.face_leds) {
    const idx = FACE_BUTTONS.indexOf(btn);
    const color = config.face_leds[idx];
    if (color) {
      return {
        h: Math.round((color[0] / 255) * 360),
        s: color[1],
        l: color[2],
      };
    }
  }
  return { h: 0, s: 100, l: 50 };
}

function setButtonHSL(
  config: Record<string, unknown>,
  btn: FaceButton,
  hsl: { h: number; s: number; l: number }
) {
  const byteHue = Math.round((hsl.h / 360) * 255);
  const led = [byteHue, hsl.s, hsl.l];

  if (btn === 'home') {
    return { ...config, home_led: led };
  }

  const faceLeds = [...((config.face_leds as FaceLED[]) ?? [])];
  const idx = FACE_BUTTONS.indexOf(btn);
  faceLeds[idx] = led;
  return { ...config, face_leds: faceLeds };
}

export function FaceLEDsTab() {
  const config = useConfigStore((s) => s.config);
  const setConfig = useConfigStore((s) => s.setConfig);
  const faceColors = useFaceColors();
  const led = useLED();
  const saveConfig = useSaveConfig();

  const handleApply = async () => {
    const a = getButtonHSL(config, 'a');
    const b = getButtonHSL(config, 'b');
    const x = getButtonHSL(config, 'x');
    const y = getButtonHSL(config, 'y');
    const home = getButtonHSL(config, 'home');

    await faceColors.mutateAsync({
      button: 'all',
      a_hue: a.h,
      a_sat: a.s,
      a_light: a.l,
      b_hue: b.h,
      b_sat: b.s,
      b_light: b.l,
      x_hue: x.h,
      x_sat: x.s,
      x_light: x.l,
      y_hue: y.h,
      y_sat: y.s,
      y_light: y.l,
    });

    await led.mutateAsync({
      target: 'home',
      hue: home.h,
      saturation: home.s,
      lightness: home.l,
    });

    await saveConfig.mutateAsync(config);
  };

  const updateButton = (
    btn: FaceButton,
    hsl: { h: number; s: number; l: number }
  ) => {
    setConfig(setButtonHSL(config, btn, hsl));
  };

  return (
    <div>
      <h2>Face Button LEDs</h2>
      <div className="face-leds-grid">
        {FACE_BUTTONS.map((btn) => {
          const hsl = getButtonHSL(config, btn);
          return (
            <SettingCard key={btn} title={`${btn.toUpperCase()} Button`}>
              <ColorWheel
                hue={hsl.h}
                saturation={hsl.s}
                lightness={hsl.l}
                width={150}
                height={150}
                onColorChange={(newHsl) => updateButton(btn, newHsl)}
              />
              <RangeSlider
                label="Hue"
                value={hsl.h}
                min={0}
                max={360}
                suffix="°"
                onChange={(v) => updateButton(btn, { ...hsl, h: v })}
              />
              <RangeSlider
                label="Saturation"
                value={hsl.s}
                min={0}
                max={100}
                onChange={(v) => updateButton(btn, { ...hsl, s: v })}
              />
              <RangeSlider
                label="Lightness"
                value={hsl.l}
                min={0}
                max={100}
                onChange={(v) => updateButton(btn, { ...hsl, l: v })}
              />
            </SettingCard>
          );
        })}
      </div>
      <button className="save-btn" onClick={handleApply}>
        Apply Face LEDs
      </button>
    </div>
  );
}
