import { useEffect } from 'react';
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
      setKeyMappingsFromDevice(query.data.key_mappings);
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
      setConfig({ ...config, key_mappings: result.key_mappings });
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
