"use client"

import * as React from "react"
import { useRouter } from "next/navigation"
import { toast } from "sonner"
import { type UserRead } from "@/lib/api"
import { useProfile } from "@/hooks/use-profile"
import { loginAction, logoutAction } from "@/app/actions/auth"

function warnLog(...args: any[]) {
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
  
  // Use TanStack Query for profile management
  const { data: user, isLoading, refetch, isFetched, error } = useProfile()

  // Explicitly handle session expiration (401)
  React.useEffect(() => {
    if (isFetched && !user && !isLoading) {
       if (error) {
         warnLog("Session invalid or fetch failed", error)
       }
    }
  }, [isFetched, user, isLoading, error])

  const isLoggingOut = React.useRef(false);

  const logout = React.useCallback(async () => {
    if (isLoggingOut.current) return;
    isLoggingOut.current = true;
    try {
      if (typeof window !== "undefined") {
        window.localStorage.removeItem("nexusedu:auth:token");
      }
      await logoutAction()
      
      // HARD BREAK: Use window.location.href instead of router.push.
      // This forcefully unloads the React app and stops all active TanStack Query refetches.
      toast.success("Đã đăng xuất")
      window.location.href = "/login"
    } catch (error: any) {
      toast.error("Lỗi khi đăng xuất")
      warnLog("Logout error", error)
    } finally {
      isLoggingOut.current = false;
    }
  }, [])

  // Global unauthorized listener
  React.useEffect(() => {
    const handleUnauthorized = () => {
      warnLog("Global unauthorized event detected, logging out...")
      logout()
    }

    window.addEventListener("nexusedu:unauthorized", handleUnauthorized)
    return () => window.removeEventListener("nexusedu:unauthorized", handleUnauthorized)
  }, [logout])

  const login = async (username: string, password: string) => {
    try {
      const result = await loginAction(username, password)
      if (result?.success) {
        // After login, re-fetch profile to update cache and context
        await refetch()
        toast.success("Đăng nhập thành công")
        router.push("/dashboard")
      } else {
        toast.error(result?.error || "Đăng nhập thất bại")
      }
    } catch (error: any) {
      toast.error(error.message || "Đăng nhập thất bại")
      throw error
    }
  }

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
