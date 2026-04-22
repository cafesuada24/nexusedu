import { Trophy, Medal, Award } from "lucide-react"
import { Avatar, AvatarFallback } from "@/components/ui/avatar"
import { Badge } from "@/components/ui/badge"
import { Progress } from "@/components/ui/progress"

const leaders = [
  {
    rank: 1,
    name: "TS. Lê Hà",
    faculty: "CNTT",
    initials: "LH",
    sent: 148,
    resolved: 128,
    rate: 92,
  },
  {
    rank: 2,
    name: "ThS. Nguyễn Minh",
    faculty: "Kinh tế",
    initials: "NM",
    sent: 112,
    resolved: 98,
    rate: 88,
  },
  {
    rank: 3,
    name: "TS. Phạm Quang",
    faculty: "Cơ khí",
    initials: "PQ",
    sent: 88,
    resolved: 72,
    rate: 82,
  },
  {
    rank: 4,
    name: "ThS. Trần Hạnh",
    faculty: "Ngoại ngữ",
    initials: "TH",
    sent: 74,
    resolved: 60,
    rate: 81,
  },
  {
    rank: 5,
    name: "TS. Võ Nam",
    faculty: "Xây dựng",
    initials: "VN",
    sent: 62,
    resolved: 48,
    rate: 77,
  },
]

const rankIcon = [Trophy, Medal, Award]
const rankTone = [
  "bg-warning/20 text-warning ring-warning/30",
  "bg-muted text-muted-foreground ring-border",
  "bg-primary/10 text-primary ring-primary/20",
]

export function AdvisorLeaderboard() {
  return (
    <ol className="divide-y divide-border">
      {leaders.map((l, i) => {
        const Icon = i < 3 ? rankIcon[i] : null
        const tone = i < 3 ? rankTone[i] : "bg-muted text-muted-foreground"
        return (
          <li
            key={l.rank}
            className="flex flex-col gap-3 py-4 first:pt-0 last:pb-0 md:flex-row md:items-center"
          >
            <div className="flex items-center gap-3 md:w-72">
              <span
                className={`grid size-9 place-items-center rounded-xl font-serif text-sm font-bold ring-1 ${tone}`}
              >
                {Icon ? <Icon className="size-4" /> : l.rank}
              </span>
              <Avatar className="size-10">
                <AvatarFallback className="bg-primary/10 text-primary font-semibold">
                  {l.initials}
                </AvatarFallback>
              </Avatar>
              <div className="min-w-0">
                <p className="truncate font-semibold">{l.name}</p>
                <p className="text-xs text-muted-foreground">
                  Khoa {l.faculty}
                </p>
              </div>
            </div>

            <div className="flex-1">
              <div className="mb-1.5 flex items-center justify-between text-xs">
                <span className="text-muted-foreground">
                  Tỷ lệ giải quyết
                </span>
                <span className="font-semibold">{l.rate}%</span>
              </div>
              <Progress value={l.rate} className="h-2" />
            </div>

            <div className="flex gap-2 md:w-52 md:justify-end">
              <Badge
                variant="outline"
                className="rounded-md"
                aria-label={`${l.sent} email đã gửi`}
              >
                {l.sent} gửi
              </Badge>
              <Badge
                variant="secondary"
                className="rounded-md bg-success/15 text-success hover:bg-success/15"
              >
                {l.resolved} xử lý
              </Badge>
            </div>
          </li>
        )
      })}
    </ol>
  )
}
