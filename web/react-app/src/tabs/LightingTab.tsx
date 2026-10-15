import { useState } from 'react';
import { useConfigStore } from '../stores/configStore';
import { ResetButton } from '../components/ResetButton';
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

// Face LED sets follow the active layout: Xbox uses the ABXY set, Switch the BAYX set.
const FACE_LABELS = {
  xbox: ['A', 'B', 'X', 'Y'],
  switch: ['B', 'A', 'Y', 'X'],
} as const;

type LightId = 'panel' | 'home' | 'f0' | 'f1' | 'f2' | 'f3';
type HSV = { h: number; s: number; v: number };

const DEFAULT_HSV: HSV = { h: 0, s: 100, v: 100 };
const FACE_IDS: LightId[] = ['f0', 'f1', 'f2', 'f3'];
const GROUPS: { label: string; ids: LightId[] }[] = [
  { label: 'All', ids: ['panel', 'home', ...FACE_IDS] },
  { label: 'Face buttons', ids: FACE_IDS },
];

const fromLed = (c: number[]): HSV => ({ h: Math.round((c[0] / 255) * 360), s: c[1], v: c[2] });
const toLed = (c: HSV): FaceLED => [Math.round((c.h / 360) * 255), c.s, c.v];

function hsvToCss({ h, s, v }: HSV): string {
  const sv = s / 100;
  const vv = v / 100;
  const l = vv * (1 - sv / 2);
  const sl = l === 0 || l === 1 ? 0 : (vv - l) / Math.min(l, 1 - l);
  return `hsl(${h}, ${Math.round(sl * 100)}%, ${Math.round(l * 100)}%)`;
}

const faceKey = (config: GameGentConfig) => (config.layout === 'switch' ? 'bayx_leds' : 'face_leds');

// Panel colour lives in color_*; home and face LEDs store [hue byte, saturation, value].
function getLight(config: GameGentConfig, id: LightId): HSV {
  if (id === 'panel') {
    return {
      h: config.color_hue ?? 0,
      s: config.color_saturation ?? 100,
      v: config.brightness ?? 100, // the panel's value is the brightness setting
    };
  }
  if (id === 'home') return config.home_led ? fromLed(config.home_led) : DEFAULT_HSV;
  const led = (config[faceKey(config)] as FaceLED[] | undefined)?.[FACE_IDS.indexOf(id)];
  return led ? fromLed(led) : DEFAULT_HSV;
}

function setLights(config: GameGentConfig, ids: LightId[], hsv: HSV): GameGentConfig {
  const next: GameGentConfig = { ...config };
  if (ids.includes('panel')) {
    next.color_hue = hsv.h;
    next.color_saturation = hsv.s;
    next.lighting_zone = 1;
  }
  if (ids.includes('home')) next.home_led = toLed(hsv);
  if (ids.some((id) => FACE_IDS.includes(id))) {
    next[faceKey(config)] = FACE_IDS.map((id) => (ids.includes(id) ? toLed(hsv) : toLed(getLight(config, id))));
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
  const layout = config.layout === 'switch' ? 'switch' : 'xbox';
  const lights: { id: LightId; label: string }[] = [
    { id: 'panel', label: 'Panel' },
    { id: 'home', label: 'Home' },
    ...FACE_IDS.map((id, i) => ({ id, label: FACE_LABELS[layout][i] })),
  ];
  const hsv = getLight(config, selected[0] ?? 'panel');
  const panelOnly = selected.length === 1 && selected[0] === 'panel';

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
  const update = (next: HSV) => setConfig(setLights(config, selected, next));
  const sameSet = (ids: LightId[]) =>
    ids.length === selected.length && ids.every((id) => selected.includes(id));

  return (
    <div>
      <h2>Lighting</h2>
      <ResetButton sections={['lighting']} what="lighting" />
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
            {lights.map((l) => (
              <button
                key={l.id}
                className={`light-chip ${selected.includes(l.id) ? 'light-chip--on' : ''}`}
                onClick={() => pick(l.id)}
              >
                <span className="light-chip__swatch" style={{ background: hsvToCss(getLight(config, l.id)) }} />
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
          <p className="hint">
            Face buttons are the {layout === 'switch' ? 'Switch (BAYX)' : 'Xbox (ABXY)'} colour set; change the layout on
            the Dashboard to edit the other set.
          </p>
          <ColorWheel
            hue={hsv.h}
            saturation={hsv.s}
            value={hsv.v}
            onColorChange={(c) => update(panelOnly ? { ...c, v: hsv.v } : c)}
          />
          <RangeSlider
            label="Hue"
            value={hsv.h}
            min={0}
            max={360}
            suffix="°"
            onChange={(v) => update({ ...hsv, h: v })}
          />
          <div className="card-row">
            <RangeSlider
              label="Saturation"
              value={hsv.s}
              min={0}
              max={100}
              onChange={(v) => update({ ...hsv, s: v })}
            />
            {!panelOnly && (
              <RangeSlider
                label="Brightness of colour"
                value={hsv.v}
                min={0}
                max={100}
                onChange={(v) => update({ ...hsv, v })}
              />
            )}
          </div>
          {panelOnly && <p className="hint">The panel's brightness is the Brightness slider above.</p>}
        </SettingCard>
      </div>
    </div>
  );
}
