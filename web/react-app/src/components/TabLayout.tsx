import { useState, type ReactNode } from 'react';
import { LiveGamepadTester } from './LiveGamepadTester';

export interface Tab {
  id: string;
  label: string;
  content: ReactNode;
  group?: string;
}

interface TabLayoutProps {
  tabs: Tab[];
}

const TAB_GROUPS = [
  { id: 'overview', label: 'Overview' },
  { id: 'appearance', label: 'Appearance' },
  { id: 'controls', label: 'Controls' },
  { id: 'advanced', label: 'Advanced' },
];

export function TabLayout({ tabs }: TabLayoutProps) {
  const [activeTab, setActiveTab] = useState(tabs[0]?.id ?? '');

  const activeContent = tabs.find((t) => t.id === activeTab)?.content;

  return (
    <div className="app-layout">
      <aside className="sidebar">
        <nav className="sidebar-nav">
          {TAB_GROUPS.map((group) => {
            const groupTabs = tabs.filter((t) => t.group === group.id);
            if (groupTabs.length === 0) return null;

            return (
              <div key={group.id} className="sidebar-group">
                <span className="sidebar-group-label">{group.label}</span>
                {groupTabs.map((tab) => (
                  <button
                    key={tab.id}
                    className={`sidebar-btn ${activeTab === tab.id ? 'active' : ''}`}
                    onClick={() => setActiveTab(tab.id)}
                  >
                    {tab.label}
                  </button>
                ))}
              </div>
            );
          })}
        </nav>
      </aside>

      <div className={`content-layout ${activeTab === 'buttons' ? 'content-layout--wide' : ''}`}>
        <main className="main-content">
          <div className="tab-pane active">{activeContent}</div>
        </main>
        {activeTab !== 'buttons' && <LiveGamepadTester />}
      </div>
    </div>
  );
}
