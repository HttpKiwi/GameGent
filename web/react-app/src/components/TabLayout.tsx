import { useState, type ReactNode } from 'react';

interface Tab {
  id: string;
  label: string;
  content: ReactNode;
}

interface TabLayoutProps {
  tabs: Tab[];
}

export function TabLayout({ tabs }: TabLayoutProps) {
  const [activeTab, setActiveTab] = useState(tabs[0]?.id ?? '');

  return (
    <div>
      <nav className="tabs">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            className={`tab-btn ${activeTab === tab.id ? 'active' : ''}`}
            onClick={() => setActiveTab(tab.id)}
          >
            {tab.label}
          </button>
        ))}
      </nav>
      <main className="tab-content">
        {tabs.map((tab) => (
          <div
            key={tab.id}
            className={`tab-pane ${activeTab === tab.id ? 'active' : ''}`}
          >
            {tab.content}
          </div>
        ))}
      </main>
    </div>
  );
}
