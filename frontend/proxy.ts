import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

export async function proxy(request: NextRequest) {
  const { pathname } = request.nextUrl;
  const token = request.cookies.get("nexusedu_auth_token")?.value;

  // 1. Route Protection: /dashboard/*
  if (pathname.startsWith("/dashboard")) {
    if (!token) {
      const url = new URL("/login", request.url);
      url.searchParams.set("callbackUrl", pathname);
      return NextResponse.redirect(url);
    }
  }

  // 2. Token Injection for API requests
  // If we are calling the backend API via the rewrite, inject the token from the cookie
  if (pathname.startsWith("/api/v1") && token) {
    const requestHeaders = new Headers(request.headers);
    requestHeaders.set("Authorization", `Bearer ${token}`);

    const response = NextResponse.next({
      request: {
        headers: requestHeaders,
      },
    });
    return response;
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/dashboard/:path*", "/api/v1/:path*"],
};
