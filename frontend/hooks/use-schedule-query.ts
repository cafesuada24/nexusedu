"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { queryKeys } from "@/lib/query-keys";
import { DEFAULT_SCHEDULE, type Schedule } from "@/lib/schedule";

async function fetchSchedule(): Promise<Schedule> {
  const res = await fetch("/api/schedule", { cache: "no-store" });
  if (!res.ok) throw new Error("failed to load schedule");
  const data = (await res.json()) as Partial<Schedule>;
  return { ...DEFAULT_SCHEDULE, ...data };
}

async function persistSchedule(next: Schedule): Promise<void> {
  await fetch("/api/schedule", {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(next),
    cache: "no-store",
  });
}

/**
 * Hook to manage advisor's schedule with automatic caching and focus revalidation.
 */
export function useScheduleQuery() {
  const queryClient = useQueryClient();

  const query = useQuery({
    queryKey: queryKeys.schedule.all,
    queryFn: fetchSchedule,
    refetchOnWindowFocus: true,
    placeholderData: DEFAULT_SCHEDULE,
  });

  const mutation = useMutation({
    mutationFn: persistSchedule,
    onMutate: async (nextSchedule) => {
      await queryClient.cancelQueries({ queryKey: queryKeys.schedule.all });
      const previousSchedule = queryClient.getQueryData(queryKeys.schedule.all);
      queryClient.setQueryData(queryKeys.schedule.all, nextSchedule);
      return { previousSchedule };
    },
    onError: (err, nextSchedule, context) => {
      if (context?.previousSchedule) {
        queryClient.setQueryData(queryKeys.schedule.all, context.previousSchedule);
      }
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.schedule.all });
    },
  });

  return {
    schedule: query.data ?? DEFAULT_SCHEDULE,
    isLoading: query.isLoading,
    setSchedule: (updater: Schedule | ((prev: Schedule) => Schedule)) => {
      const current = query.data ?? DEFAULT_SCHEDULE;
      const next = typeof updater === "function" ? updater(current) : updater;
      mutation.mutate(next);
    },
    resetSchedule: () => {
      mutation.mutate(DEFAULT_SCHEDULE);
    },
  };
}
