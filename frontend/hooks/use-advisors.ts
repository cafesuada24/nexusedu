"use client";

import { useQuery } from "@tanstack/react-query";
import { fetchAdvisorsLeaderboard, fetchAdvisorsEngagement, getAuthToken } from "@/lib/api";
import { queryKeys } from "@/lib/query-keys";
import React from "react";
import { useAuth } from "@/hooks/use-auth";

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

/**
 * Hook to fetch advisor engagement metrics.
 */
export function useAdvisorsEngagement() {
  const { isAuthenticated } = useAuth();
  const [isMounted, setIsMounted] = React.useState(false);

  React.useEffect(() => {
    setIsMounted(true);
  }, []);

  return useQuery({
    queryKey: queryKeys.advisors.engagement(),
    queryFn: fetchAdvisorsEngagement,
    enabled: isMounted && isAuthenticated,
    refetchOnWindowFocus: true,
    refetchInterval: 10000, // Balanced 10s polling for real-time updates
    retry: false,
  });
}
