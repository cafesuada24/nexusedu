"use client";

import * as React from "react";
import {
  CalendarIcon,
  Check,
  Plus,
  Sparkles,
  Target,
  Trash2,
  X,
} from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Calendar } from "@/components/ui/calendar";
import { Checkbox } from "@/components/ui/checkbox";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Empty } from "@/components/ui/empty";
import type { Problem } from "@/lib/csv";
import { cn } from "@/lib/utils";

export type Goal = {
  id: string;
  title: string;
  /** YYYY-MM-DD hoặc null nếu không đặt hạn. */
  deadline: string | null;
  done: boolean;
  /** Unix seconds. */
  createdAt: number;
};

type GoalsDialogProps = {
  /** Khi `null` → dialog đóng. */
  alert: {
    id: string;
    name: string;
    problem: Problem;
    problemLabel: string;
    problemTone: string;
    problemIcon: React.ElementType;
    goals: Goal[];
  } | null;
  onClose: () => void;
  onAdd: (alertId: string, title: string, deadline: string | null) => void;
  onToggle: (alertId: string, goalId: string) => void;
  onRemove: (alertId: string, goalId: string) => void;
};

/** Mẫu mục tiêu gợi ý theo loại vấn đề học vụ. */
const TEMPLATES: Record<Problem, string[]> = {
  failed_final: [
    "Đăng ký thi lại trong 2 tuần tới",
    "Hoàn thành toàn bộ đề cương ôn thi lại",
    "Học nhóm phụ đạo 2 buổi/tuần",
    "Gặp giảng viên môn trượt xin lộ trình ôn",
  ],
  failed_midterm: [
    "Đạt ≥ 6.5 cho bài cuối kỳ môn này",
    "Nộp đầy đủ bài tập tuần đến hết học kỳ",
    "Tham gia phụ đạo 1 buổi/tuần",
    "Ôn lại toàn bộ chương trình giữa kỳ trong 10 ngày",
  ],
  low_average: [
    "Nâng GPA học kỳ này lên ≥ 6.0",
    "Duy trì điểm danh ≥ 90% mọi môn",
    "Lập kế hoạch học tập tuần và bám sát",
    "Gặp cố vấn 2 tuần/lần để theo dõi tiến độ",
  ],
};

const DAY_FMT = new Intl.DateTimeFormat("vi-VN", {
  day: "2-digit",
  month: "2-digit",
});

function toIsoDate(d: Date): string {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
}

function fromIsoDate(s: string): Date {
  const [y, m, d] = s.split("-").map(Number);
  return new Date(y, (m ?? 1) - 1, d ?? 1);
}

function startOfToday(): Date {
  const d = new Date();
  d.setHours(0, 0, 0, 0);
  return d;
}

/** Trả về mức ưu tiên hiển thị deadline: 'overdue' | 'soon' | 'normal'. */
function deadlineStatus(
  deadline: string | null,
  done: boolean,
): "overdue" | "soon" | "normal" {
  if (!deadline || done) return "normal";
  const today = startOfToday().getTime();
  const target = fromIsoDate(deadline).getTime();
  const diffDays = Math.round((target - today) / 86_400_000);
  if (diffDays < 0) return "overdue";
  if (diffDays <= 2) return "soon";
  return "normal";
}

function compareGoals(a: Goal, b: Goal) {
  // 1. Chưa hoàn thành lên trước
  if (a.done !== b.done) return a.done ? 1 : -1;
  // 2. Trong cùng nhóm: có deadline lên trước, gần hạn hơn lên trước
  const ad = a.deadline ? fromIsoDate(a.deadline).getTime() : Infinity;
  const bd = b.deadline ? fromIsoDate(b.deadline).getTime() : Infinity;
  if (ad !== bd) return ad - bd;
  // 3. Cùng deadline → mới tạo lên trước
  return b.createdAt - a.createdAt;
}

