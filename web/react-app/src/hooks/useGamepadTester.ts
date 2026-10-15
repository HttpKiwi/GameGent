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
  /** 'vendor' = dongle state report (all physical buttons), 'js' = Linux joystick API */
  source?: 'vendor' | 'js';
  raw?: string;
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
    a.source === b.source &&
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
 * Live controller state. Prefers one server-sent-events connection (/api/gamepad/stream), which
 * the server pushes to on every change; falls back to polling /api/gamepad if the stream fails.
 * (WebKitGTK's Gamepad API folds trigger/hat axes into stick axes, hence the backend.)
 */
export function useGamepadTester(pollMs = 33): BackendGamepadState {
  const [state, setState] = useState<BackendGamepadState>(EMPTY);

  useEffect(() => {
    let cancelled = false;
    let timer = 0;
    let frame = 0;
    let source: EventSource | null = null;
    let latest: BackendGamepadState | null = null;

    const apply = (next: BackendGamepadState) => {
      // at most one React update per animation frame
      latest = next;
      if (!frame) {
        frame = window.requestAnimationFrame(() => {
          frame = 0;
          const value = latest;
          if (!cancelled && value) setState((prev) => (sameState(prev, value) ? prev : value));
        });
      }
    };

    const poll = async () => {
      try {
        apply(await apiCall<BackendGamepadState>('/gamepad'));
      } catch {
        if (!cancelled) setState((prev) => (prev.connected ? EMPTY : prev));
      } finally {
        if (!cancelled) timer = window.setTimeout(poll, pollMs);
      }
    };

    if (typeof EventSource === 'undefined') {
      poll();
    } else {
      source = new EventSource('/api/gamepad/stream');
      source.onmessage = (event) => apply(JSON.parse(event.data) as BackendGamepadState);
      source.onerror = () => {
        // stream unavailable: close it and poll instead
        source?.close();
        source = null;
        if (!cancelled && !timer) poll();
      };
    }

    return () => {
      cancelled = true;
      source?.close();
      window.clearTimeout(timer);
      window.cancelAnimationFrame(frame);
    };
  }, [pollMs]);

  return state;
}
