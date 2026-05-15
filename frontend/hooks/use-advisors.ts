"use client";

import { useQuery } from "@tanstack/react-query";
import { fetchAdvisorsLeaderboard, fetchAdvisorDashboard } from "@/lib/api";
import { queryKeys } from "@/lib/query-keys";
import React from "react";
import { useAuth } from "@/hooks/use-auth";

/**
 * Hook to fetch the advisor dashboard metrics.
 */
export function useAdvisorDashboard() {
  const { isAuthenticated } = useAuth();
  const [isMounted, setIsMounted] = React.useState(false);

  React.useEffect(() => {
    setIsMounted(true);
  }, []);

  return useQuery({
    queryKey: queryKeys.advisors.dashboard(),
    queryFn: () => fetchAdvisorDashboard(),
    enabled: isMounted && isAuthenticated,
    refetchOnWindowFocus: true,
    refetchInterval: 30000, // Poll every 30s
  });
}

/**
 * Hook to fetch the advisor leaderboard.
 */
export function useAdvisorsLeaderboard(timeWindow: "weekly" | "monthly" | "semester" | "all_time" = "all_time") {
  const { isAuthenticated } = useAuth();
  const [isMounted, setIsMounted] = React.useState(false);

  React.useEffect(() => {
    setIsMounted(true);
  }, []);

  return useQuery({
    queryKey: queryKeys.advisors.leaderboard(timeWindow),
    queryFn: () => fetchAdvisorsLeaderboard(timeWindow),
    enabled: isMounted && isAuthenticated,
    refetchOnWindowFocus: true,
    refetchInterval: 10000, // Balanced 10s polling
    retry: false,
  });
}

