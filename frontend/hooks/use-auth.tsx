"use client"

import * as React from "react"
import { useRouter } from "next/navigation"
import { toast } from "sonner"

import { type UserRead } from "@/lib/api"
import { useProfile } from "@/hooks/use-profile"
import { loginAction, logoutAction } from "@/app/actions/auth"
import { ApiError } from "next/dist/server/api-utils"

function warnLog(...args: unknown[]) {
  console.warn("[hooks/use-auth]", ...args)
}

interface AuthContextType {
  user: UserRead | null

  /**
   * True after client hydration completes.
   */
  authReady: boolean

  loading: boolean
  isAuthenticated: boolean

  login: (
    username: string,
    password: string,
  ) => Promise<void>

  logout: () => Promise<void>

  refreshUser: () => Promise<void>
}

const AuthContext =
  React.createContext<AuthContextType | undefined>(
    undefined,
  )

export function AuthProvider({
  children,
}: {
  children: React.ReactNode
}) {
  const router = useRouter()

  /**
   * Prevent SSR/client hydration mismatch.
   */
  const [mounted, setMounted] =
    React.useState(false)

  /**
   * True after component hydration.
   */
  const [authReady, setAuthReady] =
    React.useState(false)

  /**
   * Client hydration gate.
   *
   * Prevents:
   * - hydration mismatch
   * - provider remounts
   * - websocket churn
   */
  React.useEffect(() => {
    setMounted(true)
    setAuthReady(true)
  }, [])

  /**
   * Profile query only runs after hydration.
   * Authentication is handled via HTTP-only cookies.
   */
  const {
    data: user,
    isLoading,
    refetch,
    error,
  } = useProfile({
    enabled: mounted && authReady,
  })

  const isLoggingOut =
    React.useRef(false)

  const logout = React.useCallback(
    async () => {
      if (isLoggingOut.current) {
        return
      }

      isLoggingOut.current = true

      try {
        try {
          await logoutAction()
        } catch (err) {
          warnLog(
            "Server-side logout failed",
            err,
          )
        }

        toast.success("Đã đăng xuất")
      } catch (error) {
        warnLog(
          "Logout logic failed",
          error,
        )
      } finally {
        isLoggingOut.current = false

        window.location.href = "/login"
      }
    },
    [],
  )

  /**
   * Explicit authentication failure handler.
   */
  React.useEffect(() => {
    if (!mounted || !authReady || isLoading) {
      return
    }

    if (!error) {
      return
    }

    // Only log and potentially logout if we have a real error and we're not loading
    console.error(
      "[AUTH] Profile fetch failed",
      error,
    )

    /**
     * ONLY logout on explicit unauthorized (401).
     */
    const isUnauthorized =
      typeof error === "object" &&
      error !== null &&
      "status" in error &&
      (error as any).status === 401

    if (!isUnauthorized) {
      return
    }

    // If we were authenticated but now get a 401, or if we're on a dashboard route
    const isDashboard = window.location.pathname.startsWith("/dashboard")
    if (isDashboard || user) {
      warnLog("Unauthorized access detected, logging out...")
      logout()
    }
  }, [
    mounted,
    authReady,
    isLoading,
    error,
    user,
    logout,
  ])

  /**
   * Global unauthorized event listener.
   */
  React.useEffect(() => {
    if (!mounted) {
      return
    }

    const handleUnauthorized = () => {
      warnLog(
        "Global unauthorized event",
      )

      logout()
    }

    window.addEventListener(
      "nexusedu:unauthorized",
      handleUnauthorized,
    )

    return () => {
      window.removeEventListener(
        "nexusedu:unauthorized",
        handleUnauthorized,
      )
    }
  }, [mounted, logout])

  const login = React.useCallback(
    async (
      username: string,
      password: string,
    ) => {
      try {
        const result =
          await loginAction(
            username,
            password,
          )

        if (!result?.success) {
          toast.error(
            result?.error ??
            "Đăng nhập thất bại",
          )

          return
        }

        console.debug("[AUTH] Login action success, refetching profile...");
        await refetch()

        toast.success(
          "Đăng nhập thành công",
        )

        router.replace("/dashboard")
      } catch (error: any) {
        toast.error(
          error?.message ??
          "Đăng nhập thất bại",
        )

        throw error
      }
    },
    [refetch, router],
  )

  const value =
    React.useMemo<AuthContextType>(
      () => {
        console.debug("[AUTH] Context value update. user:", !!user, "isLoading:", isLoading, "isAuthenticated:", mounted && authReady && !!user);
        return {
          user: user ?? null,

          authReady,

          /**
           * Stable loading state.
           */
          loading:
            !mounted ||
            !authReady ||
            isLoading,

          /**
           * Websocket-safe authentication state.
           */
          isAuthenticated:
            mounted &&
            authReady &&
            !!user,

          login,
          logout,

          refreshUser: async () => {
            await refetch()
          },
        }
      },
      [
        mounted,
        user,
        authReady,
        isLoading,
        login,
        logout,
        refetch,
      ],
    )

  /**
   * Prevent hydration mismatch completely.
   */
  if (!mounted) {
    return null
  }

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const context =
    React.useContext(AuthContext)

  if (!context) {
    throw new Error(
      "useAuth must be used within AuthProvider",
    )
  }

  return context
}
