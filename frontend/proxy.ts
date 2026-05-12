import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";
import { authFetch, endpoint } from "./lib/api";

type UserRole = "admin" | "advisor" | "viewer";

function decodeJwtPayload(token: string): Record<string, unknown> | null {
  const parts = token.split(".");
  if (parts.length < 2) return null;

  try {
    const base64 = parts[1].replace(/-/g, "+").replace(/_/g, "/");
    const padded = base64.padEnd(Math.ceil(base64.length / 4) * 4, "=");
    const decoded = atob(padded);
    return JSON.parse(decoded) as Record<string, unknown>;
  } catch {
    return null;
  }
}

function extractRoleFromPayload(payload: Record<string, unknown>): UserRole | null {
  const candidates = [
    payload.role,
    payload.user_role,
    payload.authorities,
    payload.roles,
  ];

  for (const value of candidates) {
    if (typeof value === "string") {
      const normalized = value.toLowerCase();
      if (normalized === "admin" || normalized === "advisor" || normalized === "viewer") {
        return normalized;
      }
    }

    if (Array.isArray(value)) {
      for (const entry of value) {
        if (typeof entry !== "string") continue;
        const normalized = entry.toLowerCase();
        if (normalized === "admin" || normalized === "advisor" || normalized === "viewer") {
          return normalized;
        }
      }
    }
  }

  return null;
}

async function resolveUserRole(token: string, request: NextRequest): Promise<UserRole | null> {
  const payload = decodeJwtPayload(token);
  if (payload) {
    const roleFromToken = extractRoleFromPayload(payload);
    if (roleFromToken) return roleFromToken;
  }

  // Fetch directly from the backend to avoid Next.js middleware fetch loops.
  // We use the origin of NEXT_PUBLIC_API_BASE_URL to construct the /me URL safely.
  // const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000/api/v1";
  // let apiOrigin = "http://localhost:8000";
  // try {
  //   apiOrigin = new URL(apiBaseUrl).origin;
  // } catch {
  //   // Fallback if URL is malformed
  // }
  //
  // // Force IPv4 for local backend to prevent Node 18+ IPv6 localhost resolution failures
  // // This is a common issue in Next.js Edge runtime when fetching local servers.
  // apiOrigin = apiOrigin.replace("://localhost", "://127.0.0.1");

  try {
    const res = await authFetch(
      endpoint('users/me'),
      {
        method: "GET",
        cache: "no-store",
      });

    if (!res.ok) {
      console.warn(`[proxy] /users/me returned status ${res.status}`);
      return null;
    }
    const data = (await res.json()) as { role?: unknown };
    if (typeof data.role !== "string") return null;

    const normalized = data.role.toLowerCase();
    if (normalized === "admin" || normalized === "advisor" || normalized === "viewer") {
      return normalized;
    }
  } catch (error) {
    console.warn("[proxy] Failed to resolve role from /users/me:", error);
    return null;
  }

  return null;
}

export async function proxy(request: NextRequest) {
  const { pathname } = request.nextUrl;
  const token = request.cookies.get("nexusedu_auth_token")?.value;
  const debugApiLog =
    process.env.NODE_ENV !== "production" ||
    process.env.DEBUG_API_PROXY_LOGS === "1";

  if (pathname.startsWith("/api/v1") && debugApiLog) {
    console.info("[proxy/api-v1]", {
      method: request.method,
      pathname,
      query: request.nextUrl.search,
      hasAuthCookie: Boolean(token),
    });
  }

  // 1. Route Protection: /dashboard/*
  if (pathname.startsWith("/dashboard")) {
    if (!token) {
      const url = new URL("/login", request.url);
      url.searchParams.set("callbackUrl", pathname);
      return NextResponse.redirect(url);
    }

    if (pathname.startsWith("/dashboard/import")) {
      const role = await resolveUserRole(token, request);
      if (role !== "admin") {
        return NextResponse.redirect(new URL("/dashboard/alerts", request.url));
      }
    }
  }

  // 2. Authenticated user visiting login page
  // if (pathname === "/login" && token) {
  //   return NextResponse.redirect(new URL("/dashboard", request.url));
  // }

  // 3. Token Injection & API Proxying
  if (pathname.startsWith("/api/v1")) {
    const requestHeaders = new Headers(request.headers);
    if (token) {
      requestHeaders.set("Authorization", `Bearer ${token}`);
      requestHeaders.set("Cookie", `nexusedu_auth_token=${token}`);
    }

    // Pass through to next.config.mjs rewrites with injected headers
    return NextResponse.next({
      request: {
        headers: requestHeaders,
      },
    });
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/dashboard/:path*", "/api/v1/:path*"],
};
