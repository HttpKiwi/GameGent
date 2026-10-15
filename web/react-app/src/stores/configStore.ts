import { create } from 'zustand';
import type { GameGentConfig } from '../types/config';

const generateHash = (config: GameGentConfig): string =>
  JSON.stringify(config);

interface ConfigState {
  config: GameGentConfig;
  lastHash: string;
  isDirty: boolean;
  setConfig: (config: GameGentConfig) => void;
  setConfigFromServer: (config: GameGentConfig) => void;
  replaceConfig: (config: GameGentConfig) => void;
  setKeyMappingsFromDevice: (key_mappings: Record<string, string>, turbo_settings?: Record<string, unknown>) => void;
  updateConfig: (updates: Partial<GameGentConfig>) => void;
  setDirty: (dirty: boolean) => void;
}

export const useConfigStore = create<ConfigState>((set, get) => ({
  config: {},
  lastHash: '',
  isDirty: false,

  setConfig: (config) => {
    set({ config, lastHash: generateHash(config), isDirty: true });
  },

  setConfigFromServer: (config) => {
    if (get().isDirty) return;
    set({ config, lastHash: generateHash(config) });
  },

  replaceConfig: (config) => {
    set({ config, lastHash: generateHash(config), isDirty: false });
  },

  setKeyMappingsFromDevice: (key_mappings, turbo_settings) => {
    if (get().isDirty) return;
    const current = get().config;
    const sameMaps =
      JSON.stringify(current.key_mappings ?? {}) === JSON.stringify(key_mappings);
    const sameTurbo =
      turbo_settings === undefined ||
      JSON.stringify(current.turbo_settings ?? {}) === JSON.stringify(turbo_settings);
    if (sameMaps && sameTurbo) {
      return;
    }
    const config = {
      ...current,
      key_mappings,
      ...(turbo_settings !== undefined ? { turbo_settings } : {}),
    };
    set({ config, lastHash: generateHash(config) });
  },

  updateConfig: (updates) => {
    const current = get().config;
    const merged = { ...current, ...updates };
    set({ config: merged, lastHash: generateHash(merged), isDirty: true });
  },

  setDirty: (dirty) => {
    set({ isDirty: dirty });
  },
}));
