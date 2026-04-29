import { QueryClient } from "@tanstack/react-query";

/**
 * Global QueryClient instance with sensible defaults for the NexusEDU app.
 * - staleTime: 5 minutes (data remains fresh for 5 mins)
 * - gcTime: 10 minutes (unused data is removed from cache after 10 mins)
 * - retry: 1 (retry failed requests once)
 */
export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 1000 * 60 * 5,
      gcTime: 1000 * 60 * 10,
      retry: 1,
      refetchOnWindowFocus: true,
    },
  },
});
