import Link from "next/link"
import { ArrowRight, Sparkles, ShieldCheck, Users } from "lucide-react"
import { Button } from "@/components/ui/button"

export function Hero() {
  return (
    <section className="hero-gradient relative overflow-hidden">
      <div
        aria-hidden="true"
        className="pointer-events-none absolute inset-0 [mask-image:radial-gradient(60%_50%_at_50%_0%,black,transparent)]"
      >
        <div className="absolute inset-x-0 top-0 h-[420px] bg-[radial-gradient(closest-side,color-mix(in_oklab,var(--primary)_35%,transparent),transparent)]" />
      </div>

      <div className="relative mx-auto w-full max-w-7xl px-4 pt-16 pb-20 md:px-6 md:pt-24 md:pb-28">
        <div className="mx-auto max-w-3xl text-center">
          <span className="inline-flex items-center gap-2 rounded-full border border-primary/20 bg-primary/10 px-3 py-1 text-xs font-medium text-primary backdrop-blur">
            <Sparkles className="size-3.5" aria-hidden="true" />
            AI phát hiện sớm · HIL tin cậy · Đặt lịch thông minh
          </span>

          <h1 className="mt-6 text-balance font-serif text-4xl font-black tracking-tight text-foreground md:text-6xl">
            NexusEdu: <span className="text-primary">AI đồng hành</span>, gắn kết tình thầy trò.
          </h1>

          <p className="mt-6 text-pretty text-base leading-relaxed text-muted-foreground md:text-lg">
            Nền tảng AI giúp nhà trường phát hiện sớm sinh viên có nguy cơ bỏ
            học, soạn email chăm sóc nhẹ nhàng và đặt lịch tư vấn với cố vấn
            học tập — tất cả trong một luồng Human-in-the-Loop đáng tin cậy.
          </p>

          <div className="mt-8 flex flex-col items-center justify-center gap-3 sm:flex-row">
            <Button asChild size="lg" className="h-12 rounded-xl px-6 text-base">
              <Link href="/dashboard">
                Bắt đầu với CSV
                <ArrowRight className="size-4" />
              </Link>
            </Button>
            <Button
              asChild
              size="lg"
              variant="outline"
              className="h-12 rounded-xl px-6 text-base"
            >
              <Link href="#features">Xem tính năng</Link>
            </Button>
          </div>

          <dl className="mx-auto mt-10 grid max-w-2xl grid-cols-3 gap-4 text-left sm:gap-6">
            <Stat icon={<Users className="size-4" />} value="12k+" label="Sinh viên theo dõi" />
            <Stat icon={<ShieldCheck className="size-4" />} value="98%" label="Email được phê duyệt" />
            <Stat icon={<Sparkles className="size-4" />} value="40h" label="Tiết kiệm mỗi tuần" />
          </dl>
        </div>

        <div className="relative mx-auto mt-14 max-w-5xl">
          <div className="glass rounded-2xl border border-border/60 p-2 shadow-2xl shadow-primary/10">
            <div className="overflow-hidden rounded-xl border border-border/60 bg-card">
              <div className="flex items-center gap-1.5 border-b border-border/60 px-4 py-2.5">
                <span className="size-2.5 rounded-full bg-destructive/70" />
                <span className="size-2.5 rounded-full bg-warning/70" />
                <span className="size-2.5 rounded-full bg-success/70" />
                <span className="ml-3 text-xs text-muted-foreground">
                  nexus.edu/dashboard
                </span>
              </div>
              <HeroMock />
            </div>
          </div>
        </div>
      </div>
    </section>
  )
}

function Stat({
  icon,
  value,
  label,
}: {
  icon: React.ReactNode
  value: string
  label: string
}) {
  return (
    <div className="rounded-xl border border-border/60 bg-card/60 p-3 backdrop-blur">
      <dt className="flex items-center gap-2 text-xs text-muted-foreground">
        <span className="grid size-6 place-items-center rounded-md bg-primary/10 text-primary">
          {icon}
        </span>
        {label}
      </dt>
      <dd className="mt-1 font-serif text-2xl font-bold text-foreground">
        {value}
      </dd>
    </div>
  )
}

function HeroMock() {
  return (
    <div className="grid gap-4 p-4 md:grid-cols-3 md:p-6">
      <div className="rounded-xl border border-border/60 bg-background/60 p-4">
        <p className="text-xs font-medium text-muted-foreground">Sinh viên nguy cơ</p>
        <p className="mt-1 font-serif text-2xl font-bold">128</p>
        <div className="mt-3 h-16 rounded-md bg-gradient-to-t from-primary/20 to-primary/5" />
      </div>
      <div className="rounded-xl border border-border/60 bg-background/60 p-4">
        <p className="text-xs font-medium text-muted-foreground">Email chờ duyệt</p>
        <p className="mt-1 font-serif text-2xl font-bold">23</p>
        <ul className="mt-3 space-y-1.5 text-xs">
          <li className="flex items-center justify-between rounded-md bg-primary/5 px-2 py-1.5">
            <span className="truncate">Nguyễn An · Học phí</span>
            <span className="text-primary">AI</span>
          </li>
          <li className="flex items-center justify-between rounded-md bg-primary/5 px-2 py-1.5">
            <span className="truncate">Trần Bình · Điểm GK</span>
            <span className="text-primary">AI</span>
          </li>
        </ul>
      </div>
      <div className="rounded-xl border border-border/60 bg-background/60 p-4">
        <p className="text-xs font-medium text-muted-foreground">Tỷ lệ giữ chân</p>
        <p className="mt-1 font-serif text-2xl font-bold">94.2%</p>
        <div className="mt-3 flex h-16 items-end gap-1">
          {[40, 55, 48, 70, 62, 80, 74].map((h, i) => (
            <span
              key={i}
              className="flex-1 rounded-sm bg-primary/70"
              style={{ height: `${h}%` }}
            />
          ))}
        </div>
      </div>
    </div>
  )
}
