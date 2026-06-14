import { useState, useEffect } from 'react';
import { useConfigStore } from '../stores/configStore';
import { useRemap, useTurbo, useSaveConfig } from '../hooks/useApi';
import { SelectField, TextField, NumberField, CheckboxField, SettingCard } from '../components/ui';
import { BUTTON_OPTIONS } from './buttonOptions';

interface TurboSetting {
  target: string;
  rate: number;
  continuous: boolean;
}

const EMPTY_TURBO: TurboSetting = { target: '', rate: 10, continuous: false };

const BUTTON_LABELS: Record<string, string> = Object.fromEntries(
  BUTTON_OPTIONS.map((o) => [o.value, o.label])
);

export function ButtonsTab() {
  const config = useConfigStore((s) => s.config);
  const remap = useRemap();
  const turbo = useTurbo();
  const saveConfig = useSaveConfig();

  const [button, setButton] = useState<string>('');
  const [target, setTarget] = useState('');
  const [rate, setRate] = useState(10);
  const [continuous, setContinuous] = useState(false);
  const [turboEnabled, setTurboEnabled] = useState(false);

  useEffect(() => {
    if (!button) return;
    const currentMapping = config.key_mappings?.[button] ?? '';
    const turboSetting = config.turbo_settings?.[button] as TurboSetting | undefined;
    setTarget(currentMapping);
    setRate(turboSetting?.rate ?? 10);
    setContinuous(turboSetting?.continuous ?? false);
    setTurboEnabled(!!turboSetting);
  }, [button, config.key_mappings, config.turbo_settings]);

  const handleApply = async () => {
    if (!button) return;

    const turboSetting: TurboSetting = { target, rate, continuous };

    const newMappings = { ...(config.key_mappings ?? {}) };
    if (target) {
      newMappings[button] = target;
    } else {
      delete newMappings[button];
    }

    const newTurboSettings = { ...(config.turbo_settings ?? {}) };
    if (turboEnabled && (rate !== 10 || continuous || target)) {
      newTurboSettings[button] = turboSetting;
    } else {
      delete newTurboSettings[button];
    }

    const newConfig = {
      ...config,
      key_mappings: newMappings,
      turbo_settings: newTurboSettings,
    };

    if (target) {
      await remap.mutateAsync({ button, target });
    }

    if (turboEnabled) {
      await turbo.mutateAsync({ button, target: target || 'controller:a', rate, continuous });
    }

    await saveConfig.mutateAsync(newConfig);
  };

  const handleDelete = async () => {
    if (!button) return;

    const newMappings = { ...(config.key_mappings ?? {}) };
    delete newMappings[button];

    const newTurboSettings = { ...(config.turbo_settings ?? {}) };
    delete newTurboSettings[button];

    await remap.mutateAsync({ button, target: 'unbind' });
    await saveConfig.mutateAsync({
      ...config,
      key_mappings: newMappings,
      turbo_settings: newTurboSettings,
    });

    setTarget('');
    setRate(10);
    setContinuous(false);
  };

  const mappings = Object.entries(config.key_mappings ?? {});

  return (
    <div>
      <h2>Button Configuration</h2>
      <div className="setting-grid">
        <SettingCard title="Button Settings" span={2}>
          <div className="card-row">
            <SelectField
              label="Button"
              value={button}
              options={BUTTON_OPTIONS}
              onChange={setButton}
            />
            <TextField
              label="Remap Target"
              value={target}
              placeholder="e.g., key:enter, controller:a, mouse:left_click"
              onChange={setTarget}
            />
          </div>
          <CheckboxField label="Turbo" checked={turboEnabled} onChange={setTurboEnabled} />
          <div className={`card-row ${!turboEnabled ? 'disabled' : ''}`}>
            <NumberField label="Turbo Rate (Hz)" value={rate} min={1} max={100} onChange={setRate} disabled={!turboEnabled} />
            <CheckboxField label="Continuous" checked={continuous} onChange={setContinuous} disabled={!turboEnabled} />
          </div>
          <div className="button-row">
            <button className="form-btn" onClick={handleApply} disabled={!button}>
              Apply
            </button>
            <button className="form-btn form-btn-danger" onClick={handleDelete} disabled={!button}>
              Clear
            </button>
          </div>
        </SettingCard>
      </div>

      <div className="mappings-card">
        <h3>Current Mappings</h3>
        {mappings.length === 0 ? (
          <p className="mappings-empty">No remappings configured</p>
        ) : (
          <div className="mappings-list">
            {mappings.map(([btn, tgt]) => {
              const turboData = (config.turbo_settings?.[btn] as TurboSetting) ?? null;
              return (
                <div
                  key={btn}
                  className={`mapping-row ${button === btn ? 'active' : ''}`}
                  onClick={() => setButton(btn)}
                >
                  <span className="mapping-source">{BUTTON_LABELS[btn] || btn}</span>
                  <span className="mapping-arrow">→</span>
                  <code className="mapping-target">{tgt}</code>
                  {turboData && (
                    <span className="mapping-turbo">
                      {turboData.rate}Hz{turboData.continuous ? ' cont' : ''}
                    </span>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
