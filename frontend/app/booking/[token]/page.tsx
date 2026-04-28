import { Sparkles } from "lucide-react"
import { Badge } from "@/components/ui/badge"
import { BookingView } from "@/components/booking/booking-view"
import { PublicBookingHeader } from "@/components/booking/public-header"

// Demo-only "token → advisor" lookup. In production this would be a signed,
// one-time link that resolves to the student + advisor on the server.
const advisors: Record<
  string,
  { advisor: string; role: string; student?: string }
> = {
  "le-ha": {
    advisor: "TS. Lê Hà",
    role: "Cố vấn học tập · Khoa CNTT",
  },
}

export default async function PublicBookingPage({
  params,
}: {
  params: Promise<{ token: string }>
}) {
  const { token } = await params
  const meta = advisors[token] ?? {
    advisor: "Cố vấn học tập",
    role: "NexusEdu",
  }

  return (
    <div className="flex min-h-screen flex-col bg-muted/30">
      <PublicBookingHeader />
      <main className="flex-1">
        <div className="mx-auto flex w-full max-w-6xl flex-col gap-6 px-4 py-8 md:px-6 md:py-12">
          <div className="flex flex-col gap-3">
            <Badge
              variant="secondary"
              className="w-fit rounded-md bg-primary/10 text-primary hover:bg-primary/10"
            >
              <Sparkles className="size-3" />
              Lời mời cá nhân từ cố vấn của bạn
            </Badge>
            <h1 className="font-serif text-3xl font-bold tracking-tight text-balance md:text-4xl">
              Chọn một khung giờ phù hợp với {meta.advisor}
            </h1>
            <p className="max-w-2xl text-sm text-muted-foreground text-pretty md:text-base">
              Buổi gặp kéo dài khoảng 30 phút — hoàn toàn tự nguyện, riêng tư,
              và không có gì đáng lo. Bạn có thể đổi giờ hoặc huỷ bất cứ lúc
              nào.
            </p>
          </div>

          <BookingView />

          <p className="text-xs text-muted-foreground">
            Nếu bạn không phải là người được mời qua email này, bạn có thể bỏ
            qua trang này. NexusEdu không chia sẻ dữ liệu của bạn với bên thứ
            ba.
          </p>
        </div>
      </main>
    </div>
  )
}
