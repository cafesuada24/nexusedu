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
      className="relative py-10"
    >
      <div className="mx-auto w-full max-w-7xl px-4 md:px-6">
        <div className="mx-auto max-w-2xl text-center">
          <span className="text-xs font-semibold tracking-[0.2em] text-primary uppercase dark:text-blue-400">
            Cách hoạt động
          </span>
        </div>

        <ol className="mt-14 grid gap-6 md:grid-cols-2 lg:grid-cols-4">
          {steps.map((s, i) => (
            <li
              key={s.title}
              className="group relative rounded-2xl p-[1px] bg-gradient-to-br from-blue-500 to-cyan-400 dark:from-blue-700 dark:to-cyan-600 transition-all duration-300 hover:shadow-[0_0_20px_rgba(56,189,248,0.3)] hover:-translate-y-2 hover:scale-[1.02]"
            >
              <div className="h-full rounded-[14px] bg-white/60 dark:bg-slate-900/60 backdrop-blur-xl border border-white/20 dark:border-white/10 p-6">
                <span
                  aria-hidden="true"
                  className="absolute -top-3 left-6 rounded-md bg-primary dark:bg-blue-600 px-2 py-0.5 text-xs font-bold text-primary-foreground"
                >
                  Bước {i + 1}
                </span>
                <span className="inline-grid size-11 place-items-center rounded-xl bg-primary/10 dark:bg-slate-800 text-primary dark:text-blue-400 ring-1 ring-primary/15 dark:ring-blue-500/30 group-hover:bg-primary/20 transition-colors">
                  <s.icon className="size-5" aria-hidden="true" />
                </span>
                <h3 className="mt-5 font-serif text-lg font-bold text-foreground dark:text-white group-hover:text-blue-700 dark:group-hover:text-blue-400 transition-colors">
                  {s.title}
                </h3>
                <p className="mt-2 text-sm leading-relaxed text-muted-foreground dark:text-slate-300 group-hover:text-foreground dark:group-hover:text-white transition-colors">
                  {s.desc}
                </p>
              </div>
            </li>
          ))}
        </ol>
      </div>
    </section>
  )
}
