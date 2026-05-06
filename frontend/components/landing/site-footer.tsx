import Link from "next/link"
import { Logo } from "@/components/logo"

const cols = [
  {
    title: "Sản phẩm",
    links: [
      { href: "#features", label: "Tính năng" },
      { href: "#how", label: "Cách hoạt động" },
      { href: "#metrics", label: "Hiệu quả" },
    ],
  },
  {
    title: "Tài liệu",
    links: [
      { href: "#", label: "Hướng dẫn CSV" },
      { href: "#", label: "Bảo mật dữ liệu" },
      { href: "#", label: "Trung tâm hỗ trợ" },
    ],
  },
  {
    title: "Công ty",
    links: [
      { href: "#", label: "Về NexusEdu" },
      { href: "#", label: "Liên hệ" },
    ],
  },
]

export function SiteFooter() {
  return (
    <footer className="border-t border-border/60 bg-background">
      <div className="mx-auto w-full max-w-7xl px-4 py-14 md:px-6">
        <div className="grid gap-10 md:grid-cols-4">
          <div>
            <Logo />
            <p className="mt-4 max-w-xs text-sm text-muted-foreground">
              AI đồng hành, gắn kết tình thầy trò. Giúp nhà trường hiểu và
              chăm sóc sinh viên đúng lúc.
            </p>
          </div>
          {cols.map((c) => (
            <div key={c.title}>
              <h3 className="text-sm font-semibold">{c.title}</h3>
              <ul className="mt-4 space-y-2.5">
                {c.links.map((l) => (
                  <li key={l.label}>
                    <Link
                      href={l.href}
                      className="text-sm text-muted-foreground transition-colors hover:text-foreground"
                    >
                      {l.label}
                    </Link>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>

        <div className="mt-12 flex flex-col items-center justify-between gap-3 border-t border-border/60 pt-6 text-xs text-muted-foreground md:flex-row">
          <p>© {new Date().getFullYear()} NexusEdu. Bảo lưu mọi quyền.</p>
          <p>
            Thiết kế cho các trường đại học Việt Nam với{" "}
            <span className="text-primary">❤</span>
          </p>
        </div>
      </div>
    </footer>
  )
}
