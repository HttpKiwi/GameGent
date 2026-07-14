/** Clickable regions mapped to the controller.svg viewBox (460.79 × 284.14). */
export interface ControllerZone {
  id: string;
  cx: number;
  cy: number;
  r: number;
  label: string;
  face?: boolean;
  /** Back paddle — rendered as a gray square below the diagram */
  rear?: boolean;
}

export const CONTROLLER_VIEWBOX = { width: 460.79, height: 284.14 };

export const CONTROLLER_BUTTON_ZONES: ControllerZone[] = [
  // Face buttons
  { id: 'y', cx: 369, cy: 50, r: 14, label: 'Y', face: true },
  { id: 'b', cx: 397, cy: 78, r: 14, label: 'B', face: true },
  { id: 'x', cx: 340, cy: 78, r: 14, label: 'X', face: true },
  { id: 'a', cx: 369, cy: 106, r: 14, label: 'A', face: true },
  // Sticks
  { id: 'l3', cx: 160.4, cy: 135.8, r: 22, label: 'L3' },
  { id: 'r3', cx: 301.3, cy: 135.8, r: 22, label: 'R3' },
  // D-pad
  { id: 'dpad_up', cx: 92, cy: 55, r: 14, label: '↑' },
  { id: 'dpad_down', cx: 92, cy: 100, r: 14, label: '↓' },
  { id: 'dpad_left', cx: 70, cy: 78, r: 14, label: '←' },
  { id: 'dpad_right', cx: 118, cy: 78, r: 14, label: '→' },
  // Bumpers & triggers
  { id: 'lb', cx: 115, cy: 11, r: 8, label: 'LB' },
  { id: 'rb', cx: 345, cy: 11, r: 8, label: 'RB' },
  { id: 'lt', cx: 80, cy: 5, r: 6, label: 'LT' },
  { id: 'rt', cx: 380, cy: 5, r: 6, label: 'RT' },
  // Center
  { id: 'back', cx: 206, cy: 73, r: 8, label: 'Back' },
  { id: 'start', cx: 255, cy: 73, r: 8, label: 'Start' },
  { id: 'screenshot', cx: 230, cy: 73, r: 8, label: 'Shot' },
  // Back paddles (rear — shown as gray squares below sticks)
  { id: 'l4', cx: 160.4, cy: 225, r: 22, label: 'L4', rear: true },
  { id: 'r4', cx: 301.3, cy: 225, r: 22, label: 'R4', rear: true },
  // Grip buttons
  { id: 'c1', cx: 145, cy: 38, r: 8, label: 'C1' },
  { id: 'c2', cx: 175, cy: 58, r: 8, label: 'C2' },
  { id: 'c3', cx: 288, cy: 58, r: 8, label: 'C3' },
  { id: 'c4', cx: 316, cy: 38, r: 8, label: 'C4' },
  { id: 't1', cx: 160, cy: 14, r: 12, label: 'T1' },
  { id: 't2', cx: 300, cy: 14, r: 16, label: 'T2' },
  { id: 't3', cx: 230, cy: 30, r: 12, label: 'T3' },
];

const FACE_COLORS: Record<string, string> = {
  a: '#7fba00',
  b: '#f25022',
  x: '#00a4ef',
  y: '#ffb900',
};

export function getFaceColor(buttonId: string): string | undefined {
  return FACE_COLORS[buttonId];
}
