"use server"

import { cookies } from "next/headers"
import { endpoint, withTimeout } from "@/lib/api"
import { logger } from "@/lib/logger"

export async function loginAction(username: string, password: string) {
  try {
    const form = new URLSearchParams()
    form.append("username", username)
    form.append("password", password)

    // Using a hardcoded url or reading from env correctly since it's on the server
    const baseUrl = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000/api/v1"
    const url = `${baseUrl.replace(/\/+$/, "")}/auth/jwt/login`

    const res = await withTimeout(
      (signal) =>
        fetch(url, {
          method: "POST",
          headers: {
            "Content-Type": "application/x-www-form-urlencoded",
            Accept: "application/json",
          },
          body: form.toString(),
          signal,
        }),
      10000 // 10s timeout
    )

    if (!res.ok) {
      const errorBody = await res.json().catch(() => ({}))
      logger.warn({ username, status: res.status, errorBody }, "Login failed")
      return { success: false, error: errorBody.detail || "Đăng nhập thất bại" }
    }

    const data = await res.json()
    const token = data.access_token

    if (token) {
      const cookieStore = await cookies()
      cookieStore.set("nexusedu_auth_token", token, {
        httpOnly: true,
        secure: process.env.NODE_ENV === "production",
        sameSite: "lax",
        path: "/",
        maxAge: 60 * 60 * 8, // 8h — matches planned JWT lifetime_seconds in src/presentation/api/auth.py
      })

      logger.info({ username }, "Login successful")
      return { success: true }
    }

    logger.error({ username }, "No token received from server")
    return { success: false, error: "Không nhận được token từ server" }
  } catch (error: any) {
    logger.error({ err: error, username }, "Internal login error")
    return { success: false, error: error.message || "Internal Server Error" }
  }
}

export async function logoutAction() {
  try {
    const cookieStore = await cookies()
    cookieStore.delete("nexusedu_auth_token")
    logger.info("Logout successful")
    return { success: true }
  } catch (error: any) {
    logger.error({ err: error }, "Internal logout error")
    return { success: false, error: "Lỗi khi đăng xuất" }
  }
}
