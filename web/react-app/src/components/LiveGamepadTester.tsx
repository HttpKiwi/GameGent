import { ControllerDiagram } from './ControllerDiagram';
import { useGamepadTester } from '../hooks/useGamepadTester';

function StickReadout({ label, x, y }: { label: string; x: number; y: number }) {
  const safeX = Math.max(-1, Math.min(1, x));
  const safeY = Math.max(-1, Math.min(1, y));

  return (
    <div className="live-tester__stick">
      <span>{label}</span>
      <div className="live-tester__stick-field">
        <i
          style={{
            left: `${50 + safeX * 42}%`,
            top: `${50 + safeY * 42}%`,
          }}
        />
      </div>
      <small>{safeX.toFixed(2)}, {safeY.toFixed(2)}</small>
    </div>
  );
}

export function LiveGamepadTester() {
  const gamepad = useGamepadTester();
  const activeButtons = new Set(gamepad.pressed);

  return (
    <aside className="live-tester" aria-label="Live controller tester">
      <div className="live-tester__header">
        <div>
          <h2>Live tester</h2>
          <p>{gamepad.connected ? 'Controller input' : 'Waiting for pad…'}</p>
        </div>
        <span className={`live-tester__status ${gamepad.connected ? 'is-connected' : ''}`} />
      </div>

      {gamepad.connected ? (
        <>
          <div className="live-tester__diagram">
            <ControllerDiagram
              activeButtons={activeButtons}
              onButtonClick={() => undefined}
            />
          </div>

          <div className="live-tester__sticks">
            <StickReadout label="Left" x={gamepad.leftStick.x} y={gamepad.leftStick.y} />
            <StickReadout label="Right" x={gamepad.rightStick.x} y={gamepad.rightStick.y} />
          </div>

          <div className="live-tester__triggers">
            <label>
              <span>LT</span>
              <div className="live-tester__meter" aria-hidden>
                <i style={{ transform: `scaleX(${Math.max(0, Math.min(1, gamepad.lt))})` }} />
              </div>
              <small>{gamepad.lt.toFixed(2)}</small>
            </label>
            <label>
              <span>RT</span>
              <div className="live-tester__meter" aria-hidden>
                <i style={{ transform: `scaleX(${Math.max(0, Math.min(1, gamepad.rt))})` }} />
              </div>
              <small>{gamepad.rt.toFixed(2)}</small>
            </label>
          </div>

          <p className="live-tester__device" title={gamepad.id ?? undefined}>
            {gamepad.id}
          </p>
        </>
      ) : (
        <div className="live-tester__empty">
          <p>No Linux joystick found (or permission denied on /dev/input/js*).</p>
        </div>
      )}
    </aside>
  );
}
