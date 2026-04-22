import { BrainCircuit, MailCheck, CalendarClock, LineChart, ShieldCheck, Users } from "lucide-react"

const features = [
  {
    icon: BrainCircuit,
    title: "AI Analysis",
    desc: "Mô hình máy học phân tích điểm danh, điểm số và tài chính để phát hiện sớm sinh viên có nguy cơ — trước khi quá muộn.",
  },
  {
    icon: MailCheck,
    title: "HIL Emailing",
    desc: "AI soạn email chăm sóc nhẹ nhàng theo từng tình huống. Cố vấn xem, chỉnh và gửi — con người luôn là người quyết định.",
  },
  {
    icon: CalendarClock,
    title: "Smart Booking",
    desc: "Đồng bộ Google / School Calendar. Sinh viên chọn khung giờ phù hợp chỉ trong vài cú chạm, không email qua lại.",
  },
  {
    icon: LineChart,
    title: "BGH Dashboard",
    desc: "Biểu đồ trực quan về tỷ lệ giữ chân, mức độ tham gia của cố vấn và hiệu quả can thiệp theo khoa.",
  },
  {
    icon: ShieldCheck,
    title: "Privacy-first",
    desc: "Dữ liệu sinh viên được mã hoá, phân quyền chi tiết theo vai trò (SV / Cố vấn / BGH).",
  },
  {
    icon: Users,
    title: "Advisor Leaderboard",
    desc: "Ghi nhận nỗ lực của cố vấn năng động nhất — tạo động lực lan toả văn hoá quan tâm.",
  },
]

export function Features() {
  return (
    <section
      id="features"
      className="relative border-t border-border/60 bg-background py-20 md:py-28"
    >
      <div className="mx-auto w-full max-w-7xl px-4 md:px-6">
        <div className="mx-auto max-w-2xl text-center">
          <span className="text-xs font-semibold tracking-[0.2em] text-primary uppercase">
            Tính năng cốt lõi
          </span>
          <h2 className="mt-3 text-balance font-serif text-3xl font-black tracking-tight md:text-5xl">
            Một nền tảng, đủ cho hành trình đồng hành sinh viên.
          </h2>
          <p className="mt-4 text-pretty text-muted-foreground md:text-lg">
            Kết hợp sức mạnh AI và sự tinh tế của con người để không sinh viên
            nào bị bỏ lại phía sau.
          </p>
        </div>

        <div className="mt-14 grid gap-5 md:grid-cols-2 lg:grid-cols-3">
          {features.map((f) => (
            <article
              key={f.title}
              className="group relative overflow-hidden rounded-2xl border border-border/60 bg-card p-6 shadow-sm transition-all hover:-translate-y-0.5 hover:border-primary/30 hover:shadow-lg hover:shadow-primary/10"
            >
              <div
                aria-hidden="true"
                className="pointer-events-none absolute -top-16 -right-16 size-40 rounded-full bg-primary/10 blur-2xl transition-opacity group-hover:opacity-100 opacity-60"
              />
              <div className="relative">
                <span className="inline-grid size-11 place-items-center rounded-xl bg-primary/10 text-primary ring-1 ring-primary/15">
                  <f.icon className="size-5" aria-hidden="true" />
                </span>
                <h3 className="mt-5 font-serif text-xl font-bold">{f.title}</h3>
                <p className="mt-2 text-sm leading-relaxed text-muted-foreground">
                  {f.desc}
                </p>
              </div>
            </article>
          ))}
        </div>
      </div>
    </section>
  )
}
