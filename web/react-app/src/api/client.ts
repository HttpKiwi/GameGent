interface ApiCallOptions {
  method?: string;
  data?: unknown;
}

export async function apiCall<T = unknown>(
  endpoint: string,
  options: ApiCallOptions = {}
): Promise<T> {
  const { method = 'GET', data } = options;

  const fetchOptions: RequestInit = {
    method,
    headers: { 'Content-Type': 'application/json' },
  };

  if (data) {
    fetchOptions.body = JSON.stringify(data);
  }

  const response = await fetch(`/api${endpoint}`, fetchOptions);
  const result = await response.json();

  if (!response.ok) {
    throw new Error(result.error || 'Unknown error');
  }

  return result as T;
}

export async function fetchConfig(): Promise<Record<string, unknown>> {
  return apiCall('/config');
}

export async function saveConfig(config: Record<string, unknown>): Promise<void> {
  await apiCall('/config', { method: 'POST', data: config });
}

export async function setLighting(data: {
  mode: string;
  brightness: number;
  speed: number;
}): Promise<void> {
  await apiCall('/lighting', { method: 'POST', data });
}

export async function setLED(data: {
  target: string;
  hue: number;
  saturation: number;
  lightness: number;
}): Promise<void> {
  await apiCall('/led', { method: 'POST', data });
}

export async function setLayout(data: { layout: string }): Promise<void> {
  await apiCall('/layout', { method: 'POST', data });
}

export async function setFaceColors(data: {
  button: string;
  a_hue: number;
  a_sat: number;
  a_light: number;
  b_hue: number;
  b_sat: number;
  b_light: number;
  x_hue: number;
  x_sat: number;
  x_light: number;
  y_hue: number;
  y_sat: number;
  y_light: number;
}): Promise<void> {
  await apiCall('/face', { method: 'POST', data });
}

export async function setTriggers(data: Record<string, unknown>): Promise<void> {
  await apiCall('/trigger', { method: 'POST', data });
}

export async function setSticks(data: {
  left: Record<string, unknown>;
  right: Record<string, unknown>;
}): Promise<void> {
  await apiCall('/stick', { method: 'POST', data });
}

export async function setGyro(data: Record<string, unknown>): Promise<void> {
  await apiCall('/gyro', { method: 'POST', data });
}

export async function applyRemap(data: {
  button: string;
  target: string;
}): Promise<void> {
  await apiCall('/map', { method: 'POST', data });
}

export async function unmapRemap(data: { button: string }): Promise<void> {
  await apiCall('/map', { method: 'POST', data: { ...data, target: 'unbind' } });
}

export async function setTurbo(data: {
  button: string;
  target: string;
  rate: number;
  continuous: boolean;
}): Promise<void> {
  await apiCall('/turbo', { method: 'POST', data });
}

export async function setRumbleLevel(data: {
  pct: number;
  right: number;
}): Promise<void> {
  await apiCall('/rumble', { method: 'POST', data });
}

export async function fireRumble(data: {
  fire: number;
  fire_right: number;
  duration: number;
}): Promise<void> {
  await apiCall('/rumble', { method: 'POST', data });
}

export async function setCombo(data: {
  button: string;
  keys: string[];
}): Promise<void> {
  await apiCall('/combo', { method: 'POST', data });
}

export async function setMacro(data: {
  button: string;
  steps: string[];
  hold: boolean;
  loop: boolean;
}): Promise<void> {
  await apiCall('/macro', { method: 'POST', data });
}
