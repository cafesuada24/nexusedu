import Link from "next/link"
import { ShieldCheck, HeartPulse } from "lucide-react"

export function DashboardFooter() {
  return (
    <footer className="mt-auto border-t border-border/60 bg-muted/30">
      <div className="flex flex-col gap-3 px-4 py-4 text-xs text-muted-foreground md:flex-row md:items-center md:justify-between md:px-6">
        <div className="flex flex-wrap items-center gap-x-4 gap-y-1">
          <span className="font-medium text-foreground">
            <span className="font-sans font-bold tracking-tighter bg-gradient-to-r from-[#2563eb] to-[#f97316] bg-clip-text text-transparent">NexusEdu</span>{" "}&copy; {new Date().getFullYear()}
          </span>
          <span className="hidden md:inline text-border">|</span>
          <span className="inline-flex items-center gap-1.5">
            <ShieldCheck className="size-3.5 text-primary" />
            Dữ liệu lưu tại Singapore &middot; Mã hoá AES-256
          </span>
          <span className="hidden md:inline text-border">|</span>
          <span className="inline-flex items-center gap-1.5">
            <HeartPulse className="size-3.5 text-emerald-500" />
            Hệ thống ổn định
          </span>
        </div>

        <nav className="flex flex-wrap items-center gap-x-4 gap-y-1">
          <Link href="/dashboard/support" className="hover:text-foreground">
            Hỗ trợ
          </Link>
          <Link href="/dashboard/settings" className="hover:text-foreground">
            Cài đặt
          </Link>
          <Link href="#" className="hover:text-foreground">
            Chính sách bảo mật
          </Link>
          <Link href="#" className="hover:text-foreground">
            Điều khoản
          </Link>
          <span className="font-mono text-[11px]">v2.4.1</span>
        </nav>
      </div>
    </footer>
  )
}
