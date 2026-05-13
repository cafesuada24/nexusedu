"use client"

import { Quote, Mail, Heart } from "lucide-react"
import { Avatar, AvatarFallback } from "@/components/ui/avatar"
import { Badge } from "@/components/ui/badge"
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { TooltipProvider } from "@/components/ui/tooltip"

export type ThankYouNote = {
  id: string
  message: string
  studentName: string
  daysAgo: number
}

export const THANK_YOU_NOTES: ThankYouNote[] = [
  {
    id: "tn-1",
    message:
      "Cảm ơn cô đã không bỏ rơi em. Kỳ này em đã đậu hết các môn rồi ạ.",
    studentName: "Phạm Hoàng Yến",
    daysAgo: 2,
  },
  {
    id: "tn-2",
    message:
      "Email cô gửi đúng lúc em đang nản nhất. Mọi thứ tốt dần lên.",
    studentName: "Đặng Quốc Bảo",
    daysAgo: 5,
  },
  {
    id: "tn-3",
    message:
      "Cô là người đầu tiên hỏi em ổn không, thay vì hỏi vì sao điểm thấp.",
    studentName: "Vũ Linh Chi",
    daysAgo: 9,
  },
]

export function ThankYouNoteCard({ note: n }: { note: ThankYouNote }) {
  const initials = n.studentName
    .split(" ")
    .map((p) => p[0])
    .filter(Boolean)
    .slice(-2)
    .join("")
    .toUpperCase()

  return (
    <figure className="flex flex-col gap-2 rounded-2xl border border-border/60 bg-white p-4 ring-1 ring-primary/5 transition-shadow hover:shadow-md dark:bg-slate-900/40">
      <Quote className="size-4 shrink-0 text-primary/60" aria-hidden />
      <blockquote className="text-pretty text-sm leading-relaxed text-foreground">
        {n.message}
      </blockquote>
      <figcaption className="mt-auto flex items-center gap-2 border-t border-border/60 pt-2">
        <Avatar className="size-7">
          <AvatarFallback className="bg-primary/10 text-[11px] font-medium text-primary">
            {initials}
          </AvatarFallback>
        </Avatar>
        <span className="flex-1 truncate text-xs font-medium">
          {n.studentName}
        </span>
        <span className="shrink-0 text-[11px] font-mono text-muted-foreground">
          {n.daysAgo}d
        </span>
      </figcaption>
    </figure>
  )
}

export function ThankYouNotes() {
  return (
    <TooltipProvider delayDuration={150}>
      <Card className="stripe-primary rounded-2xl border-primary/15 bg-gradient-to-br from-primary/18 via-primary/8 to-white dark:to-slate-900/40">
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-3">
          <CardTitle className="flex items-center gap-2 font-serif text-lg">
            <span
              aria-hidden
              className="grid size-7 place-items-center rounded-lg bg-primary/10 text-primary ring-1 ring-primary/15"
            >
              <Heart className="size-3.5" />
            </span>
            Lời nhắn từ sinh viên
          </CardTitle>
          <Badge
            variant="secondary"
            className="gap-1 rounded-md bg-primary/10 text-primary hover:bg-primary/10"
          >
            <Mail className="size-3" />
            {THANK_YOU_NOTES.length}
          </Badge>
        </CardHeader>
        <CardContent>
          <ul role="list" className="grid gap-3 md:grid-cols-2 lg:grid-cols-3">
            {THANK_YOU_NOTES.map((n) => (
              <li key={n.id} className="contents">
                <ThankYouNoteCard note={n} />
              </li>
            ))}
          </ul>
        </CardContent>
      </Card>
    </TooltipProvider>
  )
}
