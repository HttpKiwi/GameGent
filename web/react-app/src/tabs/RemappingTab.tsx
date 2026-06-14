import { useState } from 'react';
import { useConfigStore } from '../stores/configStore';
import { useRemap, useUnmap, useSaveConfig } from '../hooks/useApi';
import { SelectField, TextField } from '../components/ui';
import { BUTTON_OPTIONS } from './buttonOptions';

const BUTTON_LABELS: Record<string, string> = Object.fromEntries(
  BUTTON_OPTIONS.map((o) => [o.value, o.label])
);

export function RemappingTab() {
  const config = useConfigStore((s) => s.config);
  const remap = useRemap();
  const unmap = useUnmap();
  const saveConfig = useSaveConfig();

  const [source, setSource] = useState('');
  const [target, setTarget] = useState('');

  const mappings = Object.entries(config.key_mappings ?? {});

  const handleApply = async () => {
    if (!source || !target) return;
    await remap.mutateAsync({ button: source, target });
    const updated = {
      ...config,
      key_mappings: { ...(config.key_mappings ?? {}), [source]: target },
    };
    await saveConfig.mutateAsync(updated);
    setSource('');
    setTarget('');
  };

  const handleDelete = async (button: string) => {
    await unmap.mutateAsync({ button });
    const updated = { ...(config.key_mappings ?? {}) };
    delete updated[button];
    await saveConfig.mutateAsync({ ...config, key_mappings: updated });
  };

  return (
    <div>
      <h2>Button Remapping</h2>
      <div className="remapping-container">
        <div className="controller-svg-container">
          <img src="/static/svg/controller.svg" alt="Controller" />
        </div>
        <div className="remapping-controls">
          <SelectField
            label="Source Button"
            value={source}
            options={BUTTON_OPTIONS}
            onChange={setSource}
          />
          <TextField
            label="Target"
            value={target}
            placeholder="e.g., key:enter, controller:a, mouse:left_click"
            onChange={setTarget}
          />
          <button className="save-btn" onClick={handleApply}>
            Apply Remap
          </button>
        </div>
      </div>

      <div className="mappings-card">
        <h3>Current Mappings</h3>
        {mappings.length === 0 ? (
          <p className="mappings-empty">No remappings configured</p>
        ) : (
          <div className="mappings-list">
            {mappings.map(([button, tgt]) => (
              <div key={button} className="mapping-row">
                <span className="mapping-source">{BUTTON_LABELS[button] || button}</span>
                <span className="mapping-arrow">→</span>
                <code className="mapping-target">{tgt}</code>
                <button
                  className="mapping-delete-btn"
                  onClick={() => handleDelete(button)}
                  title="Remove mapping"
                >
                  ×
                </button>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
