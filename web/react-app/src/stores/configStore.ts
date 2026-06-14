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

  updateConfig: (updates) => {
    const current = get().config;
    const merged = { ...current, ...updates };
    set({ config: merged, lastHash: generateHash(merged), isDirty: true });
  },

  setDirty: (dirty) => {
    set({ isDirty: dirty });
  },
}));
