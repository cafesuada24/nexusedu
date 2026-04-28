const numbers = [
  { value: "−38%", label: "Tỷ lệ bỏ học sau 1 kỳ triển khai" },
  { value: "3.2x", label: "Email chăm sóc gửi mỗi tuần" },
  { value: "40h", label: "Giờ tiết kiệm cho mỗi cố vấn/tháng" },
  { value: "92%", label: "Sinh viên hài lòng với tư vấn" },
]

export function Metrics() {
  return (
    <section
      id="metrics"
      className="relative border-t border-border/60 bg-background py-20 md:py-28"
    >
      <div className="mx-auto w-full max-w-7xl px-4 md:px-6">
        <div className="rounded-3xl border border-primary/20 bg-gradient-to-br from-primary/10 via-primary/5 to-transparent p-8 md:p-14">
          <div className="mx-auto max-w-2xl text-center">
            <h2 className="text-balance font-serif text-3xl font-black tracking-tight md:text-5xl">
              Kết quả thực tế từ các trường tiên phong.
            </h2>
            <p className="mt-4 text-pretty text-muted-foreground md:text-lg">
              Được đo lường trên hơn 12,000 sinh viên tại 6 khoa khác nhau.
            </p>
          </div>

          <dl className="mt-10 grid grid-cols-2 gap-4 md:grid-cols-4 md:gap-6">
            {numbers.map((n) => (
              <div
                key={n.label}
                className="rounded-2xl border border-border/60 bg-card p-6 text-center shadow-sm"
              >
                <dt className="sr-only">{n.label}</dt>
                <dd>
                  <span className="block font-serif text-4xl font-black text-primary md:text-5xl">
                    {n.value}
                  </span>
                  <span className="mt-2 block text-sm text-muted-foreground">
                    {n.label}
                  </span>
                </dd>
              </div>
            ))}
          </dl>
        </div>
      </div>
    </section>
  )
}
