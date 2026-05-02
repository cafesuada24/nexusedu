"use client"

import * as React from "react"
import { useRouter } from "next/navigation"
import { toast } from "sonner"
import { useQueryClient } from "@tanstack/react-query"
import {
  login as apiLogin,
  logout as apiLogout,
  type UserRead,
} from "@/lib/api"
import { useProfile } from "@/hooks/use-profile"

function warnLog(...args: any[]) {
  // eslint-disable-next-line no-console
  console.warn("[hooks/use-auth]", ...args)
}

interface AuthContextType {
  user: UserRead | null
  loading: boolean
  isAuthenticated: boolean
  login: (username: string, password: string) => Promise<void>
  logout: () => Promise<void>
  refreshUser: () => Promise<void>
}

const AuthContext = React.createContext<AuthContextType | undefined>(undefined)

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const router = useRouter()
  const queryClient = useQueryClient()
  
  // Use TanStack Query for profile management
  const { data: user, isLoading, refetch, isFetched, error } = useProfile()

  // Explicitly handle session expiration (401)
  React.useEffect(() => {
    if (isFetched && !user && !isLoading) {
       // If we were on a protected route, the middleware would have redirected us.
       // But if we are already here and the profile fetch fails, we might want to clear state.
       if (error) {
         warnLog("Session invalid or fetch failed", error)
       }
    }
  }, [isFetched, user, isLoading, error])

  const login = async (username: string, password: string) => {
    try {
      const result = await apiLogin(username, password)
      if (result?.success) {
        // After login, re-fetch profile to update cache and context
        await refetch()
        toast.success("Đăng nhập thành công")
        router.push("/dashboard")
        }
        } catch (error: any) {      toast.error(error.message || "Đăng nhập thất bại")
      throw error
    }
  }

  const logout = React.useCallback(async () => {
    try {
      await apiLogout()
      // Clear all queries to remove user-specific data from cache
      queryClient.clear()
      toast.success("Đã đăng xuất")
      router.push("/login")
    } catch (error: any) {
      toast.error("Lỗi khi đăng xuất")
      warnLog("Logout error", error)
    }
  }, [router, queryClient])

  const value = React.useMemo(
    () => ({
      user: user || null,
      loading: isLoading,
      isAuthenticated: !!user,
      login,
      logout,
      refreshUser: async () => { await refetch() },
    }),
    [user, isLoading, login, logout, refetch],
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
