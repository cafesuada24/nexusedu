"use client";

import * as React from "react";
import {
  useQuery,
  type UseQueryResult,
} from "@tanstack/react-query";

import {
  getCurrentUser,
} from "@/lib/api";

import { queryKeys } from "@/lib/query-keys";

interface UseProfileOptions {
  enabled?: boolean;
}

/**
 * Fetch current authenticated user profile.
 *
 * Features:
 * - SSR-safe hydration
 * - controllable execution
 * - stable auth lifecycle
 * - prevents premature unauthorized calls
 */
export function useProfile(
  options?: UseProfileOptions,
): UseQueryResult<any, Error> {
  const [isMounted, setIsMounted] =
    React.useState(false);

  React.useEffect(() => {
    setIsMounted(true);
  }, []);

  const enabled =
    options?.enabled ?? true;

  return useQuery({
    queryKey: queryKeys.auth.me,

    queryFn: getCurrentUser,

    /**
     * Only execute:
     * - after client mount
     * - when explicitly enabled
     */
    enabled:
      isMounted &&
      enabled,

    staleTime:
      1000 * 60 * 15,

    retry: false,

    refetchOnWindowFocus: false,
  });
}
