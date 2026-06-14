import { type ChangeEvent } from 'react';

interface RangeSliderProps {
  label?: string;
  value: number;
  min: number;
  max: number;
  suffix?: string;
  onChange: (value: number) => void;
}

export function RangeSlider({
  label,
  value,
  min,
  max,
  suffix = '%',
  onChange,
}: RangeSliderProps) {
  return (
    <div className="setting-group">
      {label && <label>{label}</label>}
      <input
        type="range"
        min={min}
        max={max}
        value={value}
        onChange={(e: ChangeEvent<HTMLInputElement>) =>
          onChange(parseInt(e.target.value))
        }
      />
      <span className="value-display">
        {value}
        {suffix}
      </span>
    </div>
  );
}
