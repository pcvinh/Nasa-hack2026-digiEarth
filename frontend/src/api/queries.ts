import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { client, unwrap } from './client';
import type { GuideRequest, SessionInput, TrendRequest } from './types';

export const useVariables = () =>
  useQuery({ queryKey: ['variables'], queryFn: async () => unwrap(await client.GET('/variables', { params: { query: {} } })).items });

export const useRegions = () =>
  useQuery({ queryKey: ['regions'], queryFn: async () => unwrap(await client.GET('/regions', { params: { query: {} } })).items });

export const useRegion = (id: string | null) =>
  useQuery({ queryKey: ['region', id], enabled: !!id, queryFn: async () => unwrap(await client.GET('/regions/{regionId}', { params: { path: { regionId: id! } } })) });

export const useTrend = (req: TrendRequest | null) =>
  useQuery({ queryKey: ['trend', req], enabled: !!req, queryFn: async () => unwrap(await client.POST('/trends/analyze', { body: req! })) });

export const useTrendMap = (variableId: string | null, enabled: boolean) =>
  useQuery({ queryKey: ['trend-map', variableId], enabled: enabled && !!variableId, queryFn: async () => unwrap(await client.GET('/trend-maps/{variableId}', { params: { path: { variableId: variableId! } } })) });

export const useGuideChat = () =>
  useMutation({ mutationFn: async (body: GuideRequest) => unwrap(await client.POST('/guide/chat', { body })) });

export const useSessions = () =>
  useQuery({ queryKey: ['sessions'], queryFn: async () => unwrap(await client.GET('/sessions')).items });

export const getSession = async (id: string) => unwrap(await client.GET('/sessions/{sessionId}', { params: { path: { sessionId: id } } }));

export function useSaveSession() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, body }: { id: string | null; body: SessionInput }) =>
      id
        ? unwrap(await client.PUT('/sessions/{sessionId}', { params: { path: { sessionId: id } }, body }))
        : unwrap(await client.POST('/sessions', { body })),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['sessions'] }),
  });
}
