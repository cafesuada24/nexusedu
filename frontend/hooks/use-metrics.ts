"use client";

import { useQuery } from "@tanstack/react-query";
import { fetchKpiStats, fetchRetentionTrend } from "@/lib/api";
import { queryKeys } from "@/lib/query-keys";
import React from "react";
import { useAuth } from "@/hooks/use-auth";

/**
 * Hook to fetch dashboard KPI stats.
 */
export function useKpiStats() {
  const { token } = useAuth();
  const [isMounted, setIsMounted] = React.useState(false);

  React.useEffect(() => {
    setIsMounted(true);
  }, []);

  return useQuery({
    queryKey: [...queryKeys.metrics.stats, token],
    queryFn: fetchKpiStats,
    enabled: isMounted && !!token,
    refetchOnWindowFocus: true,
    refetchInterval: 3000,
    retry: false,
  });
}

/**
 * Hook to fetch retention trend data.
 */
export function useRetentionTrend() {
  const { token } = useAuth();
  const [isMounted, setIsMounted] = React.useState(false);

  React.useEffect(() => {
    setIsMounted(true);
  }, []);

  return useQuery({
    queryKey: [...queryKeys.metrics.retention, token],
    queryFn: fetchRetentionTrend,
    enabled: isMounted && !!token,
    refetchOnWindowFocus: true,
    refetchInterval: 3000,
    retry: false,
  });
}
