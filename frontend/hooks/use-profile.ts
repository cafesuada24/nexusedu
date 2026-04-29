"use client";

import * as React from "react";
import { useQuery } from "@tanstack/react-query";
import { getCurrentUser, getAuthToken } from "@/lib/api";
import { queryKeys } from "@/lib/query-keys";

/**
 * Hook to fetch the current user's profile.
 * Only enables the query if a JWT token is present in localStorage.
 */
export function useProfile(initialToken?: string | null) {
  const [isMounted, setIsMounted] = React.useState(false);

  React.useEffect(() => {
    setIsMounted(true);
  }, []);

  // Use the provided token or fall back to localStorage on mount
  const token = initialToken !== undefined ? initialToken : (typeof window !== "undefined" ? getAuthToken() : null);

  return useQuery({
    queryKey: [...queryKeys.auth.me, token],
    queryFn: getCurrentUser,
    enabled: isMounted && !!token, 
    staleTime: 1000 * 60 * 15,
    retry: false, // Don't retry on 401s to avoid multiple error toasts
  });
}
