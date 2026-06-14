import { type ChangeEvent } from 'react';

interface TextFieldProps {
  label?: string;
  value: string;
  placeholder?: string;
  onChange: (value: string) => void;
}

export function TextField({ label, value, placeholder, onChange }: TextFieldProps) {
  return (
    <div className="setting-group">
      {label && <label>{label}</label>}
      <input
        type="text"
        value={value}
        placeholder={placeholder}
        onChange={(e: ChangeEvent<HTMLInputElement>) => onChange(e.target.value)}
      />
    </div>
  );
}
