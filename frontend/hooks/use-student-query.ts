"use client"

import { useQuery } from "@tanstack/react-query"
import { fetchStudent } from "@/lib/api"
import { queryKeys } from "@/lib/query-keys"

export function useStudent(sid: string | undefined, enabled = true) {
  return useQuery({
    queryKey: sid ? queryKeys.students.detail(sid) : ["students", "detail", "none"],
    queryFn: () => fetchStudent(sid!),
    enabled: enabled && !!sid,
    staleTime: 1000 * 60 * 5, // 5 minutes
  })
}
