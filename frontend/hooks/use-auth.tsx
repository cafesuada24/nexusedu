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

  const isLoggingOut = React.useRef(false);

  const logout = React.useCallback(async () => {
    if (isLoggingOut.current) return;
    isLoggingOut.current = true;
    
    try {
      if (typeof window !== "undefined") {
        window.localStorage.removeItem("nexusedu:auth:token");
      }
      
      // Attempt server-side logout but don't let it block redirection
      try {
        await logoutAction()
      } catch (err) {
        warnLog("Server-side logout action failed", err)
      }
      
      toast.success("Đã đăng xuất")
    } catch (error: any) {
      warnLog("Logout logic error", error)
    } finally {
      // Force redirect regardless of success or failure
      isLoggingOut.current = false;
      if (typeof window !== "undefined") {
        window.location.href = "/login"
      }
    }
  }, [])

  // Explicitly handle session expiration (401/403)
  React.useEffect(() => {
    // getCurrentUser returns null on 401/403 authentication failures
    if (isFetched && !user && !isLoading) {
      if (error) {
        warnLog("Profile fetch encountered an error", error)
      }
      
      // Auto-logout if on a protected route
      if (typeof window !== "undefined") {
        const path = window.location.pathname
        if (path.startsWith("/dashboard")) {
          warnLog("Unauthorized access to dashboard detected, logging out...")
          logout()
        }
      }
    }
  }, [isFetched, user, isLoading, error, logout])


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
