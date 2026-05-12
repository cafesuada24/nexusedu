import type { Metadata, Viewport } from "next";
import { Analytics } from "@vercel/analytics/next";
import { Providers } from "@/components/providers";
import "./globals.css";

// We intentionally avoid next/font/google in dev to reduce server-side
// font fetching overhead. Fonts are provided via CSS variables in
// globals.css (fallback to system fonts).

export const metadata: Metadata = {
  title: "NexusEdu — Hệ sinh thái AI hỗ trợ đào tạo và quản lý sinh viên",
  description:
    "NexusEdu là nền tảng AI phát hiện sớm sinh viên có nguy cơ, hỗ trợ cố vấn học tập gửi email chăm sóc và đặt lịch tư vấn thông minh.",
  keywords: [
    "NexusEdu",
    "AI giáo dục",
    "cố vấn học tập",
    "student success",
    "advisor booking",
  ],
};

export const viewport: Viewport = {
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: "#ffffff" },
    { media: "(prefers-color-scheme: dark)", color: "#0b1220" },
  ],
  width: "device-width",
  initialScale: 1,
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="vi" suppressHydrationWarning>
      <head />
      <body className="font-sans antialiased bg-background" suppressHydrationWarning>
        <Providers>{children}</Providers>
        {process.env.NODE_ENV === "production" && <Analytics />}
      </body>
    </html>
  );
}
