import { AlertCircle, Star } from "lucide-react"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { FeedbackView } from "@/components/feedback/feedback-view"
import { PublicBookingHeader } from "@/components/booking/public-header"
import Link from "next/link"

const ADVISOR_META: Record<string, { advisor: string; role: string }> = {
  "le-ha": {
    advisor: "TS. Lê Hà",
    role: "Cố vấn học tập · Khoa CNTT",
  },
}

function decodeJwtPayload(
  token: string,
): { case_id?: string; advisor?: string } | null {
  try {
    const payload = token.split(".")[1]
    return JSON.parse(Buffer.from(payload, "base64url").toString("utf8"))
  } catch {
    return null
  }
}

export default async function PublicFeedbackPage({
  searchParams,
}: {
  searchParams: Promise<{ [key: string]: string | string[] | undefined }>
}) {
  const { token } = await searchParams
  const raw = typeof token === "string" ? token : undefined

  const claims = raw ? decodeJwtPayload(raw) : null
  const meta =
    ADVISOR_META[claims?.advisor ?? ""] ?? ADVISOR_META["le-ha"]

  if (!raw || !claims?.case_id) {
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
              Vui lòng sử dụng liên kết đánh giá được gửi trực tiếp đến email
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
        <div className="mx-auto flex w-full max-w-2xl flex-col gap-6 px-4 py-8 md:px-6 md:py-12">
          <div className="flex flex-col gap-3">
            <Badge
              variant="secondary"
              className="w-fit rounded-md bg-primary/10 text-primary hover:bg-primary/10"
            >
              <Star className="size-3" />
              Đánh giá quá trình hỗ trợ từ {meta.advisor}
            </Badge>
            <h1 className="font-serif text-3xl font-bold tracking-tight text-balance md:text-4xl">
              Bạn cảm thấy thế nào sau buổi hỗ trợ?
            </h1>
            <p className="max-w-xl text-sm text-muted-foreground text-pretty md:text-base">
              Phản hồi của bạn hoàn toàn bảo mật và giúp {meta.advisor} cải
              thiện chất lượng hỗ trợ cho các sinh viên khác.
            </p>
          </div>

          <FeedbackView token={raw} />

          <p className="text-xs text-muted-foreground">
            Nếu bạn không phải là người nhận được yêu cầu đánh giá này, bạn có
            thể bỏ qua trang này. NexusEdu không chia sẻ dữ liệu của bạn với
            bên thứ ba.
          </p>
        </div>
      </main>
    </div>
  )
}
