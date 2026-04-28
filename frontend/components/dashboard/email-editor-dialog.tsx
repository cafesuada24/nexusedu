"use client"

import * as React from "react"
import Link from "next/link"
import { Sparkles, Send, RotateCcw, CalendarDays, ExternalLink } from "lucide-react"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import { Badge } from "@/components/ui/badge"

import { type Alert } from "@/lib/alerts"

type Props = {
  alert: Alert | null
  onClose: () => void
  onSave: (a: Alert) => void
}

export function EmailEditorDialog({ alert, onClose, onSave }: Props) {
  const [subject, setSubject] = React.useState("")
  const [body, setBody] = React.useState("")

  React.useEffect(() => {
    if (alert) {
      setSubject(alert.subject)
      setBody(alert.body)
    }
  }, [alert])

  const reset = () => {
    if (alert) {
      setSubject(alert.subject)
      setBody(alert.body)
    }
  }

  return (
    <Dialog open={!!alert} onOpenChange={(o) => !o && onClose()}>
      <DialogContent className="max-w-2xl rounded-2xl">
        <DialogHeader>
          <div className="flex items-center gap-2">
            <Badge
              variant="secondary"
              className="rounded-md bg-primary/10 text-primary hover:bg-primary/10"
            >
              <Sparkles className="size-3" />
              AI draft
            </Badge>
            {alert && (
              <Badge variant="outline" className="rounded-md">
                {alert.name} · MSSV {alert.mssv}
              </Badge>
            )}
          </div>
          <DialogTitle className="font-serif text-xl">
            Chỉnh sửa email
          </DialogTitle>
          <DialogDescription>
            Giữ giọng điệu nhẹ nhàng, đồng cảm. Bạn luôn là người quyết định
            gửi.
          </DialogDescription>
        </DialogHeader>

        <div className="grid gap-4 py-2">
          <div className="grid gap-2">
            <Label htmlFor="subject">Tiêu đề</Label>
            <Input
              id="subject"
              value={subject}
              onChange={(e) => setSubject(e.target.value)}
              className="rounded-xl"
            />
          </div>
          <div className="grid gap-2">
            <Label htmlFor="body">Nội dung</Label>
            <Textarea
              id="body"
              value={body}
              onChange={(e) => setBody(e.target.value)}
              rows={12}
              className="resize-none rounded-xl font-mono text-sm leading-relaxed"
            />
            <p className="text-xs text-muted-foreground">
              Mẹo: giữ email dưới 120 từ, hỏi thăm trước khi đưa giải pháp.
            </p>
          </div>

          <div className="flex items-start gap-3 rounded-xl border border-primary/20 bg-primary/5 p-3">
            <span className="mt-0.5 grid size-8 place-items-center rounded-lg bg-primary/15 text-primary">
              <CalendarDays className="size-4" />
            </span>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium">Liên kết đặt lịch dành cho sinh viên</p>
              <p className="mt-0.5 text-xs text-muted-foreground">
                Tự động đính kèm vào email. Sinh viên mở link để chọn khung
                giờ — bạn không cần tạo lịch thủ công.
              </p>
              <Link
                href="/booking/le-ha"
                target="_blank"
                className="mt-2 inline-flex items-center gap-1.5 font-mono text-xs text-primary hover:underline"
              >
                nexusedu.app/booking/le-ha
                <ExternalLink className="size-3" />
              </Link>
            </div>
          </div>
        </div>

        <DialogFooter className="gap-2 sm:gap-2">
          <Button
            variant="ghost"
            className="rounded-xl"
            onClick={reset}
            type="button"
          >
            <RotateCcw className="size-4" />
            Khôi phục bản nháp AI
          </Button>
          <Button variant="outline" className="rounded-xl" onClick={onClose}>
            Huỷ
          </Button>
          <Button
            className="rounded-xl"
            onClick={() =>
              alert && onSave({ ...alert, subject, body })
            }
          >
            <Send className="size-4" />
            Lưu & sẵn sàng gửi
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
