"use client";

import * as React from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { queryKeys } from "@/lib/query-keys";
import { 
  fetchNotifications, 
  markNotificationAsRead as apiMarkAsRead, 
  markAllNotificationsAsRead as apiMarkAllAsRead,
  Notification
} from "@/lib/api";
import { toast } from "sonner";

export type { Notification };

export function useNotifications() {
  const queryClient = useQueryClient();

  const { data, isLoading } = useQuery({
    queryKey: queryKeys.notifications.list(),
    queryFn: fetchNotifications,
    refetchInterval: 30000, // Poll every 30 seconds as a fallback
  });

  const notifications = data?.notifications ?? [];
  const unreadCount = data?.unreadCount ?? 0;

  const markAsReadMutation = useMutation({
    mutationFn: apiMarkAsRead,
    onMutate: async (id) => {
      await queryClient.cancelQueries({ queryKey: queryKeys.notifications.list() });
      const previousData = queryClient.getQueryData(queryKeys.notifications.list());
      
      queryClient.setQueryData(queryKeys.notifications.list(), (old: any) => {
        if (!old) return old;
        return {
          ...old,
          unreadCount: Math.max(0, old.unreadCount - 1),
          notifications: old.notifications.map((n: Notification) => 
            n.id === id ? { ...n, isRead: true } : n
          ),
        };
      });

      return { previousData };
    },
    onError: (err, id, context) => {
      queryClient.setQueryData(queryKeys.notifications.list(), context?.previousData);
      toast.error("Không thể đánh dấu đã đọc");
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.notifications.list() });
    },
  });

  const markAllAsReadMutation = useMutation({
    mutationFn: apiMarkAllAsRead,
    onMutate: async () => {
      await queryClient.cancelQueries({ queryKey: queryKeys.notifications.list() });
      const previousData = queryClient.getQueryData(queryKeys.notifications.list());
      
      queryClient.setQueryData(queryKeys.notifications.list(), (old: any) => {
        if (!old) return old;
        return {
          ...old,
          unreadCount: 0,
          notifications: old.notifications.map((n: Notification) => ({ ...n, isRead: true })),
        };
      });

      return { previousData };
    },
    onError: (err, variables, context) => {
      queryClient.setQueryData(queryKeys.notifications.list(), context?.previousData);
      toast.error("Không thể đánh dấu tất cả đã đọc");
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.notifications.list() });
    },
  });

  const markAsRead = (id: string) => {
    markAsReadMutation.mutate(id);
  };

  const markAllAsRead = () => {
    markAllAsReadMutation.mutate();
  };

  const clearNotifications = () => {
    // This is a local-only operation in the original mock, 
    // we'll just invalidate for now or we could implement a DELETE all if needed.
    queryClient.setQueryData(queryKeys.notifications.list(), { notifications: [], unreadCount: 0 });
  };

  return {
    notifications,
    unreadCount,
    isLoading,
    markAsRead,
    markAllAsRead,
    clearNotifications,
  };
}
