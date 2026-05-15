"use client"

import { useQuery } from "@tanstack/react-query"
import { fetchAdminDashboard } from "@/lib/api"
import { useAuth } from "@/hooks/use-auth"
import React from "react"

/**
 * Hook to fetch admin strategic overview data.
 */
export function useAdminDashboard() {
  const { isAuthenticated, user } = useAuth()
  const isAdmin = user?.role === "admin"
  const [isMounted, setIsMounted] = React.useState(false)

  React.useEffect(() => {
    setIsMounted(true)
  }, [])

  return useQuery({
    queryKey: ["admin", "dashboard"],
    queryFn: fetchAdminDashboard,
    enabled: isMounted && isAuthenticated && isAdmin,
    refetchInterval: 30000, // 30 seconds polling for real-time overview
    staleTime: 10000,
    retry: 1,
  })
}
