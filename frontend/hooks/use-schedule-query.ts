"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { queryKeys } from "@/lib/query-keys";
import { DEFAULT_SCHEDULE, type Schedule } from "@/lib/schedule";
import type { AdvisorProfileRead } from "@/lib/api";
import {
  fetchAdvisorSchedule,
  addWorkingHours,
  deleteWorkingHours,
  addDayOff,
  deleteDayOff,
} from "@/lib/api";
import {
  backendToFrontend,
  generateDiffCommands,
} from "@/lib/schedule-adapter";

async function fetchSchedule(): Promise<Schedule> {
  const beSchedule = await fetchAdvisorSchedule();
  return backendToFrontend(beSchedule);
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

  /** Resolve advisor_id from the cached auth profile (avoids extra network call). */
  const getAdvisorId = (): string => {
    const cached = queryClient.getQueryData<AdvisorProfileRead | null>(
      queryKeys.auth.me,
    );
    // The auth query stores { id, email, role } but advisor profile is separate.
    // Fall back to a dedicated advisor profile query key if present.
    const advisorCached = queryClient.getQueryData<AdvisorProfileRead>(
      ["advisor", "profile"],
    );
    const id = advisorCached?.advisor_id ?? (cached as any)?.advisor_id;
    if (id) return id;
    throw new Error("Không tìm thấy advisor_id. Vui lòng tải lại trang.");
  };

  const mutation = useMutation({
    mutationFn: async (next: Schedule | "RESET") => {
      const prevBe = await fetchAdvisorSchedule();

      if (next === "RESET") {
        // Delete all working hours and days off on BE — clean slate
        for (const wh of prevBe.working_hours) {
          await deleteWorkingHours(wh.id);
        }
        for (const doff of prevBe.days_off) {
          await deleteDayOff(doff.id);
        }
        return;
      }

      const commands = generateDiffCommands(prevBe, next);

      let advisorId: string;
      try {
        advisorId = getAdvisorId();
      } catch {
        // Fallback: fetch profile if not cached (first-time edge case)
        const { fetchAdvisorProfile } = await import("@/lib/api");
        const profile = await fetchAdvisorProfile();
        advisorId = profile.advisor_id;
      }

      // Execute commands sequentially to avoid DB lock issues or partial state
      for (const id of commands.deleteWorkingHours) {
        await deleteWorkingHours(id);
      }
      for (const payload of commands.addWorkingHours) {
        await addWorkingHours(advisorId, payload);
      }
      for (const id of commands.deleteDayOff) {
        await deleteDayOff(id);
      }
      for (const payload of commands.addDayOff) {
        await addDayOff(advisorId, payload);
      }
    },
    onMutate: async (nextSchedule) => {
      await queryClient.cancelQueries({ queryKey: queryKeys.schedule.all });
      const previousSchedule = queryClient.getQueryData(queryKeys.schedule.all);
      if (nextSchedule !== "RESET") {
        queryClient.setQueryData(queryKeys.schedule.all, nextSchedule);
      } else {
        // Optimistically show empty schedule for reset
        const empty: Schedule = {
          ...DEFAULT_SCHEDULE,
          week: {
            mon: { enabled: false, slots: [] },
            tue: { enabled: false, slots: [] },
            wed: { enabled: false, slots: [] },
            thu: { enabled: false, slots: [] },
            fri: { enabled: false, slots: [] },
            sat: { enabled: false, slots: [] },
            sun: { enabled: false, slots: [] },
          },
          overrides: [],
        };
        queryClient.setQueryData(queryKeys.schedule.all, empty);
      }
      return { previousSchedule };
    },
    onError: (_err, _nextSchedule, context) => {
      if (context?.previousSchedule) {
        queryClient.setQueryData(
          queryKeys.schedule.all,
          context.previousSchedule,
        );
      }
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.schedule.all });
    },
  });

  return {
    schedule: query.data ?? DEFAULT_SCHEDULE,
    isLoading: query.isLoading,
    isMutating: mutation.isPending,
    isError: query.isError,
    error: query.error,
    setSchedule: (updater: Schedule | ((prev: Schedule) => Schedule)) => {
      const current = query.data ?? DEFAULT_SCHEDULE;
      const next = typeof updater === "function" ? updater(current) : updater;
      mutation.mutate(next);
    },
    resetSchedule: () => {
      mutation.mutate("RESET");
    },
  };
}

