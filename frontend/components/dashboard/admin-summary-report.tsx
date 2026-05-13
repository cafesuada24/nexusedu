"use client"

import { 
  BarChart3, 
  AlertTriangle, 
  ChevronRight,
  School,
  Building2,
  Users
} from "lucide-react"
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
} from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Progress } from "@/components/ui/progress"
import { cn } from "@/lib/utils"

const DEPARTMENT_DATA = [
  { name: "Công nghệ thông tin", status: 85, total: 450, atRisk: 12 },
  { name: "Kinh tế & Quản trị", status: 72, total: 600, atRisk: 45 },
  { name: "Ngôn ngữ Anh", status: 90, total: 300, atRisk: 8 },
  { name: "Kỹ thuật Ô tô", status: 65, total: 250, atRisk: 30 },
]

const CRITICAL_CASES = [
  { id: "1", name: "Nguyễn Văn A", major: "CNTT", reason: "Nghỉ học > 50%", priority: "high" },
  { id: "2", name: "Trần Thị B", major: "Kinh tế", reason: "GPA < 1.0", priority: "high" },
  { id: "3", name: "Lê Minh C", major: "Ô tô", reason: "Cảnh báo học vụ lần 2", priority: "medium" },
]

export function AdminSummaryReport() {
  return (
    <div className="grid gap-6 lg:grid-cols-2">
      {/* Status by Department */}
      <Card className="rounded-2xl border-primary/10 bg-white/50 shadow-sm backdrop-blur-sm dark:bg-slate-900/40">
        <CardHeader className="pb-3">
          <CardTitle className="flex items-center gap-2 font-serif text-lg">
            <School className="size-5 text-primary" />
            Tình trạng theo Khoa / Ngành
          </CardTitle>
          <CardDescription>
            Tỷ lệ sinh viên ổn định sau can thiệp theo đơn vị
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex flex-col gap-5">
            {DEPARTMENT_DATA.map((dept) => (
              <div key={dept.name} className="flex flex-col gap-2">
                <div className="flex items-center justify-between text-sm">
                  <span className="font-medium text-foreground">{dept.name}</span>
                  <div className="flex items-center gap-2">
                    <span className="text-xs text-muted-foreground">{dept.atRisk} SV rủi ro</span>
                    <span className="font-bold text-primary">{dept.status}%</span>
                  </div>
                </div>
                <Progress value={dept.status} className="h-2" />
              </div>
            ))}
          </div>
          <Button variant="ghost" size="sm" className="mt-6 w-full gap-2 rounded-xl text-muted-foreground hover:text-primary">
            Xem chi tiết báo cáo Khoa <ChevronRight className="size-4" />
          </Button>
        </CardContent>
      </Card>

      {/* Critical Cases */}
      <Card className="rounded-2xl border-destructive/10 bg-white/50 shadow-sm backdrop-blur-sm dark:bg-slate-900/40">
        <CardHeader className="pb-3">
          <CardTitle className="flex items-center gap-2 font-serif text-lg">
            <AlertTriangle className="size-5 text-destructive" />
            Case trọng điểm cần lãnh đạo can thiệp
          </CardTitle>
          <CardDescription>
            Danh sách sinh viên rủi ro cao vượt ngưỡng xử lý của cố vấn
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex flex-col gap-3">
            {CRITICAL_CASES.map((item) => (
              <div 
                key={item.id} 
                className="flex items-center justify-between rounded-xl border border-border/50 bg-card/50 p-3 transition-colors hover:bg-card"
              >
                <div className="flex items-center gap-3">
                  <div className={cn(
                    "grid size-9 place-items-center rounded-lg",
                    item.priority === "high" ? "bg-destructive/10 text-destructive" : "bg-warning/10 text-warning"
                  )}>
                    <Users className="size-4" />
                  </div>
                  <div>
                    <p className="text-sm font-bold">{item.name}</p>
                    <p className="text-[11px] text-muted-foreground">{item.major} • {item.reason}</p>
                  </div>
                </div>
                <Badge 
                  variant={item.priority === "high" ? "destructive" : "secondary"}
                  className="rounded-md px-2 py-0 text-[10px] uppercase tracking-wider"
                >
                  {item.priority === "high" ? "Khẩn cấp" : "Trung bình"}
                </Badge>
              </div>
            ))}
          </div>
          <Button variant="outline" size="sm" className="mt-6 w-full gap-2 rounded-xl border-destructive/20 text-destructive hover:bg-destructive/5 hover:text-destructive">
            Mở danh sách xử lý trọng điểm <ChevronRight className="size-4" />
          </Button>
        </CardContent>
      </Card>
    </div>
  )
}
