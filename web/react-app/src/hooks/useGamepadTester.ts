import { useEffect, useState } from 'react';
import { apiCall } from '../api/client';

export interface BackendGamepadState {
  connected: boolean;
  id: string | null;
  path?: string;
  pressed: string[];
  leftStick: { x: number; y: number };
  rightStick: { x: number; y: number };
  lt: number;
  rt: number;
  axes: number[];
  buttons: number[];
  layout?: string;
  error?: string;
}

const EMPTY: BackendGamepadState = {
  connected: false,
  id: null,
  pressed: [],
  leftStick: { x: 0, y: 0 },
  rightStick: { x: 0, y: 0 },
  lt: 0,
  rt: 0,
  axes: [],
  buttons: [],
};

function sameState(a: BackendGamepadState, b: BackendGamepadState): boolean {
  return (
    a.connected === b.connected &&
    a.id === b.id &&
    a.lt === b.lt &&
    a.rt === b.rt &&
    a.leftStick.x === b.leftStick.x &&
    a.leftStick.y === b.leftStick.y &&
    a.rightStick.x === b.rightStick.x &&
    a.rightStick.y === b.rightStick.y &&
    a.pressed.join(',') === b.pressed.join(',')
  );
}

/**
 * Poll Flask /api/gamepad — reliable on Linux where WebKitGTK's Gamepad API
 * folds trigger/hat axes into stick axes and may pick mouse passthrough first.
 */
export function useGamepadTester(intervalMs = 16): BackendGamepadState {
  const [state, setState] = useState<BackendGamepadState>(EMPTY);

  useEffect(() => {
    let cancelled = false;
    let timer = 0;

    const tick = async () => {
      try {
        const next = await apiCall<BackendGamepadState>('/gamepad');
        if (!cancelled) {
          setState((prev) => (sameState(prev, next) ? prev : next));
        }
      } catch {
        if (!cancelled) {
          setState((prev) => (prev.connected ? EMPTY : prev));
        }
      } finally {
        if (!cancelled) {
          timer = window.setTimeout(tick, intervalMs);
        }
      }
    };

    tick();
    return () => {
      cancelled = true;
      window.clearTimeout(timer);
    };
  }, [intervalMs]);

  return state;
}
