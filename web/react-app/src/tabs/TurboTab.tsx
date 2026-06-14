import { useState } from 'react';
import { useTurbo } from '../hooks/useApi';
import { SelectField, TextField, NumberField, CheckboxField, SettingCard } from '../components/ui';
import { BUTTON_OPTIONS } from './buttonOptions';

export function TurboTab() {
  const turbo = useTurbo();

  const [button, setButton] = useState('l4');
  const [target, setTarget] = useState('');
  const [rate, setRate] = useState(10);
  const [continuous, setContinuous] = useState(false);

  const handleApply = async () => {
    await turbo.mutateAsync({ button, target, rate, continuous });
  };

  return (
    <div>
      <h2>Turbo</h2>
      <div className="setting-grid">
        <SettingCard title="Turbo Setup" span={2}>
          <div className="card-row">
            <SelectField label="Button" value={button} options={BUTTON_OPTIONS} onChange={setButton} />
            <NumberField label="Turbo Rate (Hz)" value={rate} min={1} max={100} onChange={setRate} />
          </div>
          <TextField label="Target" value={target} placeholder="e.g., key:enter, controller:a" onChange={setTarget} />
          <CheckboxField label="Continuous" checked={continuous} onChange={setContinuous} />
          <button className="save-btn" onClick={handleApply}>Apply Turbo</button>
        </SettingCard>
      </div>
    </div>
  );
}
