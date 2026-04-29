"use client"

import * as React from "react"
import { useRouter } from "next/navigation"
import { toast } from "sonner"
import { useQueryClient } from "@tanstack/react-query"
import {
  login as apiLogin,
  clearAuthToken,
  getAuthToken,
  type UserRead,
} from "@/lib/api"
import { useProfile } from "@/hooks/use-profile"

function warnLog(...args: any[]) {
  // eslint-disable-next-line no-console
  console.warn("[hooks/use-auth]", ...args)
}

interface AuthContextType {
  user: UserRead | null
  token: string | null
  loading: boolean
  isAuthenticated: boolean
  login: (username: string, password: string) => Promise<void>
  logout: () => void
  refreshUser: () => Promise<void>
}

const AuthContext = React.createContext<AuthContextType | undefined>(undefined)

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const router = useRouter()
  const queryClient = useQueryClient()
  const [token, setToken] = React.useState<string | null>(null)

  // Initialize token from localStorage on mount
  React.useEffect(() => {
    setToken(getAuthToken())
  }, [])
  
  // Use TanStack Query for profile management
  const { data: user, isLoading, refetch, isFetched } = useProfile(token)

  // Explicitly handle session expiration (401)
  React.useEffect(() => {
    if (isFetched && !user && typeof window !== "undefined") {
      const activeToken = getAuthToken()
      if (activeToken) {
        // Token exists but profile is null -> session expired or invalid
        warnLog("Session invalid, clearing token")
        setToken(null)
        clearAuthToken()
        queryClient.clear()
        toast.error("Phiên làm việc hết hạn", {
          description: "Vui lòng đăng nhập lại.",
          id: "auth-expired",
        })
        router.push("/login")
      }
    }
  }, [isFetched, user, queryClient, router])

  const login = async (username: string, password: string) => {
    try {
      const result = await apiLogin(username, password)
      if (result?.access_token) {
        setToken(result.access_token)
        // After login, re-fetch profile to update cache and context
        await refetch()
        toast.success("Đăng nhập thành công")
        router.push("/dashboard/analysis")
      }
    } catch (error: any) {
      toast.error(error.message || "Đăng nhập thất bại")
      throw error
    }
  }

  const logout = React.useCallback(() => {
    setToken(null)
    clearAuthToken()
    // Clear all queries to remove user-specific data from cache
    queryClient.clear()
    toast.success("Đã đăng xuất")
    router.push("/login")
  }, [router, queryClient])

  const value = React.useMemo(
    () => ({
      user: user || null,
      token,
      loading: isLoading,
      isAuthenticated: !!user,
      login,
      logout,
      refreshUser: async () => { await refetch() },
    }),
    [user, token, isLoading, login, logout, refetch],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const context = React.useContext(AuthContext)
  if (context === undefined) {
    throw new Error("useAuth must be used within an AuthProvider")
  }
  return context
}
