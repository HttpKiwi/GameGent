import { useState } from 'react';
import { useCombo } from '../hooks/useApi';
import { SelectField, TextField, SettingCard } from '../components/ui';
import { BUTTON_OPTIONS } from './buttonOptions';

export function CombosTab() {
  const combo = useCombo();

  const [button, setButton] = useState('l4');
  const [keysText, setKeysText] = useState('');

  const handleApply = async () => {
    const keys = keysText.split(' ').filter((k) => k);
    if (keys.length < 2 || keys.length > 3) {
      alert('Combo requires 2 or 3 keys');
      return;
    }
    await combo.mutateAsync({ button, keys });
    setKeysText('');
  };

  return (
    <div>
      <h2>Combos</h2>
      <div className="setting-grid">
        <SettingCard title="Combo Setup" span={2}>
          <SelectField label="Source Button" value={button} options={BUTTON_OPTIONS} onChange={setButton} />
          <TextField
            label="Combo Keys (2 or 3)"
            value={keysText}
            placeholder="e.g., controller:x controller:y"
            onChange={setKeysText}
          />
          <button className="save-btn" onClick={handleApply}>Apply Combo</button>
        </SettingCard>
      </div>
    </div>
  );
}
