import type { ReactNode } from 'react';

interface SettingCardProps {
  title: string;
  children: ReactNode;
  span?: 1 | 2;
}

export function SettingCard({ title, children, span = 1 }: SettingCardProps) {
  return (
    <div className={`setting-card card-span-${span}`}>
      <h3>{title}</h3>
      <div className="card-body">{children}</div>
    </div>
  );
}
