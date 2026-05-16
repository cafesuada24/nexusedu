import type { Metadata, Viewport } from "next";
import { Plus_Jakarta_Sans, JetBrains_Mono } from "next/font/google";
import { Analytics } from "@vercel/analytics/next";
import { Providers } from "@/components/providers";
import "./globals.css";

const fontSans = Plus_Jakarta_Sans({
  subsets: ["latin", "latin-ext", "vietnamese"],
  variable: "--font-jakarta",
  weight: ["300", "400", "500", "600", "700", "800"],
  display: "swap",
});

const fontMono = JetBrains_Mono({
  subsets: ["latin"],
  variable: "--font-jetbrains",
  weight: ["400", "500"],
  display: "swap",
});

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
  icons: {
    icon: "/logos/logo.png",
  },
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
    <html lang="vi" suppressHydrationWarning className={`${fontSans.variable} ${fontMono.variable}`}>
      <head />
      <body className="font-sans antialiased bg-background" suppressHydrationWarning>
        <Providers>{children}</Providers>
        {process.env.NODE_ENV === "production" && <Analytics />}
      </body>
    </html>
  );
}
