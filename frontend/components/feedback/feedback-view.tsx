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
import { submitFeedback } from "@/lib/api"

const RATING_LABELS = ["", "Không hài lòng", "Tạm được", "Ổn", "Hài lòng", "Rất hài lòng"]

export function FeedbackView({ caseId }: { caseId: string }) {
  const [rating, setRating] = React.useState(0)
  const [hovered, setHovered] = React.useState(0)
  const [comment, setComment] = React.useState("")
  const [stage, setStage] = React.useState<"form" | "submitting" | "done">("form")

  const active = hovered || rating

  const submit = async () => {
    if (rating === 0) return
    setStage("submitting")
    try {
      await submitFeedback(caseId, rating, comment.trim() || null)
      setStage("done")
    } catch (err) {
      setStage("form")
      toast.error("Không thể gửi đánh giá. Vui lòng thử lại sau.", {
        description: err instanceof Error ? err.message : undefined,
      })
    }
  }

  if (stage === "done") {
    return (
      <Card className="rounded-2xl border-success/30 bg-success/5">
        <CardContent className="flex flex-col items-center gap-4 p-10 text-center">
          <span className="grid size-16 place-items-center rounded-2xl bg-success/15 text-success">
            <CheckCircle2 className="size-8" />
          </span>
          <div>
            <h2 className="font-serif text-2xl font-bold">Cảm ơn bạn đã đánh giá!</h2>
            <p className="mt-2 text-sm text-muted-foreground">
              Phản hồi của bạn giúp chúng tôi cải thiện chất lượng hỗ trợ học tập.
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
          Ý kiến của bạn rất quan trọng để cải thiện chất lượng dịch vụ.
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
            Nhận xét thêm{" "}
            <span className="font-normal text-muted-foreground">(không bắt buộc)</span>
          </label>
          <Textarea
            id="comment"
            value={comment}
            onChange={(e) => setComment(e.target.value)}
            placeholder="Chia sẻ thêm về trải nghiệm của bạn..."
            className="min-h-[100px] resize-none rounded-xl"
            maxLength={500}
          />
          <p className="text-right text-xs text-muted-foreground">{comment.length}/500</p>
        </div>

        <Button
          className="h-11 rounded-xl text-sm font-medium"
          disabled={rating === 0 || stage === "submitting"}
          onClick={submit}
        >
          {stage === "submitting" ? (
            <>
              <Loader2 className="size-4 animate-spin" />
              Đang gửi...
            </>
          ) : (
            "Gửi đánh giá"
          )}
        </Button>
      </CardContent>
    </Card>
  )
}
