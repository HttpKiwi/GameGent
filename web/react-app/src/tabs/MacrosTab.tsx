import { useState } from 'react';
import { useMacro } from '../hooks/useApi';
import { SelectField, TextAreaField, CheckboxField, SettingCard } from '../components/ui';
import { BUTTON_OPTIONS } from './buttonOptions';

export function MacrosTab() {
  const macro = useMacro();

  const [button, setButton] = useState('l4');
  const [stepsText, setStepsText] = useState('');
  const [hold, setHold] = useState(false);
  const [loop, setLoop] = useState(false);

  const handleApply = async () => {
    const steps = stepsText.split('\n').filter((s) => s.trim());
    await macro.mutateAsync({ button, steps, hold, loop });
    setStepsText('');
  };

  return (
    <div>
      <h2>Macros</h2>
      <div className="setting-grid">
        <SettingCard title="Macro Setup" span={2}>
          <SelectField label="Source Button" value={button} options={BUTTON_OPTIONS} onChange={setButton} />
          <TextAreaField
            label="Macro Steps (target:press_ms:release_ms, max 12)"
            value={stepsText}
            placeholder="e.g., lb:0:50 (one step per line); key:a:0:50 or mouse:left_click:0:50 for keys/mouse"
            onChange={setStepsText}
          />
          <div className="card-row">
            <CheckboxField label="Hold to Fire" checked={hold} onChange={setHold} />
            <CheckboxField label="Loop" checked={loop} onChange={setLoop} />
          </div>
          <button className="save-btn" onClick={handleApply}>Apply Macro</button>
        </SettingCard>
      </div>
    </div>
  );
}
