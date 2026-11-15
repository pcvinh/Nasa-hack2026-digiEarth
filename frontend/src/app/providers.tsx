import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import type { ReactNode } from 'react';
import { ApiError } from '../api/client';

const client = new QueryClient({ defaultOptions: { queries: { staleTime: Infinity, retry: (n, err) => !(err instanceof ApiError) && n < 1, refetchOnWindowFocus: false } } });

export function Providers({ children }: { children: ReactNode }) {
  return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
}
