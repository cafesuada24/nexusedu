import { Wallet, BookOpen, CalendarX } from "lucide-react"
import { Avatar, AvatarFallback } from "@/components/ui/avatar"
import { Badge } from "@/components/ui/badge"

const alerts = [
  {
    name: "Nguyễn Minh An",
    id: "20215032",
    problem: "Học phí quá hạn 14 ngày",
    icon: Wallet,
    tone: "destructive" as const,
    time: "5 phút trước",
  },
  {
    name: "Trần Hoàng Bình",
    id: "20215098",
    problem: "Điểm GK < 4.0 (3 môn)",
    icon: BookOpen,
    tone: "warning" as const,
    time: "38 phút trước",
  },
  {
    name: "Phạm Thu Hà",
    id: "20215172",
    problem: "Vắng 6/10 buổi gần nhất",
    icon: CalendarX,
    tone: "warning" as const,
    time: "1 giờ trước",
  },
  {
    name: "Lê Quốc Huy",
    id: "20215211",
    problem: "Điểm TB giảm 2 kỳ liên tiếp",
    icon: BookOpen,
    tone: "destructive" as const,
    time: "2 giờ trước",
  },
]

const toneMap = {
  destructive: "bg-destructive/10 text-destructive",
  warning: "bg-warning/15 text-warning",
}

export function RecentAlerts() {
  return (
    <ul className="space-y-2">
      {alerts.map((a) => (
        <li
          key={a.id}
          className="flex items-center gap-3 rounded-xl border border-border/60 bg-card p-3 transition-colors hover:bg-accent/50"
        >
          <Avatar className="size-9">
            <AvatarFallback className="bg-primary/10 text-primary text-xs font-semibold">
              {a.name
                .split(" ")
                .map((n) => n[0])
                .slice(-2)
                .join("")}
            </AvatarFallback>
          </Avatar>
          <div className="min-w-0 flex-1">
            <p className="truncate text-sm font-medium">{a.name}</p>
            <p className="truncate text-xs text-muted-foreground">{a.problem}</p>
          </div>
          <Badge
            variant="secondary"
            className={`${toneMap[a.tone]} rounded-md hover:${toneMap[a.tone]}`}
          >
            <a.icon className="size-3" />
          </Badge>
        </li>
      ))}
    </ul>
  )
}
