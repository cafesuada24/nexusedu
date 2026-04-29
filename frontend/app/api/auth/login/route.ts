import { cookies } from "next/headers";
import { NextResponse } from "next/server";
import { endpoint, withTimeout } from "@/lib/api";

export async function POST(request: Request) {
  try {
    const { username, password } = await request.json();

    const form = new URLSearchParams();
    form.append("username", username);
    form.append("password", password);

    const res = await withTimeout(
      (signal) =>
        fetch(endpoint("/auth/jwt/login"), {
          method: "POST",
          headers: {
            "Content-Type": "application/x-www-form-urlencoded",
            Accept: "application/json",
          },
          body: form.toString(),
          signal,
        }),
      10000 // 10s timeout
    );

    if (!res.ok) {
      const errorBody = await res.json().catch(() => ({}));
      return NextResponse.json(
        { detail: errorBody.detail || "Đăng nhập thất bại" },
        { status: res.status }
      );
    }

    const data = await res.json();
    const token = data.access_token;

    if (token) {
      const cookieStore = await cookies();
      cookieStore.set("nexusedu_auth_token", token, {
        httpOnly: true,
        secure: process.env.NODE_ENV === "production",
        sameSite: "lax",
        path: "/",
        // Set maxAge to match token expiry if known, or a reasonable default (e.g., 7 days)
        maxAge: 60 * 60 * 24 * 7,
      });

      return NextResponse.json({ success: true });
    }

    return NextResponse.json(
      { detail: "Không nhận được token từ server" },
      { status: 500 }
    );
  } catch (error: any) {
    return NextResponse.json(
      { detail: error.message || "Internal Server Error" },
      { status: 500 }
    );
  }
}
