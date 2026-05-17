"use client"

import * as React from "react"
import { Star, CheckCircle2, Loader2 } from "lucide-react"
import { toast } from "sonner"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Textarea } from "@/components/ui/textarea"
import { cn } from "@/lib/utils"
import { submitFeedback, type StudentSatisfaction } from "@/lib/api"

const RATING_LABELS = ["", "Không hài lòng", "Tạm được", "Ổn", "Hài lòng", "Rất hài lòng"]

type Submitting = "none" | "resolved"
type Stage = "form" | "done_resolved"

function toSatisfaction(rating: number, resolved: boolean): StudentSatisfaction {
  if (!resolved) return "very_bad"
  if (rating <= 1) return "very_bad"
  if (rating === 2) return "bad"
  if (rating === 3) return "normal"
  if (rating === 4) return "good"
  return "very_good"
}

export function FeedbackView({ token }: { token: string }) {
  const [rating, setRating] = React.useState(0)
  const [hovered, setHovered] = React.useState(0)
  const [comment, setComment] = React.useState("")
  const [submitting, setSubmitting] = React.useState<Submitting>("none")
  const [stage, setStage] = React.useState<Stage>("form")
  const active = hovered || rating
  const mountedRef = React.useRef(true)

  React.useEffect(() => {
    return () => { mountedRef.current = false }
  }, [])

  const handleResolved = async () => {
    if (rating === 0) {
      toast.error("Vui lòng chọn số sao trước khi xác nhận đã giải quyết.")
      return
    }
    setSubmitting("resolved")
    try {
      await submitFeedback(token, toSatisfaction(rating, true), comment.trim() || null)
      await new Promise((r) => setTimeout(r, 400))
      if (mountedRef.current) setStage("done_resolved")
    } catch {
      if (mountedRef.current) setSubmitting("none")
      toast.error("Không thể gửi xác nhận. Vui lòng thử lại sau.")
    }
  }

  if (stage === "done_resolved") {
    return (
      <Card className="rounded-2xl border-success/30 bg-success/5">
        <CardContent className="flex flex-col items-center gap-4 p-10 text-center">
          <span className="grid size-16 place-items-center rounded-2xl bg-success/15 text-success">
            <CheckCircle2 className="size-8" />
          </span>
          <div>
            <h2 className="font-serif text-2xl font-bold">Cảm ơn bạn đã xác nhận!</h2>
            <p className="mt-2 text-sm text-muted-foreground">
              Phản hồi tích cực của bạn đã được gửi tới cố vấn. Chúc bạn học tập hiệu quả!
            </p>
          </div>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card className="rounded-2xl border-border/60">
      <CardHeader>
        <CardTitle className="font-serif text-xl">Đánh giá quá trình hỗ trợ</CardTitle>
        <CardDescription>
          Hãy cho chúng tôi biết tình hình của bạn sau buổi hỗ trợ.
        </CardDescription>
      </CardHeader>
      <CardContent className="grid gap-6">
        <div className="flex flex-col items-center gap-3">
          <div className="flex gap-1">
            {[1, 2, 3, 4, 5].map((n) => (
              <button
                key={n}
                type="button"
                onClick={() => setRating(n)}
                onMouseEnter={() => setHovered(n)}
                onMouseLeave={() => setHovered(0)}
                aria-label={`${n} sao`}
                className="p-1 transition-transform hover:scale-110 focus:outline-none"
              >
                <Star
                  className={cn(
                    "size-10 transition-colors",
                    n <= active
                      ? "fill-amber-400 text-amber-400"
                      : "fill-muted text-muted-foreground/40",
                  )}
                />
              </button>
            ))}
          </div>
          <p className={cn("h-5 text-sm font-medium transition-opacity", active ? "opacity-100" : "opacity-0")}>
            {RATING_LABELS[active]}
          </p>
        </div>

        <div className="grid gap-2">
          <label htmlFor="comment" className="text-sm font-medium">
            Nhận xét / Lý do
          </label>
          <Textarea
            id="comment"
            value={comment}
            onChange={(e) => setComment(e.target.value)}
            placeholder="Chia sẻ thêm về trải nghiệm hoặc vấn đề chưa được giải quyết..."
            className="min-h-[100px] resize-none rounded-xl"
            maxLength={500}
          />
          <p className="text-right text-xs text-muted-foreground">{comment.length}/500</p>
        </div>

        <div className="grid gap-2">
          <Button
            className="h-11 rounded-xl bg-success text-success-foreground hover:bg-success/90"
            disabled={submitting !== "none"}
            onClick={handleResolved}
          >
            {submitting === "resolved" ? (
              <>
                <Loader2 className="size-4 animate-spin" />
                Đang gửi...
              </>
            ) : (
              <>
                <CheckCircle2 className="size-4" />
                Đã giải quyết xong
              </>
            )}
          </Button>
        </div>
      </CardContent>
    </Card>
  )
}
