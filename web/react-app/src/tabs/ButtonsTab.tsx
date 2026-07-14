import { useState } from 'react';
import { useConfigStore } from '../stores/configStore';
import { useRemap, useTurbo, useSaveConfig, useReadDeviceMappings } from '../hooks/useApi';
import { SelectField, TextField, NumberField, CheckboxField, SettingCard } from '../components/ui';
import { ControllerDiagram } from '../components/ControllerDiagram';
import { BUTTON_OPTIONS } from './buttonOptions';

interface TurboSetting {
  target: string;
  rate: number;
  continuous: boolean;
}

const BUTTON_LABELS: Record<string, string> = Object.fromEntries(
  BUTTON_OPTIONS.map((o) => [o.value, o.label])
);

export function ButtonsTab() {
  const config = useConfigStore((s) => s.config);
  const remap = useRemap();
  const turbo = useTurbo();
  const saveConfig = useSaveConfig();
  const readDeviceMappings = useReadDeviceMappings();

  const [button, setButton] = useState<string>('');
  const [target, setTarget] = useState('');
  const [rate, setRate] = useState(10);
  const [continuous, setContinuous] = useState(false);
  const [turboEnabled, setTurboEnabled] = useState(false);
  const [showAllZones, setShowAllZones] = useState(false);

  const selectButton = (btn: string) => {
    setButton(btn);
    if (!btn) {
      setTarget('');
      setRate(10);
      setContinuous(false);
      setTurboEnabled(false);
      return;
    }
    const currentMapping = config.key_mappings?.[btn] ?? '';
    const turboSetting = config.turbo_settings?.[btn] as TurboSetting | undefined;
    setTarget(currentMapping);
    setRate(turboSetting?.rate ?? 10);
    setContinuous(turboSetting?.continuous ?? false);
    setTurboEnabled(!!turboSetting);
  };

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
    setTurboEnabled(false);
  };

  const mappings = Object.entries(config.key_mappings ?? {});
  const isApplying = remap.isPending || turbo.isPending || saveConfig.isPending;
  const isReading = readDeviceMappings.isPending;

  const handlePullFromDevice = async (sync: boolean) => {
    await readDeviceMappings.mutateAsync(sync);
    if (button) {
      const latest = useConfigStore.getState().config;
      const currentMapping = latest.key_mappings?.[button] ?? '';
      setTarget(currentMapping);
    }
  };

  return (
    <div className="buttons-tab">
      <div className="page-header">
        <h2>Button Remapping</h2>
        <p className="page-description">
          Click any button on the controller diagram to select it, then set a remap target below.
        </p>
      </div>

      <div className="remapping-layout">
        <div className="remapping-diagram">
          <div className="diagram-toolbar">
            <label className="calibrate-toggle">
              <input
                type="checkbox"
                checked={showAllZones}
                onChange={(e) => setShowAllZones(e.target.checked)}
              />
              Show all zone overlays
            </label>
          </div>
          <ControllerDiagram
            selectedButton={button}
            mappings={config.key_mappings ?? {}}
            onButtonClick={selectButton}
            showAllZones={showAllZones}
          />
          <div className="diagram-legend">
            <span className="legend-item legend-item--selected">Selected</span>
            <span className="legend-item legend-item--mapped">Remapped</span>
          </div>
        </div>

        <div className="remapping-panel">
          <SettingCard title="Remap Settings">
            <SelectField
              label="Button"
              value={button}
              options={[{ value: '', label: '— Select a button —' }, ...BUTTON_OPTIONS]}
              onChange={selectButton}
            />
            <TextField
              label="Remap Target"
              value={target}
              placeholder="key:enter, controller:a, mouse:left_click"
              onChange={setTarget}
            />
            <p className="field-hint">
              Prefix with <code>key:</code>, <code>controller:</code>, or <code>mouse:</code>
            </p>
            <CheckboxField label="Turbo" checked={turboEnabled} onChange={setTurboEnabled} />
            <div className={`card-row ${!turboEnabled ? 'disabled' : ''}`}>
              <NumberField
                label="Turbo Rate (Hz)"
                value={rate}
                min={1}
                max={100}
                onChange={setRate}
                disabled={!turboEnabled}
              />
              <CheckboxField
                label="Continuous"
                checked={continuous}
                onChange={setContinuous}
                disabled={!turboEnabled}
              />
            </div>
            <div className="button-row">
              <button
                className="form-btn"
                onClick={handleApply}
                disabled={!button || isApplying}
              >
                {isApplying ? 'Applying…' : 'Apply'}
              </button>
              <button
                className="form-btn form-btn-danger"
                onClick={handleDelete}
                disabled={!button || isApplying}
              >
                Clear
              </button>
            </div>
          </SettingCard>
        </div>
      </div>

      <div className="mappings-card">
        <div className="mappings-card-header">
          <h3>Current Mappings</h3>
          <div className="mappings-card-actions">
            <button
              className="form-btn form-btn-secondary"
              onClick={() => handlePullFromDevice(false)}
              disabled={isReading || isApplying}
            >
              {isReading ? 'Reading…' : 'Pull from Device'}
            </button>
            <button
              className="form-btn form-btn-secondary"
              onClick={() => handlePullFromDevice(true)}
              disabled={isReading || isApplying}
              title="Read from controller and save to config file"
            >
              Pull &amp; Save
            </button>
          </div>
        </div>
        {mappings.length === 0 ? (
          <p className="mappings-empty">No remappings configured — click a button on the diagram to get started.</p>
        ) : (
          <div className="mappings-list">
            {mappings.map(([btn, tgt]) => {
              const turboData = (config.turbo_settings?.[btn] as TurboSetting) ?? null;
              return (
                <div
                  key={btn}
                  className={`mapping-row ${button === btn ? 'active' : ''}`}
                  onClick={() => selectButton(btn)}
                  role="button"
                  tabIndex={0}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' || e.key === ' ') {
                      e.preventDefault();
                      selectButton(btn);
                    }
                  }}
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
