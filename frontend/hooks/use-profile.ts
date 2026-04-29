"use client";

import * as React from "react";
import { useQuery } from "@tanstack/react-query";
import { getCurrentUser, getAuthToken } from "@/lib/api";
import { queryKeys } from "@/lib/query-keys";

/**
 * Hook to fetch the current user's profile.
 * Relies on httpOnly cookies for authentication.
 */
export function useProfile() {
  const [isMounted, setIsMounted] = React.useState(false);

  React.useEffect(() => {
    setIsMounted(true);
  }, []);

  return useQuery({
    queryKey: queryKeys.auth.me,
    queryFn: getCurrentUser,
    enabled: isMounted, 
    staleTime: 1000 * 60 * 15,
    retry: false, // Don't retry on 401s to avoid multiple error toasts
  });
}
