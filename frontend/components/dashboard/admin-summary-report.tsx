"use client"

import * as React from "react"
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
import { Skeleton } from "@/components/ui/skeleton"
import { cn } from "@/lib/utils"
import { useAdminDashboard } from "@/hooks/use-admin-dashboard"

export function AdminSummaryReport() {
  const { data: dashboardData, isLoading, isError, error } = useAdminDashboard()

  React.useEffect(() => {
    if (dashboardData) {
      console.log("AdminSummaryReport Data:", dashboardData)
    }
  }, [dashboardData])

  if (isLoading) {
    return (
      <div className="grid gap-6 lg:grid-cols-2">
        <Card className="rounded-2xl border-primary/10 bg-white/50 shadow-sm backdrop-blur-sm dark:bg-slate-900/40">
          <CardHeader className="pb-3">
            <Skeleton className="h-6 w-48" />
            <Skeleton className="h-4 w-64" />
          </CardHeader>
          <CardContent className="flex flex-col gap-5">
            {[1, 2, 3, 4].map((i) => (
              <div key={i} className="space-y-2">
                <div className="flex justify-between">
                  <Skeleton className="h-4 w-32" />
                  <Skeleton className="h-4 w-16" />
                </div>
                <Skeleton className="h-2 w-full" />
              </div>
            ))}
          </CardContent>
        </Card>
        <Card className="rounded-2xl border-destructive/10 bg-white/50 shadow-sm backdrop-blur-sm dark:bg-slate-900/40">
          <CardHeader className="pb-3">
            <Skeleton className="h-6 w-48" />
            <Skeleton className="h-4 w-64" />
          </CardHeader>
          <CardContent className="flex flex-col gap-3">
            {[1, 2, 3].map((i) => (
              <Skeleton key={i} className="h-16 w-full rounded-xl" />
            ))}
          </CardContent>
        </Card>
      </div>
    )
  }

  if (isError) {
    return (
      <Card className="border-destructive/20 bg-destructive/5 p-4 text-center">
        <p className="text-xs font-medium text-destructive">Lỗi tải báo cáo: {error instanceof Error ? error.message : "Lỗi không xác định"}</p>
      </Card>
    )
  }

  const majorRiskData = dashboardData?.major_risk || []

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
            {majorRiskData.length > 0 ? (
              majorRiskData.map((dept) => (
                <div key={dept.major} className="flex flex-col gap-2">
                  <div className="flex items-center justify-between text-sm">
                    <span className="font-medium text-foreground">{dept.major || "N/A"}</span>
                    <div className="flex items-center gap-2">
                      <span className="text-xs text-muted-foreground">{dept.total_students || 0} SV tổng</span>
                      <span className="font-bold text-destructive">{((dept.risk_percentage || 0) * 100).toFixed(0)}% rủi ro</span>
                    </div>
                  </div>
                  <Progress value={(dept.risk_percentage || 0) * 100} className="h-2" indicatorClassName="bg-destructive" />
                </div>
              ))
            ) : (
              <div className="flex flex-col items-center justify-center py-8 text-center">
                <p className="text-xs text-muted-foreground">Không có dữ liệu rủi ro theo ngành</p>
              </div>
            )}
          </div>
          <Button variant="ghost" size="sm" className="mt-6 w-full gap-2 rounded-xl text-muted-foreground hover:text-primary">
            Xem chi tiết báo cáo Khoa <ChevronRight className="size-4" />
          </Button>
        </CardContent>
      </Card>

      {/* Critical Cases (Placeholder for now, keeping existing mock structure) */}
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
            {[
              { id: "1", name: "Nguyễn Văn A", major: "CNTT", reason: "Nghỉ học > 50%", priority: "high" },
              { id: "2", name: "Trần Thị B", major: "Kinh tế", reason: "GPA < 1.0", priority: "high" },
              { id: "3", name: "Lê Minh C", major: "Ô tô", reason: "Cảnh báo học vụ lần 2", priority: "medium" },
            ].map((item) => (
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

