import { useEffect, useRef, useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import * as api from '../api/client';
import { useConfigStore } from '../stores/configStore';
import type { GameGentConfig } from '../types/config';

export function useDeviceStatus() {
  return useQuery({
    queryKey: ['device-status'],
    queryFn: api.getDeviceStatus,
    refetchInterval: 2000,
  });
}

export function useDeviceMappingsPoll(connected: boolean) {
  const setKeyMappingsFromDevice = useConfigStore((s) => s.setKeyMappingsFromDevice);

  const query = useQuery({
    queryKey: ['device-mappings'],
    queryFn: () => api.readDeviceMappings(false),
    enabled: connected,
    refetchInterval: 4000,
    retry: false,
  });

  useEffect(() => {
    if (query.data?.key_mappings) {
      setKeyMappingsFromDevice(query.data.key_mappings, query.data.turbo_settings);
    }
  }, [query.data, setKeyMappingsFromDevice]);

  return query;
}

export function useConfig() {
  const setConfigFromServer = useConfigStore((s) => s.setConfigFromServer);

  return useQuery({
    queryKey: ['config'],
    queryFn: async () => {
      const config = (await api.fetchConfig()) as GameGentConfig;
      setConfigFromServer(config);
      return config;
    },
  });
}

export function useSaveConfig() {
  const queryClient = useQueryClient();
  const setDirty = useConfigStore((s) => s.setDirty);

  return useMutation({
    mutationFn: (config: GameGentConfig) => api.saveConfig(config),
    onSuccess: () => {
      setDirty(false);
      queryClient.invalidateQueries({ queryKey: ['config'] });
    },
  });
}

export type AutoSaveState =
  | { status: 'idle' }
  | { status: 'saving' }
  | { status: 'saved'; profile: string | null; failed: string[] }
  | { status: 'error'; message: string };

/**
 * Saves every edit to the working config and the active profile and pushes the
 * changed sections to the controller, ~0.8s after the last change.
 */
export function useAutoSave(): AutoSaveState {
  const config = useConfigStore((s) => s.config);
  const isDirty = useConfigStore((s) => s.isDirty);
  const queryClient = useQueryClient();
  const { data: profiles } = useProfiles();
  const active = profiles?.active ?? null;
  const [state, setState] = useState<AutoSaveState>({ status: 'idle' });
  const chain = useRef<Promise<unknown>>(Promise.resolve());

  useEffect(() => {
    if (!isDirty) return;
    const timer = setTimeout(() => {
      // Serialize saves so an older request can't land after a newer one.
      chain.current = chain.current.then(async () => {
        setState({ status: 'saving' });
        try {
          const result = await api.autosaveConfig(config, active);
          // Only clear dirty if nothing was edited while the request was in flight.
          if (useConfigStore.getState().config === config) {
            useConfigStore.getState().setDirty(false);
          }
          const failed = Object.entries(result.applied)
            .filter(([, v]) => v !== 'ok' && v !== 'skipped' && !/^\d+ ok$/.test(v))
            .map(([k, v]) => `${k}: ${v}`);
          setState({ status: 'saved', profile: result.profile, failed });
          queryClient.invalidateQueries({ queryKey: ['profiles'] });
        } catch (err) {
          const message = err instanceof Error ? err.message : 'Save failed';
          if (message === 'active profile changed') {
            // Game auto-switch changed the profile under us: take the server's state.
            useConfigStore.getState().setDirty(false);
            queryClient.invalidateQueries({ queryKey: ['profiles'] });
            queryClient.invalidateQueries({ queryKey: ['config'] });
          }
          setState({ status: 'error', message });
        }
      });
    }, 800);
    return () => clearTimeout(timer);
  }, [config, isDirty, active, queryClient]);

  return state;
}

export function useProfiles() {
  return useQuery({
    queryKey: ['profiles'],
    queryFn: api.listProfiles,
  });
}

export function useGameRules() {
  return useQuery({
    queryKey: ['game-rules'],
    queryFn: api.fetchGameRules,
  });
}

export function useGameRulesStatus(enabled = true) {
  const queryClient = useQueryClient();
  const query = useQuery({
    queryKey: ['game-rules-status'],
    queryFn: api.fetchGameRulesStatus,
    enabled,
    refetchInterval: 2000,
  });

  useEffect(() => {
    if (!query.data?.last_applied_profile) return;
    // Auto-switch may have changed working config on the server.
    queryClient.invalidateQueries({ queryKey: ['profiles'] });
    queryClient.invalidateQueries({ queryKey: ['config'] });
  }, [query.data?.last_applied_profile, queryClient]);

  return query;
}

export function useSaveGameRules() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: api.GameRules) => api.saveGameRules(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['game-rules'] });
      queryClient.invalidateQueries({ queryKey: ['game-rules-status'] });
    },
  });
}

