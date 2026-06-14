import { type ChangeEvent } from 'react';

interface CheckboxFieldProps {
  label?: string;
  checked: boolean;
  onChange: (checked: boolean) => void;
}

export function CheckboxField({ label, checked, onChange }: CheckboxFieldProps) {
  return (
    <div className="setting-group">
      {label && <label>{label}</label>}
      <input
        type="checkbox"
        checked={checked}
        onChange={(e: ChangeEvent<HTMLInputElement>) => onChange(e.target.checked)}
      />
    </div>
  );
}
