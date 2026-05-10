import Link from "next/link"
import { ShieldCheck } from "lucide-react"
import { Logo } from "@/components/logo"

export function PublicBookingHeader() {
  return (
    <header className="sticky top-0 z-30 border-b border-border/60 bg-background/80 backdrop-blur">
      <div className="mx-auto flex h-16 w-full max-w-6xl items-center justify-between px-4 md:px-6">
        <Logo size="sm" priority />
        <div className="flex items-center gap-2 text-xs text-muted-foreground">
          <ShieldCheck className="size-3.5 text-success" />
          <span className="hidden sm:inline">
            Liên kết riêng tư · chỉ dành cho sinh viên được mời
          </span>
          <span className="sm:hidden">Liên kết riêng tư</span>
        </div>
      </div>
    </header>
  )
}
