"use client"

import { useQuery } from "@tanstack/react-query"
import { authFetch, DEFAULT_TIMEOUT_MS, endpoint, withTimeout } from "@/lib/api"
import { queryKeys } from "@/lib/query-keys"
import type { Appointment } from "@/lib/appointments"

type FetchArgs = {
  caseId: string
  from: string
  to: string
}

async function fetchAppointments({
  caseId,
  from,
  to,
}: FetchArgs): Promise<Appointment[]> {
  const params = new URLSearchParams({ case_id: caseId, from, to })
  const url = endpoint(`/appointments?${params.toString()}`)
  const res = await withTimeout(
    (signal) =>
      authFetch(
        url,
        { cache: "no-store", suppressUnauthorizedEvent: true },
        signal,
      ),
    DEFAULT_TIMEOUT_MS,
  )
  if (!res.ok) throw new Error(`failed to load appointments (${res.status})`)
  return (await res.json()) as Appointment[]
}

export function useAppointmentsQuery(args: FetchArgs) {
  return useQuery({
    queryKey: queryKeys.appointments.list(args.caseId, args.from, args.to),
    queryFn: () => fetchAppointments(args),
    enabled: Boolean(args.caseId),
    refetchOnWindowFocus: true,
    staleTime: 0,
  })
}
