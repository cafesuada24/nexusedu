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
  const { token } = useAuth();
  const [isMounted, setIsMounted] = React.useState(false);

  React.useEffect(() => {
    setIsMounted(true);
  }, []);

  return useQuery({
    queryKey: [...queryKeys.advisors.leaderboard(timeWindow), token],
    queryFn: () => fetchAdvisorsLeaderboard(timeWindow),
    enabled: isMounted && !!token,
    refetchOnWindowFocus: true,
    refetchInterval: 3000,
    retry: false,
  });
}

/**
 * Hook to fetch advisor engagement metrics.
 */
export function useAdvisorsEngagement() {
  const { token } = useAuth();
  const [isMounted, setIsMounted] = React.useState(false);

  React.useEffect(() => {
    setIsMounted(true);
  }, []);

  return useQuery({
    queryKey: [...queryKeys.advisors.engagement(), token],
    queryFn: fetchAdvisorsEngagement,
    enabled: isMounted && !!token,
    refetchOnWindowFocus: true,
    refetchInterval: 3000,
    retry: false,
  });
}
