import { type ChangeEvent } from 'react';

interface NumberFieldProps {
  label?: string;
  value: number;
  min?: number;
  max?: number;
  onChange: (value: number) => void;
}

export function NumberField({ label, value, min, max, onChange }: NumberFieldProps) {
  return (
    <div className="setting-group">
      {label && <label>{label}</label>}
      <input
        type="number"
        min={min}
        max={max}
        value={value}
        onChange={(e: ChangeEvent<HTMLInputElement>) =>
          onChange(parseInt(e.target.value) || 0)
        }
      />
    </div>
  );
}