export function GoalsDialog({
  alert,
  onClose,
  onAdd,
  onToggle,
  onRemove,
}: GoalsDialogProps) {
  const [draftTitle, setDraftTitle] = React.useState("");
  const [draftDate, setDraftDate] = React.useState<Date | undefined>();
  const [pickerOpen, setPickerOpen] = React.useState(false);

  // Reset draft khi đổi sinh viên hoặc khi đóng.
  React.useEffect(() => {
    if (!alert) {
      setDraftTitle("");
      setDraftDate(undefined);
    }
  }, [alert]);

  if (!alert) {
    return (
      <Dialog open={false} onOpenChange={(o) => !o && onClose()}>
        <DialogContent />
      </Dialog>
    );
  }

  const {
    id,
    name,
    problemLabel,
    problemTone,
    problemIcon: ProblemIcon,
  } = alert;
  const goals = [...alert.goals].sort(compareGoals);
  const total = goals.length;
  const done = goals.filter((g) => g.done).length;
  const pct = total === 0 ? 0 : Math.round((done / total) * 100);
  const templates = TEMPLATES[alert.problem];

  function handleAdd() {
    const title = draftTitle.trim();
    if (!title) return;
    onAdd(id, title, draftDate ? toIsoDate(draftDate) : null);
    setDraftTitle("");
    setDraftDate(undefined);
  }

  return (
    <Dialog
      open
      onOpenChange={(o) => {
        if (!o) onClose();
      }}
    >
      <DialogContent className="max-w-xl gap-4 rounded-2xl">
        <DialogHeader className="gap-2">
          <div className="flex items-center gap-2 text-primary">
            <span
              className="grid size-9 place-items-center rounded-xl bg-primary/10 ring-1 ring-primary/20"
              aria-hidden
            >
              <Target className="size-4" />
            </span>
            <DialogTitle className="font-serif text-lg">
              Mục tiêu cho {name}
            </DialogTitle>
          </div>
          <DialogDescription className="text-sm">
            Đặt mục tiêu cụ thể, có thời hạn để theo dõi tiến độ can thiệp và
            báo cáo BGH.
          </DialogDescription>
          <Badge
            variant="outline"
            className={cn(
              "w-fit gap-1 rounded-md border-transparent ring-1",
              problemTone,
            )}
          >
            <ProblemIcon className="size-3" />
            {problemLabel}
          </Badge>
        </DialogHeader>

        {/* Tiến độ */}
        <div className="rounded-xl border border-border/60 bg-muted/30 p-3">
          <div className="flex items-center justify-between text-xs">
            <span className="font-medium">
              {total === 0 ? (
                "Chưa đặt mục tiêu nào"
              ) : (
                <>
                  Đã hoàn thành{" "}
                  <span className="font-mono text-foreground">
                    {done}/{total}
                  </span>
                </>
              )}
            </span>
            <span className="font-mono text-muted-foreground">{pct}%</span>
          </div>
          <div
            className="mt-2 h-1.5 overflow-hidden rounded-full bg-border/60"
            role="progressbar"
            aria-valuenow={pct}
            aria-valuemin={0}
            aria-valuemax={100}
          >
            <div
              className="h-full rounded-full bg-success transition-[width] duration-300"
              style={{ width: `${pct}%` }}
            />
          </div>
        </div>

        {/* Danh sách mục tiêu */}
        <div className="space-y-2">
          <p className="text-xs font-semibold text-muted-foreground">
            Mục tiêu hiện tại
          </p>
          {goals.length === 0 ? (
            <Empty className="rounded-xl border border-dashed border-border/60 bg-muted/20 py-6">
              <Target className="size-6 text-muted-foreground" />
              <p className="text-sm font-medium">Chưa có mục tiêu</p>
              <p className="text-xs text-muted-foreground">
                Chọn một mẫu gợi ý hoặc tự thêm mục tiêu mới ở bên dưới.
              </p>
            </Empty>
          ) : (
            <ScrollArea className="max-h-64 rounded-xl border border-border/60">
              <ul className="divide-y divide-border/60">
                {goals.map((g) => {
                  const ds = deadlineStatus(g.deadline, g.done);
                  return (
                    <li
                      key={g.id}
                      className={cn(
                        "flex items-start gap-3 px-3 py-2.5 transition-colors",
                        g.done && "bg-muted/30",
                      )}
                    >
                      <Checkbox
                        checked={g.done}
                        onCheckedChange={() => onToggle(id, g.id)}
                        className="mt-0.5"
                        aria-label={
                          g.done
                            ? "Bỏ đánh dấu hoàn thành"
                            : "Đánh dấu hoàn thành"
                        }
                      />
                      <div className="min-w-0 flex-1">
                        <p
                          className={cn(
                            "text-sm leading-snug",
                            g.done &&
                              "text-muted-foreground line-through decoration-muted-foreground/60",
                          )}
                        >
                          {g.title}
                        </p>
                        {g.deadline ? (
                          <span
                            className={cn(
                              "mt-1 inline-flex items-center gap-1 rounded-md px-1.5 py-0.5 text-[10.5px] font-medium",
                              ds === "overdue" &&
                                "bg-destructive/10 text-destructive ring-1 ring-destructive/20",
                              ds === "soon" &&
                                "bg-warning/15 text-warning ring-1 ring-warning/25",
                              ds === "normal" &&
                                "bg-muted text-muted-foreground",
                            )}
                          >
                            <CalendarIcon className="size-3" />
                            {ds === "overdue" && !g.done
                              ? "Quá hạn"
                              : "Hạn"}{" "}
                            {DAY_FMT.format(fromIsoDate(g.deadline))}
                          </span>
                        ) : null}
                      </div>
                      <Button
                        variant="ghost"
                        size="icon"
                        className="size-7 shrink-0 rounded-md text-muted-foreground hover:text-destructive"
                        onClick={() => onRemove(id, g.id)}
                        aria-label="Xoá mục tiêu"
                      >
                        <Trash2 className="size-3.5" />
                      </Button>
                    </li>
                  );
                })}
              </ul>
            </ScrollArea>
          )}
        </div>

        {/* Templates */}
        <div className="space-y-2">
          <p className="flex items-center gap-1 text-xs font-semibold text-muted-foreground">
            <Sparkles className="size-3 text-primary" />
            Gợi ý cho “{problemLabel}”
          </p>
          <div className="flex flex-wrap gap-1.5">
            {templates.map((t) => (
              <button
                key={t}
                type="button"
                onClick={() => setDraftTitle(t)}
                className="rounded-md border border-border/60 bg-card px-2 py-1 text-[11.5px] font-medium text-foreground/80 transition-colors hover:border-primary/40 hover:bg-primary/5 hover:text-primary"
              >
                + {t}
              </button>
            ))}
          </div>
        </div>

        {/* Add new */}
        <div className="space-y-2 border-t border-border/60 pt-3">
          <p className="text-xs font-semibold text-muted-foreground">
            Thêm mục tiêu mới
          </p>
          <Input
            value={draftTitle}
            onChange={(e) => setDraftTitle(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") {
                e.preventDefault();
                handleAdd();
              }
            }}
            placeholder="Ví dụ: Hoàn thành đề cương ôn tập trước 30/12"
            className="rounded-lg"
          />
          <div className="flex flex-wrap items-center gap-2">
            <Popover open={pickerOpen} onOpenChange={setPickerOpen}>
              <PopoverTrigger asChild>
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  className="h-9 gap-1.5 rounded-lg"
                >
                  <CalendarIcon className="size-3.5" />
                  {draftDate ? `Hạn ${DAY_FMT.format(draftDate)}` : "Chọn hạn"}
                  {draftDate ? (
                    <span
                      role="button"
                      tabIndex={0}
                      onClick={(e) => {
                        e.stopPropagation();
                        setDraftDate(undefined);
                      }}
                      onKeyDown={(e) => {
                        if (e.key === "Enter" || e.key === " ") {
                          e.preventDefault();
                          e.stopPropagation();
                          setDraftDate(undefined);
                        }
                      }}
                      aria-label="Xoá hạn"
                      className="ml-0.5 grid size-4 place-items-center rounded-full hover:bg-muted"
                    >
                      <X className="size-3" />
                    </span>
                  ) : null}
                </Button>
              </PopoverTrigger>
              <PopoverContent className="w-auto p-0" align="start">
                <Calendar
                  mode="single"
                  selected={draftDate}
                  onSelect={(d) => {
                    setDraftDate(d ?? undefined);
                    setPickerOpen(false);
                  }}
                  disabled={(d) => d < startOfToday()}
                  initialFocus
                />
              </PopoverContent>
            </Popover>
            <Button
              type="button"
              size="sm"
              onClick={handleAdd}
              disabled={!draftTitle.trim()}
              className="ml-auto h-9 gap-1.5 rounded-lg"
            >
              <Plus className="size-3.5" />
              Thêm mục tiêu
            </Button>
          </div>
        </div>

        <div className="flex justify-end pt-1">
          <Button variant="ghost" size="sm" onClick={onClose} className="gap-1">
            <Check className="size-4" />
            Xong
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
