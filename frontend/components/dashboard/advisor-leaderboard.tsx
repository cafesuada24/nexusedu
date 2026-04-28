import { Mail, CheckCircle2 } from "lucide-react"
import { Avatar, AvatarFallback } from "@/components/ui/avatar"
import { Badge } from "@/components/ui/badge"
import { Progress } from "@/components/ui/progress"
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip"

// School portal — neutral activity list (no leaderboard / trophy framing).
const advisors = [
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

export function AdvisorLeaderboard() {
  return (
    <TooltipProvider delayDuration={150}>
      <ol className="divide-y divide-border">
        {advisors.map((l) => {
          return (
            <li
              key={l.rank}
              className="flex flex-col gap-3 py-3 first:pt-0 last:pb-0 md:flex-row md:items-center"
            >
              <div className="flex items-center gap-3 md:w-72">
                <span
                  className="grid size-9 place-items-center rounded-xl bg-muted font-mono text-sm font-semibold text-muted-foreground ring-1 ring-border"
                  aria-label={`Số thứ tự ${l.rank}`}
                >
                  {l.rank}
                </span>
                <Avatar className="size-9">
                  <AvatarFallback className="bg-primary/10 text-primary text-xs font-semibold">
                    {l.initials}
                  </AvatarFallback>
                </Avatar>
                <div className="min-w-0">
                  <p className="truncate text-sm font-semibold">{l.name}</p>
                  <p className="truncate text-xs text-muted-foreground">
                    {l.faculty}
                  </p>
                </div>
              </div>

              <div className="flex-1">
                <div className="mb-1.5 flex items-center justify-between">
                  <span
                    className="font-mono text-xs font-semibold text-success"
                    aria-label="Tỷ lệ giải quyết"
                  >
                    {l.rate}%
                  </span>
                </div>
                <Progress value={l.rate} className="h-1.5" />
              </div>

              <div className="flex gap-1.5 md:w-auto md:justify-end">
                <Tooltip>
                  <TooltipTrigger asChild>
                    <Badge
                      variant="outline"
                      className="gap-1 rounded-md font-mono text-[11px]"
                    >
                      <Mail className="size-3" />
                      {l.sent}
                    </Badge>
                  </TooltipTrigger>
                  <TooltipContent>{l.sent} email đã gửi</TooltipContent>
                </Tooltip>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <Badge
                      variant="secondary"
                      className="gap-1 rounded-md bg-success/15 font-mono text-[11px] text-success hover:bg-success/15"
                    >
                      <CheckCircle2 className="size-3" />
                      {l.resolved}
                    </Badge>
                  </TooltipTrigger>
                  <TooltipContent>{l.resolved} đã xử lý</TooltipContent>
                </Tooltip>
              </div>
            </li>
          )
        })}
      </ol>
    </TooltipProvider>
  )
}
