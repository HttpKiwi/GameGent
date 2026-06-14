import { type ChangeEvent } from 'react';

interface NumberFieldProps {
  label?: string;
  value: number;
  min?: number;
  max?: number;
  onChange: (value: number) => void;
  disabled?: boolean;
}

export function NumberField({ label, value, min, max, onChange, disabled }: NumberFieldProps) {
  return (
    <div className={`setting-group ${disabled ? 'disabled' : ''}`}>
      {label && <label>{label}</label>}
      <input
        type="number"
        min={min}
        max={max}
        value={value}
        disabled={disabled}
        onChange={(e: ChangeEvent<HTMLInputElement>) =>
          onChange(parseInt(e.target.value) || 0)
        }
      />
    </div>
  );
}
