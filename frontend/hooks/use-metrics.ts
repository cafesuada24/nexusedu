"use client";

import { useQuery } from "@tanstack/react-query";
import { fetchKpiStats, fetchRetentionTrend, type KpiStats, type RetentionTrendItem } from "@/lib/api";
import { queryKeys } from "@/lib/query-keys";
import React from "react";
import { useAuth } from "@/hooks/use-auth";

/**
 * Hook to fetch dashboard KPI stats.
 */
export function useKpiStats(initialData?: KpiStats) {
  const { isAuthenticated } = useAuth();
  const [isMounted, setIsMounted] = React.useState(false);

  React.useEffect(() => {
    setIsMounted(true);
  }, []);

  return useQuery({
    queryKey: queryKeys.metrics.stats,
    queryFn: fetchKpiStats,
    enabled: isMounted && isAuthenticated,
    initialData,
    refetchOnWindowFocus: true,
    refetchInterval: 10000, // Balanced 10s polling for real-time dashboard
    retry: false,
  });
}

/**
 * Hook to fetch retention trend data.
 */
export function useRetentionTrend(initialData?: RetentionTrendItem[]) {
  const { isAuthenticated } = useAuth();
  const [isMounted, setIsMounted] = React.useState(false);

  React.useEffect(() => {
    setIsMounted(true);
  }, []);

  return useQuery({
    queryKey: queryKeys.metrics.retention,
    queryFn: fetchRetentionTrend,
    enabled: isMounted && isAuthenticated,
    initialData,
    refetchOnWindowFocus: true,
    refetchInterval: 10000, // Balanced 10s polling for real-time dashboard
    retry: false,
  });
}
