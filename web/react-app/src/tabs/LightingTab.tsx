import { useState } from 'react';
import { useConfigStore } from '../stores/configStore';
import { SelectField, RangeSlider, ColorWheel, SettingCard } from '../components/ui';
import type { FaceLED, GameGentConfig } from '../types/config';

const LIGHTING_MODES = [
  { value: 'off', label: 'Off' },
  { value: 'static', label: 'Static' },
  { value: 'breathing', label: 'Breathing' },
  { value: 'colorful', label: 'Colorful' },
  { value: 'rainbow', label: 'Rainbow' },
  { value: 'radar', label: 'Radar' },
];

const LIGHTS = [
  { id: 'panel', label: 'Panel' },
  { id: 'home', label: 'Home' },
  { id: 'a', label: 'A' },
  { id: 'b', label: 'B' },
  { id: 'x', label: 'X' },
  { id: 'y', label: 'Y' },
] as const;
type LightId = (typeof LIGHTS)[number]['id'];

const FACE: LightId[] = ['a', 'b', 'x', 'y'];
const GROUPS: { label: string; ids: LightId[] }[] = [
  { label: 'All', ids: LIGHTS.map((l) => l.id) },
  { label: 'Face buttons', ids: FACE },
];

type HSL = { h: number; s: number; l: number };
const DEFAULT_HSL: HSL = { h: 0, s: 100, l: 50 };
const fromLed = (c: number[]): HSL => ({ h: Math.round((c[0] / 255) * 360), s: c[1], l: c[2] });
const toLed = (c: HSL): FaceLED => [Math.round((c.h / 360) * 255), c.s, c.l];
const css = (c: HSL) => `hsl(${c.h}, ${c.s}%, ${c.l}%)`;

// Panel colour lives in color_*; home and face buttons store [byteHue, sat, light].
function getLight(config: GameGentConfig, id: LightId): HSL {
  if (id === 'panel') {
    return {
      h: config.color_hue ?? 0,
      s: config.color_saturation ?? 100,
      l: config.color_lightness ?? 50,
    };
  }
  if (id === 'home') return config.home_led ? fromLed(config.home_led) : DEFAULT_HSL;
  const led = config.face_leds?.[FACE.indexOf(id)];
  return led ? fromLed(led) : DEFAULT_HSL;
}

function setLights(config: GameGentConfig, ids: LightId[], hsl: HSL): GameGentConfig {
  const next: GameGentConfig = { ...config };
  if (ids.includes('panel')) {
    next.color_hue = hsl.h;
    next.color_saturation = hsl.s;
    next.color_lightness = hsl.l;
    next.lighting_zone = 1;
  }
  if (ids.includes('home')) next.home_led = toLed(hsl);
  if (ids.some((id) => FACE.includes(id))) {
    next.face_leds = FACE.map((id) => (ids.includes(id) ? toLed(hsl) : toLed(getLight(config, id))));
  }
  return next;
}

export function LightingTab() {
  const config = useConfigStore((s) => s.config);
  const setConfig = useConfigStore((s) => s.setConfig);
  const [selected, setSelected] = useState<LightId[]>(['panel']);
  const [group, setGroup] = useState(false);

  const mode = config.lighting_mode ?? 'static';
  const brightness = config.brightness ?? 100;
  const speed = config.lighting_speed ?? 100;
  const hsl = getLight(config, selected[0] ?? 'panel');

  // One light: a click selects just that light. Group: clicks add/remove lights.
  const pick = (id: LightId) =>
    setSelected((cur) => {
      if (!group) return [id];
      return cur.includes(id) ? (cur.length > 1 ? cur.filter((c) => c !== id) : cur) : [...cur, id];
    });
  const setMode = (grouped: boolean) => {
    setGroup(grouped);
    if (!grouped) setSelected((cur) => [cur[0]]);
  };
  const update = (next: HSL) => setConfig(setLights(config, selected, next));
  const sameSet = (ids: LightId[]) =>
    ids.length === selected.length && ids.every((id) => selected.includes(id));

  return (
    <div>
      <h2>Lighting</h2>
      <div className="setting-grid">
        <SettingCard title="Effect">
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

        <SettingCard title="Lights" span={2}>
          <div className="light-chips">
            <button
              className={`light-chip light-chip--group ${!group ? 'light-chip--on' : ''}`}
              onClick={() => setMode(false)}
            >
              One light
            </button>
            <button
              className={`light-chip light-chip--group ${group ? 'light-chip--on' : ''}`}
              onClick={() => setMode(true)}
            >
              Group
            </button>
          </div>
          <div className="light-chips">
            {LIGHTS.map((l) => (
              <button
                key={l.id}
                className={`light-chip ${selected.includes(l.id) ? 'light-chip--on' : ''}`}
                onClick={() => pick(l.id)}
              >
                <span className="light-chip__swatch" style={{ background: css(getLight(config, l.id)) }} />
                {l.label}
              </button>
            ))}
          </div>
          <div className="light-chips">
            {GROUPS.map((g) => (
              <button
                key={g.label}
                className={`light-chip light-chip--group ${sameSet(g.ids) ? 'light-chip--on' : ''}`}
                onClick={() => {
                  setGroup(true);
                  setSelected(g.ids);
                }}
              >
                {g.label}
              </button>
            ))}
          </div>
          <ColorWheel
            hue={hsl.h}
            saturation={hsl.s}
            lightness={hsl.l}
            onColorChange={update}
          />
          <RangeSlider
            label="Hue"
            value={hsl.h}
            min={0}
            max={360}
            suffix="°"
            onChange={(v) => update({ ...hsl, h: v })}
          />
          <div className="card-row">
            <RangeSlider
              label="Saturation"
              value={hsl.s}
              min={0}
              max={100}
              onChange={(v) => update({ ...hsl, s: v })}
            />
            <RangeSlider
              label="Lightness"
              value={hsl.l}
              min={0}
              max={100}
              onChange={(v) => update({ ...hsl, l: v })}
            />
          </div>
        </SettingCard>
      </div>
    </div>
  );
}