export function useSaveProfile() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: { name: string; config?: GameGentConfig; make_active?: boolean }) =>
      api.saveProfile(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['profiles'] });
    },
  });
}

export function useActivateProfile() {
  const queryClient = useQueryClient();
  const replaceConfig = useConfigStore((s) => s.replaceConfig);

  return useMutation({
    mutationFn: (data: { name: string; apply?: boolean }) => api.activateProfile(data),
    onSuccess: (result) => {
      replaceConfig(result.config as GameGentConfig);
      queryClient.invalidateQueries({ queryKey: ['profiles'] });
      queryClient.invalidateQueries({ queryKey: ['config'] });
    },
  });
}

export function useDeleteProfile() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (name: string) => api.deleteProfile(name),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['profiles'] });
    },
  });
}

export function useApplyConfig() {
  return useMutation({
    mutationFn: (config?: GameGentConfig) => api.applyConfig(config),
  });
}

function useGenericMutation<T>(
  mutationFn: (data: T) => Promise<void>,
  options?: { successMessage?: string }
) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['config'] });
      if (options?.successMessage) {
        console.log(options.successMessage);
      }
    },
  });
}

export function useLighting() {
  return useGenericMutation(api.setLighting);
}

export function useLED() {
  return useGenericMutation(api.setLED);
}

export function useLayout() {
  return useGenericMutation(api.setLayout);
}

export function useFaceColors() {
  return useGenericMutation(api.setFaceColors);
}

export function useTriggers() {
  return useGenericMutation(api.setTriggers);
}

export function useSticks() {
  return useGenericMutation(api.setSticks);
}

export function useGyro() {
  return useGenericMutation(api.setGyro);
}

export function useRemap() {
  return useGenericMutation(api.applyRemap);
}

export function useReadDeviceMappings() {
  const queryClient = useQueryClient();
  const setConfig = useConfigStore((s) => s.setConfig);
  const setDirty = useConfigStore((s) => s.setDirty);

  return useMutation({
    mutationFn: (sync: boolean = false) => api.readDeviceMappings(sync),
    onSuccess: (result, sync) => {
      const config = useConfigStore.getState().config;
      setConfig({
        ...config,
        key_mappings: result.key_mappings,
        ...(result.turbo_settings ? { turbo_settings: result.turbo_settings } : {}),
      });
      if (sync) {
        setDirty(false);
      }
      queryClient.invalidateQueries({ queryKey: ['config'] });
    },
  });
}

export function useUnmap() {
  return useGenericMutation(api.unmapRemap);
}

export function useTurbo() {
  return useGenericMutation(api.setTurbo);
}

export function useRumbleLevel() {
  return useGenericMutation(api.setRumbleLevel);
}

export function useFireRumble() {
  return useGenericMutation(api.fireRumble);
}

export function useCombo() {
  return useGenericMutation(api.setCombo);
}

export function useMacro() {
  return useGenericMutation(api.setMacro);
}
