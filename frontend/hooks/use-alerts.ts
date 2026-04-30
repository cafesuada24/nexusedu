"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { fetchAlerts, updateAlertStatus, type BackendInterventionStatus, getAuthToken, fetchDraftStatus } from "@/lib/api";
import { queryKeys } from "@/lib/query-keys";
import { toast } from "sonner";
import React from "react";

import { useAuth } from "@/hooks/use-auth";

/**
 * Hook to fetch the list of alerts (at-risk students).
 */
export function useAlerts() {
  const { isAuthenticated } = useAuth();
  const [isMounted, setIsMounted] = React.useState(false);

  React.useEffect(() => {
    setIsMounted(true);
  }, []);

  return useQuery({
    queryKey: queryKeys.alerts.list(),
    queryFn: fetchAlerts,
    enabled: isMounted && isAuthenticated,
    // Ensure we refetch when coming back to the tab to keep Kanban fresh
    refetchOnWindowFocus: true,
    refetchInterval: 10000, // Balanced 10s polling for real-time Kanban updates
    retry: false,
  });
}

/**
 * Mutation hook to update an alert's intervention status.
 * Implements optimistic updates to ensure the Kanban board feels snappy.
 */
export function useUpdateAlertStatus() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ sid, status }: { sid: string; status: BackendInterventionStatus }) =>
      updateAlertStatus(sid, status),
    
    // Optimistic Update logic
    onMutate: async ({ sid, status }) => {
      // Cancel any outgoing refetches (so they don't overwrite our optimistic update)
      await queryClient.cancelQueries({ queryKey: queryKeys.alerts.list() });

      // Snapshot the previous value
      const previousAlerts = queryClient.getQueryData(queryKeys.alerts.list());

      // Optimistically update to the new value
      queryClient.setQueryData(queryKeys.alerts.list(), (old: any[] | undefined) => {
        if (!old) return [];
        return old.map((alert) =>
          alert.sid === sid ? { ...alert, intervention_status: status } : alert
        );
      });

      // Return a context object with the snapshotted value
      return { previousAlerts };
    },

    // If the mutation fails, use the context returned from onMutate to roll back
    onError: (err, variables, context) => {
      if (context?.previousAlerts) {
        queryClient.setQueryData(queryKeys.alerts.list(), context.previousAlerts);
      }
      toast.error("Không thể cập nhật trạng thái", {
        description: "Vui lòng thử lại sau.",
      });
    },

    // Always refetch after error or success to ensure we are in sync with the server
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.alerts.list() });
    },
  });
}

/**
 * Hook to poll draft status for a student.
 */
export function useDraftStatus(sid?: string | null) {
  return useQuery({
    queryKey: sid ? ["alerts", sid, "draft"] : ["alerts", "draft", "none"],
    queryFn: async () => {
      if (!sid) return null;
      return await fetchDraftStatus(sid);
    },
    enabled: !!sid,
    // Poll only if the query data suggests generation is in progress.
    refetchInterval: (query) => {
      const state = query.state;
      const data = state.data;
      
      // Stop polling if we have data and generation is finished, or if there's an error.
      if (data && !data.is_generating) {
        return false;
      }
      return 3000; // Poll every 3s while generating.
    },
    // Prevent refetching on window focus to reduce noise during background polling.
    refetchOnWindowFocus: false,
    staleTime: 0,
    retry: 2,
    retryDelay: 3000,
  });
}
