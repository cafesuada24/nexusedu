import Link from "next/link"

export function DashboardFooter() {
  return (
    <footer className="mt-auto border-t border-border/60 bg-muted/30">
      <div className="flex flex-col gap-3 px-4 py-4 text-xs text-muted-foreground md:flex-row md:items-center md:justify-between md:px-6">
        <div className="flex flex-wrap items-center gap-x-4 gap-y-1">
          <span className="font-medium text-foreground">
            <span className="font-sans font-bold tracking-tighter">
              <span className="text-[#2563eb]">Nexus</span>
              <span className="text-[#f97316]">Edu</span>
            </span>{" "}&copy; {new Date().getFullYear()}
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
