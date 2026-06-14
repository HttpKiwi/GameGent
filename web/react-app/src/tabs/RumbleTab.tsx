import { useState } from 'react';
import { useRumbleLevel, useFireRumble } from '../hooks/useApi';
import { RangeSlider, NumberField, SettingCard } from '../components/ui';

export function RumbleTab() {
  const rumbleLevel = useRumbleLevel();
  const fireRumble = useFireRumble();

  const [leftLevel, setLeftLevel] = useState(0);
  const [rightLevel, setRightLevel] = useState(0);
  const [fireLeft, setFireLeft] = useState(100);
  const [fireRight, setFireRight] = useState(100);
  const [duration, setDuration] = useState(500);

  return (
    <div>
      <h2>Rumble</h2>
      <div className="setting-grid">
        <SettingCard title="Rumble Level" span={2}>
          <div className="card-row">
            <RangeSlider label="Left" value={leftLevel} min={0} max={100} onChange={setLeftLevel} />
            <RangeSlider label="Right" value={rightLevel} min={0} max={100} onChange={setRightLevel} />
          </div>
          <button className="save-btn" onClick={() => rumbleLevel.mutateAsync({ pct: leftLevel, right: rightLevel })}>
            Set Rumble Level
          </button>
        </SettingCard>

        <SettingCard title="Fire Rumble" span={2}>
          <div className="card-row">
            <RangeSlider label="Left Fire" value={fireLeft} min={0} max={100} onChange={setFireLeft} />
            <RangeSlider label="Right Fire" value={fireRight} min={0} max={100} onChange={setFireRight} />
          </div>
          <NumberField label="Duration (ms)" value={duration} min={100} max={5000} onChange={setDuration} />
          <button className="save-btn" onClick={() => fireRumble.mutateAsync({ fire: fireLeft, fire_right: fireRight, duration })}>
            Fire Rumble
          </button>
        </SettingCard>
      </div>
    </div>
  );
}
