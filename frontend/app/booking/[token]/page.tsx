import { Sparkles, AlertCircle } from "lucide-react"
import { Badge } from "@/components/ui/badge"
import { BookingView } from "@/components/booking/booking-view"
import { PublicBookingHeader } from "@/components/booking/public-header"
import { Button } from "@/components/ui/button"
import Link from "next/link"

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
  searchParams,
}: {
  params: Promise<{ token: string }>
  searchParams: Promise<{ [key: string]: string | string[] | undefined }>
}) {
  const { token } = await params
  const { cid } = await searchParams

  const meta = advisors[token] ?? {
    advisor: "Cố vấn học tập",
    role: "NexusEdu",
  }

  const caseId = typeof cid === "string" ? cid : undefined
  const studentName = undefined // Mock student lookup by SID is deprecated here


  if (!caseId) {
    return (
      <div className="flex min-h-screen flex-col bg-muted/30">
        <PublicBookingHeader />
        <main className="flex flex-1 items-center justify-center p-6 text-center">
          <div className="max-w-md space-y-4 rounded-2xl border border-destructive/20 bg-destructive/5 p-8 shadow-sm">
            <div className="mx-auto grid size-12 place-items-center rounded-xl bg-destructive/10 text-destructive">
              <AlertCircle className="size-6" />
            </div>
            <h1 className="text-xl font-bold text-destructive">
              Liên kết không hợp lệ
            </h1>
            <p className="text-sm text-muted-foreground">
              Vui lòng sử dụng liên kết đặt lịch được gửi trực tiếp đến email
              của bạn. Nếu bạn cho rằng đây là lỗi, hãy liên hệ với cố vấn học
              tập.
            </p>
            <Button asChild className="rounded-xl">
              <Link href="/">Quay lại trang chủ</Link>
            </Button>
          </div>
        </main>
      </div>
    )
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
              Chào {studentName || "bạn"}, hãy chọn một khung giờ phù hợp với{" "}
              {meta.advisor}
            </h1>
            <p className="max-w-2xl text-sm text-muted-foreground text-pretty md:text-base">
              Buổi gặp kéo dài khoảng 30 phút — hoàn toàn tự nguyện, riêng tư,
              và không có gì đáng lo. Bạn có thể đổi giờ hoặc huỷ bất cứ lúc
              nào.
            </p>
          </div>

          <BookingView studentId={caseId} studentName={studentName} />

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
