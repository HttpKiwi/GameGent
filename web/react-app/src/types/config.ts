export interface TriggerConfig {
  hair_mode: string;
  hair_trigger_begin: number;
  hair_trigger_end: number;
  deadzone_begin: number;
  deadzone_end: number;
  antideadzone_begin: number;
  antideadzone_end: number;
  curve_preset: string;
  curve_intensity: number;
}

export interface StickConfig {
  mode: string;
  x_sensitivity: number;
  y_sensitivity: number;
  overlap_percent: number;
  mouse_x_dpi: number;
  mouse_y_dpi: number;
  is_circle: boolean;
  deadzone_min: number;
  antideadzone_min: number;
  deadzone_max: number;
  antideadzone_max: number;
  curve_preset: string;
  curve_intensity: number;
}

export interface GyroConfig {
  output_mode: string;
  motion_mode: string;
  axis_mode: string;
  activate_method: string;
  activate_button: string;
  x_sensitivity: number;
  y_sensitivity: number;
  overlap_percent: number;
  mouse_dpi: number;
  deadzone_min: number;
  deadzone_max: number;
  antideadzone_min: number;
  antideadzone_max: number;
  invert_x: boolean;
  invert_y: boolean;
  curve_preset: string;
  curve_intensity: number;
  kb_up: string;
  kb_down: string;
  kb_left: string;
  kb_right: string;
}

export type FaceLED = [number, number, number];

export type KeyMappings = Record<string, string>;

export interface GameGentConfig {
  lighting_mode?: string;
  brightness?: number;
  lighting_speed?: number;
  color_hue?: number;
  color_saturation?: number;
  color_lightness?: number;
  lighting_zone?: number;
  layout?: string;
  stick_left?: StickConfig;
  stick_right?: StickConfig;
  trigger_left?: TriggerConfig;
  trigger_right?: TriggerConfig;
  gyro?: GyroConfig;
  face_leds?: FaceLED[];
  home_led?: FaceLED;
  key_mappings?: KeyMappings;
  [key: string]: unknown;
}
