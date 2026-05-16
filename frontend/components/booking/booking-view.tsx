"use client";

import * as React from "react";
import { addDays, format, isSameDay, startOfToday } from "date-fns";
import { vi } from "date-fns/locale";
import {
    CalendarCheck2,
    CheckCircle2,
    Clock,
    Loader2,
    MapPin,
    Video,
} from "lucide-react";
import { toast } from "sonner";
import {
    Card,
    CardContent,
    CardDescription,
    CardHeader,
    CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Calendar } from "@/components/ui/calendar";
import { Badge } from "@/components/ui/badge";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import { Label } from "@/components/ui/label";
import { Separator } from "@/components/ui/separator";
import { cn } from "@/lib/utils";
import { useScheduleQuery } from "@/hooks/use-schedule-query";
import { generateSlotsForDate, isDateOff } from "@/lib/schedule";
import { confirmBooking, fetchTakenSlots, SlotTakenError } from "@/lib/api";

type Mode = "video" | "inperson";

export function BookingView({ caseId }: { caseId: string }) {
    const today = startOfToday();
    const { schedule } = useScheduleQuery();
    const [date, setDate] = React.useState<Date | undefined>(addDays(today, 1));
    const [slot, setSlot] = React.useState<string | null>(null);
    const [mode, setMode] = React.useState<Mode>("video");
    const [stage, setStage] = React.useState<"pick" | "syncing" | "done">(
        "pick",
    );
    const [takenSlots, setTakenSlots] = React.useState<Set<string>>(new Set());

    const slotsForDate = React.useMemo(
        () => (date ? generateSlotsForDate(date, schedule) : []),
        [date, schedule],
    );

    React.useEffect(() => {
        if (!date) return;
        const dateStr = format(date, "yyyy-MM-dd");
        fetchTakenSlots(caseId, dateStr).then((slots) => {
            const taken = new Set(
                slots.map((s) => {
                    // Convert UTC ISO string → HH:MM in UTC+7
                    const utcDate = new Date(s.start_time);
                    const h = ((utcDate.getUTCHours() + 7) % 24)
                        .toString()
                        .padStart(2, "0");
                    const m = utcDate.getUTCMinutes().toString().padStart(2, "0");
                    return `${h}:${m}`;
                }),
            );
            setTakenSlots(taken);
        });
    }, [date, caseId]);

    const confirm = async () => {
        if (!date || !slot) return;
        setStage("syncing");

        const dateStr = format(date, "yyyy-MM-dd");
        // UI hiển thị "Múi giờ (GMT+7) Hồ Chí Minh" — gắn explicit offset để
        // backend nhận đúng instant bất kể browser của student đang ở đâu.
        const appointmentTime = `${dateStr}T${slot}:00+07:00`;

        console.log(appointmentTime);
        try {
            await confirmBooking(caseId, {
                appointmentTime,
                meetingMethod: mode === "video" ? "online" : "in_person",
            });
        } catch (error) {
            setStage("pick");
            if (error instanceof SlotTakenError) {
                setSlot(null);
                toast.error("Khung giờ vừa được người khác đặt", {
                    description: "Vui lòng chọn khung giờ khác.",
                });
            } else {
                toast.error(
                    "Không thể xác nhận đặt lịch. Vui lòng thử lại sau.",
                );
                // eslint-disable-next-line no-console
                console.error("[booking] confirm failed:", error);
            }
            return;
        }

        setTimeout(() => {
            setStage("done");
            toast.success("Đã đặt lịch thành công", {
                description: `${format(date, "EEEE, d MMMM", { locale: vi })} · ${slot}`,
            });
        }, 800);
    };

    if (stage === "done" && date && slot) {
        return (
            <Card className="rounded-2xl border-success/30 bg-success/5">
                <CardContent className="grid gap-6 p-8 md:grid-cols-[auto_1fr] md:items-center">
                    <span className="grid size-16 place-items-center rounded-2xl bg-success/15 text-success">
                        <CheckCircle2 className="size-8" />
                    </span>
                    <div>
                        <h2 className="font-serif text-2xl font-bold">
                            Đã đặt lịch thành công
                        </h2>
                        <div className="mt-4 flex flex-wrap gap-2">
                            <Badge variant="outline" className="rounded-md">
                                <CalendarCheck2 className="size-3" />
                                {format(date, "EEEE, d MMMM yyyy", {
                                    locale: vi,
                                })}
                            </Badge>
                            <Badge variant="outline" className="rounded-md">
                                <Clock className="size-3" />
                                {slot}
                            </Badge>
                            <Badge variant="outline" className="rounded-md">
                                {mode === "video" ? (
                                    <Video className="size-3" />
                                ) : (
                                    <MapPin className="size-3" />
                                )}
                                {mode === "video"
                                    ? "Google Meet"
                                    : "Phòng B3.402"}
                            </Badge>
                        </div>
                    </div>
                </CardContent>
            </Card>
        );
    }

    return (
        <div className="grid gap-4 lg:grid-cols-[380px_1fr]">
            <Card className="rounded-2xl border-border/60">
                <CardHeader>
                    <div className="flex items-center gap-3">
                        <Avatar className="size-11">
                            <AvatarFallback className="bg-primary/10 text-primary font-semibold">
                                LH
                            </AvatarFallback>
                        </Avatar>
                        <div>
                            <CardTitle className="font-serif text-lg">
                                TS. Lê Hà
                            </CardTitle>
                            <CardDescription>
                                Cố vấn học tập · Khoa CNTT
                            </CardDescription>
                        </div>
                    </div>
                </CardHeader>
                <CardContent className="grid gap-4">
                    <Separator />
                    <div>
                        <p className="text-sm font-medium">Thời lượng</p>
                        <p className="text-sm text-muted-foreground">
                            {schedule.duration} phút · trực tuyến hoặc trực tiếp
                        </p>
                    </div>
                    <div>
                        <p className="mb-2 text-sm font-medium">
                            Hình thức gặp
                        </p>
                        <RadioGroup
                            value={mode}
                            onValueChange={(v) => setMode(v as Mode)}
                            className="grid gap-2"
                        >
                            <Label
                                htmlFor="m-video"
                                className={cn(
                                    "flex cursor-pointer items-center gap-3 rounded-xl border border-border p-3 transition-colors hover:bg-accent/60",
                                    mode === "video" &&
                                        "border-primary bg-primary/5",
                                )}
                            >
                                <RadioGroupItem id="m-video" value="video" />
                                <Video className="size-4 text-primary" />
                                <span className="text-sm font-medium">
                                    Google Meet
                                </span>
                            </Label>
                            <Label
                                htmlFor="m-inperson"
                                className={cn(
                                    "flex cursor-pointer items-center gap-3 rounded-xl border border-border p-3 transition-colors hover:bg-accent/60",
                                    mode === "inperson" &&
                                        "border-primary bg-primary/5",
                                )}
                            >
                                <RadioGroupItem
                                    id="m-inperson"
                                    value="inperson"
                                />
                                <MapPin className="size-4 text-primary" />
                                <span className="text-sm font-medium">
                                    Tại văn phòng · B3.402
                                </span>
                            </Label>
                        </RadioGroup>
                    </div>
                    <div className="rounded-xl bg-muted/50 p-3 text-xs text-muted-foreground">
                        Múi giờ (GMT+7) Hồ Chí Minh
                    </div>
                </CardContent>
            </Card>

            <Card className="rounded-2xl border-border/60">
                <CardHeader>
                    <CardTitle className="font-serif text-lg">
                        Chọn ngày & giờ
                    </CardTitle>
                    <CardDescription>
                        Các khung giờ trống được đồng bộ từ lịch cố vấn.
                    </CardDescription>
                </CardHeader>
                <CardContent className="grid gap-6 md:grid-cols-[auto_1fr]">
                    <Calendar
                        mode="single"
                        selected={date}
                        onSelect={(d) => {
                            setDate(d);
                            setSlot(null);
                            setTakenSlots(new Set());
                        }}
                        disabled={(d) => d < today || isDateOff(d, schedule)}
                        className="rounded-xl border border-border bg-card p-3"
                    />
                    <div>
                        <div className="mb-3 flex items-center justify-between">
                            <p className="text-sm font-medium">
                                {date
                                    ? format(date, "EEEE, d MMMM", {
                                          locale: vi,
                                      })
                                    : "Chọn một ngày"}
                            </p>
                            <Badge
                                variant="outline"
                                className="rounded-md text-xs text-muted-foreground"
                            >
                                {date && isSameDay(date, today)
                                    ? "Hôm nay"
                                    : "Sắp tới"}
                            </Badge>
                        </div>
                        {slotsForDate.length === 0 ? (
                            <div className="rounded-xl border border-dashed border-border/60 bg-muted/30 px-4 py-6 text-center text-sm text-muted-foreground">
                                {date
                                    ? "Không có khung giờ trống trong ngày này."
                                    : "Vui lòng chọn một ngày để xem khung giờ."}
                            </div>
                        ) : (
                            <div className="grid grid-cols-3 gap-2 sm:grid-cols-4">
                                {slotsForDate.map((s) => {
                                    const selected = s === slot;
                                    const taken = takenSlots.has(s);
                                    return (
                                        <button
                                            key={s}
                                            type="button"
                                            onClick={() => !taken && setSlot(s)}
                                            aria-pressed={selected}
                                            disabled={taken}
                                            title={taken ? "Khung giờ đã được đặt" : undefined}
                                            className={cn(
                                                "relative h-10 rounded-xl border text-sm font-medium transition-all",
                                                taken &&
                                                    "cursor-not-allowed border-border/40 bg-muted/40 text-muted-foreground/50",
                                                !taken && !selected &&
                                                    "border-border hover:border-primary/50 hover:bg-primary/5",
                                                !taken && selected &&
                                                    "border-primary bg-primary text-primary-foreground shadow-sm",
                                            )}
                                        >
                                            {taken && (
                                                <span
                                                    aria-hidden
                                                    className="pointer-events-none absolute inset-x-2 top-1/2 h-px -translate-y-1/2 bg-muted-foreground/40"
                                                />
                                            )}
                                            {s}
                                        </button>
                                    );
                                })}
                            </div>
                        )}
                        <p className="mt-3 text-xs text-muted-foreground">
                            Khung giờ đồng bộ từ &ldquo;Giờ làm việc&rdquo; cố
                            vấn đã cấu hình. Khung giờ xám là đã được đặt.
                        </p>

                        <div className="mt-6 flex items-center justify-end gap-2">
                            <Button
                                variant="outline"
                                className="rounded-xl"
                                disabled={!slot}
                                onClick={() => setSlot(null)}
                            >
                                Xoá chọn
                            </Button>
                            <Button
                                className="rounded-xl"
                                disabled={!date || !slot || stage === "syncing"}
                                onClick={confirm}
                            >
                                {stage === "syncing" ? (
                                    <>
                                        <Loader2 className="size-4 animate-spin" />
                                        Đang đồng bộ với lịch...
                                    </>
                                ) : (
                                    <>
                                        <CalendarCheck2 className="size-4" />
                                        Xác nhận đặt lịch
                                    </>
                                )}
                            </Button>
                        </div>
                    </div>
                </CardContent>
            </Card>
        </div>
    );
}
