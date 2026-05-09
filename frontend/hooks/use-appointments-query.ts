"use client"

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { queryKeys } from "@/lib/query-keys"
import {
  SlotTakenError,
  type Appointment,
  type CreateAppointmentInput,
} from "@/lib/appointments"

type FetchArgs = {
  advisorToken: string
  from: string
  to: string
}

async function fetchAppointments({
  advisorToken,
  from,
  to,
}: FetchArgs): Promise<Appointment[]> {
  const params = new URLSearchParams({ advisor: advisorToken, from, to })
  const res = await fetch(`/api/appointments?${params.toString()}`, {
    cache: "no-store",
  })
  if (!res.ok) throw new Error("failed to load appointments")
  return (await res.json()) as Appointment[]
}

async function createAppointment(
  input: CreateAppointmentInput,
): Promise<Appointment> {
  const res = await fetch("/api/appointments", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
    cache: "no-store",
  })
  if (res.status === 409) {
    throw new SlotTakenError()
  }
  if (!res.ok) {
    throw new Error(`failed to create appointment (${res.status})`)
  }
  return (await res.json()) as Appointment
}

export function useAppointmentsQuery(args: FetchArgs) {
  return useQuery({
    queryKey: queryKeys.appointments.list(args.advisorToken, args.from, args.to),
    queryFn: () => fetchAppointments(args),
    refetchOnWindowFocus: true,
    staleTime: 0,
  })
}

export function useCreateAppointment() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: createAppointment,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.appointments.all })
    },
  })
}
