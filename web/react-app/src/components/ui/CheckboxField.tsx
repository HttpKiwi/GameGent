import { type ChangeEvent } from 'react';

interface CheckboxFieldProps {
  label?: string;
  checked: boolean;
  onChange: (checked: boolean) => void;
  disabled?: boolean;
}

export function CheckboxField({ label, checked, onChange, disabled }: CheckboxFieldProps) {
  return (
    <div className={`setting-group ${disabled ? 'disabled' : ''}`}>
      {label && <label>{label}</label>}
      <input
        type="checkbox"
        checked={checked}
        disabled={disabled}
        onChange={(e: ChangeEvent<HTMLInputElement>) => onChange(e.target.checked)}
      />
    </div>
  );
}
