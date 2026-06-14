import type { ReactNode } from 'react';

interface SettingGroupProps {
  label: string;
  children: ReactNode;
}

export function SettingGroup({ label, children }: SettingGroupProps) {
  return (
    <div className="setting-group">
      <label>{label}</label>
      {children}
    </div>
  );
}
