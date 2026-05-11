"use client"

import * as React from "react"
import { useRouter } from "next/navigation"
import { toast } from "sonner"

import { type UserRead } from "@/lib/api"
import { useProfile } from "@/hooks/use-profile"
import { loginAction, logoutAction } from "@/app/actions/auth"

function warnLog(...args: unknown[]) {
  console.warn("[hooks/use-auth]", ...args)
}

interface AuthContextType {
  user: UserRead | null
  token: string | null

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
   * null = unauthenticated
   */
  const [token, setToken] =
    React.useState<string | null>(null)

  /**
   * True after localStorage hydration.
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
  }, [])

  /**
   * Hydrate auth token exactly once.
   */
  React.useEffect(() => {
    if (!mounted) {
      return
    }

    const storedToken =
      window.localStorage.getItem(
        "nexusedu:auth:token",
      )

    setToken(storedToken)

    setAuthReady(true)
  }, [mounted])

  /**
   * Profile query only runs after:
   * - hydration complete
   * - token available
   */
  const {
    data: user,
    isLoading,
    refetch,
    error,
  } = useProfile({
    enabled:
      mounted &&
      authReady &&
      !!token,
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
        window.localStorage.removeItem(
          "nexusedu:auth:token",
        )

        setToken(null)

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
   *
   * Avoid triggering logout from transient
   * query invalidation states.
   */
  React.useEffect(() => {
    if (!mounted) {
      return
    }

    if (!authReady) {
      return
    }

    if (!token) {
      return
    }

    if (isLoading) {
      return
    }

    if (!error) {
      return
    }

    warnLog(
      "Authentication failure detected",
      error,
    )

    const path =
      window.location.pathname

    if (path.startsWith("/dashboard")) {
      logout()
    }
  }, [
    mounted,
    authReady,
    token,
    isLoading,
    error,
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

        if (result.token) {
          window.localStorage.setItem(
            "nexusedu:auth:token",
            result.token,
          )

          setToken(result.token)
        }

        await refetch()

        toast.success(
          "Đăng nhập thành công",
        )

        router.push("/dashboard")
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
      () => ({
        user: user ?? null,

        token,

        authReady,

        /**
         * Stable loading state.
         */
        loading:
          !mounted ||
          !authReady ||
          (
            authReady &&
            !!token &&
            isLoading
          ),

        /**
         * Websocket-safe authentication state.
         */
        isAuthenticated:
          mounted &&
          authReady &&
          !!token,

        login,
        logout,

        refreshUser: async () => {
          await refetch()
        },
      }),
      [
        mounted,
        user,
        token,
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
