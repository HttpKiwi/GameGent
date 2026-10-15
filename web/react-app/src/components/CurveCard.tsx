import { SelectField, RangeSlider, NumberField, SettingCard } from './ui';

const CURVE_OPTIONS = [
  { value: 'linear', label: 'Linear' },
  { value: 'expo', label: 'Concave / Convex' },
  { value: 's-curve', label: 'S-Curve' },
  { value: 'custom', label: 'Custom' },
];

const DEFAULT_POINTS: [number, number][] = [
  [30, 30],
  [50, 50],
  [70, 70],
];

type Curve = {
  curve_preset?: unknown;
  curve_intensity?: unknown;
  curve_points?: unknown;
};

/** Response curve: preset + curvature, or three editable points for "Custom". */
export function CurveCard({
  value,
  onChange,
}: {
  value: Curve;
  onChange: (updates: Record<string, unknown>) => void;
}) {
  const preset = (value.curve_preset as string) ?? 'linear';
  const points = (value.curve_points as [number, number][] | undefined) ?? DEFAULT_POINTS;

  const setPoint = (i: number, axis: 0 | 1, v: number) => {
    const next = points.map((p) => [...p] as [number, number]);
    next[i][axis] = Math.max(0, Math.min(100, v));
    onChange({ curve_points: next });
  };

  return (
    <SettingCard title="Curve">
      <SelectField
        label="Response curve"
        value={preset}
        options={CURVE_OPTIONS}
        onChange={(v) =>
          onChange({ curve_preset: v, ...(v === 'custom' && !value.curve_points ? { curve_points: DEFAULT_POINTS } : {}) })
        }
      />
      {(preset === 'expo' || preset === 's-curve') && (
        <RangeSlider
          label="Curvature"
          value={(value.curve_intensity as number) ?? 100}
          min={0}
          max={100}
          onChange={(v) => onChange({ curve_intensity: v })}
        />
      )}
      {preset === 'custom' &&
        points.map((p, i) => (
          <div className="card-row" key={i}>
            <NumberField label={`Point ${i + 1} input`} value={p[0]} min={0} max={100} onChange={(v) => setPoint(i, 0, v)} />
            <NumberField label={`Point ${i + 1} output`} value={p[1]} min={0} max={100} onChange={(v) => setPoint(i, 1, v)} />
          </div>
        ))}
    </SettingCard>
  );
}
