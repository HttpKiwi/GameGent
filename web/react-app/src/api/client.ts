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

export interface DeviceStatus {
  connected: boolean;
  path: string | null;
}

export async function getDeviceStatus(): Promise<DeviceStatus> {
  return apiCall('/status');
}

export async function fetchConfig(): Promise<Record<string, unknown>> {
  return apiCall('/config');
}

export async function saveConfig(config: Record<string, unknown>): Promise<void> {
  await apiCall('/config', { method: 'POST', data: config });
}

export async function applyConfig(config?: Record<string, unknown>): Promise<{
  applied: Record<string, string>;
}> {
  return apiCall('/config/apply', {
    method: 'POST',
    data: config ? { config } : {},
  });
}

export interface ProfileInfo {
  name: string;
  updated_at: string | null;
  active: boolean;
}

export async function listProfiles(): Promise<{
  profiles: ProfileInfo[];
  active: string | null;
}> {
  return apiCall('/profiles');
}

export async function saveProfile(data: {
  name: string;
  config?: Record<string, unknown>;
  make_active?: boolean;
}): Promise<{ name: string; active: string | null }> {
  return apiCall('/profiles', { method: 'POST', data });
}

export async function activateProfile(data: {
  name: string;
  apply?: boolean;
}): Promise<{
  name: string;
  active: string | null;
  config: Record<string, unknown>;
  applied: Record<string, string> | null;
}> {
  return apiCall('/profiles/activate', { method: 'POST', data });
}

export async function deleteProfile(name: string): Promise<{ active: string | null }> {
  return apiCall(`/profiles/${encodeURIComponent(name)}`, { method: 'DELETE' });
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

export async function readDeviceMappings(sync = false): Promise<{ key_mappings: Record<string, string> }> {
  return apiCall('/mappings/read', { method: 'POST', data: { sync } });
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
