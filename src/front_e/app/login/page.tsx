import Link from "next/link"
import { ArrowLeft, Lock, Mail } from "lucide-react"
import { Logo } from "@/components/logo"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Separator } from "@/components/ui/separator"
import { ThemeToggle } from "@/components/theme-toggle"

export default function LoginPage() {
  return (
    <div className="hero-gradient relative flex min-h-screen flex-col">
      <header className="relative z-10 mx-auto flex w-full max-w-7xl items-center justify-between px-4 py-5 md:px-6">
        <Link
          href="/"
          className="inline-flex items-center gap-2 text-sm font-medium text-muted-foreground transition-colors hover:text-foreground"
        >
          <ArrowLeft className="size-4" />
          Về trang chủ
        </Link>
        <ThemeToggle />
      </header>

      <main className="relative z-10 flex flex-1 items-center justify-center px-4 py-10 md:px-6">
        <div className="w-full max-w-md">
          <div className="mb-6 flex justify-center">
            <Logo size="lg" href={null} />
          </div>

          <div className="glass-strong rounded-2xl border border-border/60 p-6 shadow-xl shadow-primary/10 md:p-8">
            <div className="text-center">
              <h1 className="font-serif text-2xl font-bold md:text-3xl">
                Chào mừng trở lại
              </h1>
              <p className="mt-2 text-sm text-muted-foreground">
                Đăng nhập bằng tài khoản nhà trường để tiếp tục.
              </p>
            </div>

            <div className="mt-7 grid gap-2.5">
              <Button
                variant="outline"
                size="lg"
                className="h-11 rounded-xl"
                aria-label="Đăng nhập bằng Google Workspace"
              >
                <GoogleIcon />
                Tiếp tục với Google Workspace
              </Button>
              <Button
                variant="outline"
                size="lg"
                className="h-11 rounded-xl"
                aria-label="Đăng nhập bằng Microsoft Workspace"
              >
                <MicrosoftIcon />
                Tiếp tục với Microsoft 365
              </Button>
            </div>

            <div className="my-6 flex items-center gap-3">
              <Separator className="flex-1" />
              <span className="text-xs text-muted-foreground">hoặc</span>
              <Separator className="flex-1" />
            </div>

            <form className="grid gap-4">
              <div className="grid gap-2">
                <Label htmlFor="email">Email trường</Label>
                <div className="relative">
                  <Mail
                    className="pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2 text-muted-foreground"
                    aria-hidden="true"
                  />
                  <Input
                    id="email"
                    type="email"
                    required
                    placeholder="giangvien@truong.edu.vn"
                    className="h-11 rounded-xl pl-9"
                  />
                </div>
              </div>
              <div className="grid gap-2">
                <div className="flex items-center justify-between">
                  <Label htmlFor="password">Mật khẩu</Label>
                  <Link
                    href="#"
                    className="text-xs font-medium text-primary hover:underline"
                  >
                    Quên mật khẩu?
                  </Link>
                </div>
                <div className="relative">
                  <Lock
                    className="pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2 text-muted-foreground"
                    aria-hidden="true"
                  />
                  <Input
                    id="password"
                    type="password"
                    required
                    placeholder="••••••••"
                    className="h-11 rounded-xl pl-9"
                  />
                </div>
              </div>

              <Button asChild size="lg" className="mt-2 h-11 rounded-xl">
                <Link href="/dashboard">Đăng nhập</Link>
              </Button>
            </form>

            <p className="mt-6 text-center text-xs text-muted-foreground">
              Bảo mật chuẩn SSO — dữ liệu sinh viên không bao giờ rời khỏi
              máy chủ trường.
            </p>
          </div>

          <p className="mt-6 text-center text-sm text-muted-foreground">
            Chưa có tài khoản?{" "}
            <Link
              href="#"
              className="font-medium text-primary hover:underline"
            >
              Liên hệ quản trị viên
            </Link>
          </p>
        </div>
      </main>
    </div>
  )
}

function GoogleIcon() {
  return (
    <svg viewBox="0 0 24 24" className="size-5" aria-hidden="true">
      <path
        fill="#EA4335"
        d="M12 10.2v3.9h5.5c-.2 1.4-1.7 4.2-5.5 4.2-3.3 0-6-2.7-6-6.1s2.7-6.1 6-6.1c1.9 0 3.1.8 3.8 1.5l2.6-2.5C16.9 3.7 14.7 2.8 12 2.8 6.9 2.8 2.8 6.9 2.8 12S6.9 21.2 12 21.2c6.9 0 9.2-4.9 9.2-7.3 0-.5-.1-.9-.1-1.3H12z"
      />
    </svg>
  )
}

function MicrosoftIcon() {
  return (
    <svg viewBox="0 0 24 24" className="size-5" aria-hidden="true">
      <path fill="#F25022" d="M3 3h8v8H3z" />
      <path fill="#7FBA00" d="M13 3h8v8h-8z" />
      <path fill="#00A4EF" d="M3 13h8v8H3z" />
      <path fill="#FFB900" d="M13 13h8v8h-8z" />
    </svg>
  )
}
