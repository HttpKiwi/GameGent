import { type ChangeEvent } from 'react';

interface TextAreaFieldProps {
  label?: string;
  value: string;
  placeholder?: string;
  rows?: number;
  onChange: (value: string) => void;
}

export function TextAreaField({
  label,
  value,
  placeholder,
  rows = 5,
  onChange,
}: TextAreaFieldProps) {
  return (
    <div className="setting-group">
      {label && <label>{label}</label>}
      <textarea
        rows={rows}
        value={value}
        placeholder={placeholder}
        onChange={(e: ChangeEvent<HTMLTextAreaElement>) => onChange(e.target.value)}
      />
    </div>
  );
}
