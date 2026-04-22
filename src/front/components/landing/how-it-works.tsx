import { FileSpreadsheet, Cpu, Send, CalendarCheck2 } from "lucide-react"

const steps = [
  {
    icon: FileSpreadsheet,
    title: "Nhập danh sách CSV",
    desc: "Tải lên bảng điểm, điểm danh, trạng thái học phí. Không cần tích hợp phức tạp.",
  },
  {
    icon: Cpu,
    title: "AI phân tích nguy cơ",
    desc: "Mô hình đánh giá và xếp hạng sinh viên có nguy cơ theo từng nhóm vấn đề.",
  },
  {
    icon: Send,
    title: "Cố vấn gửi email HIL",
    desc: "Xem bản nháp AI, chỉnh lại giọng điệu, gửi — con người luôn là người quyết định.",
  },
  {
    icon: CalendarCheck2,
    title: "Sinh viên đặt lịch",
    desc: "Chọn khung giờ trống của cố vấn, đồng bộ tự động với Google Calendar.",
  },
]

export function HowItWorks() {
  return (
    <section
      id="how"
      className="relative border-t border-border/60 bg-muted/30 py-20 md:py-28"
    >
      <div className="mx-auto w-full max-w-7xl px-4 md:px-6">
        <div className="mx-auto max-w-2xl text-center">
          <span className="text-xs font-semibold tracking-[0.2em] text-primary uppercase">
            Cách hoạt động
          </span>
          <h2 className="mt-3 text-balance font-serif text-3xl font-black tracking-tight md:text-5xl">
            Bốn bước, từ dữ liệu đến cuộc trò chuyện.
          </h2>
        </div>

        <ol className="mt-14 grid gap-5 md:grid-cols-2 lg:grid-cols-4">
          {steps.map((s, i) => (
            <li
              key={s.title}
              className="relative rounded-2xl border border-border/60 bg-card p-6 shadow-sm"
            >
              <span
                aria-hidden="true"
                className="absolute -top-3 left-6 rounded-md bg-primary px-2 py-0.5 text-xs font-bold text-primary-foreground"
              >
                Bước {i + 1}
              </span>
              <span className="inline-grid size-11 place-items-center rounded-xl bg-primary/10 text-primary ring-1 ring-primary/15">
                <s.icon className="size-5" aria-hidden="true" />
              </span>
              <h3 className="mt-5 font-serif text-lg font-bold">{s.title}</h3>
              <p className="mt-2 text-sm leading-relaxed text-muted-foreground">
                {s.desc}
              </p>
            </li>
          ))}
        </ol>
      </div>
    </section>
  )
}
