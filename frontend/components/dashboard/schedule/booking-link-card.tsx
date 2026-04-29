"use client";

import { Link2, Globe, Copy, Check, Users, CalendarClock, type LucideIcon } from "lucide-react";
import { toast } from "sonner";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { cn } from "@/lib/utils";

interface BookingLinkCardProps {
  displayUrl: string;
  bookingUrl: string;
  timezone: string;
  autoConfirm: boolean;
  allowOnline: boolean;
  windowDays: number;
}

export function BookingLinkCard({
  displayUrl,
  bookingUrl,
  timezone,
  autoConfirm,
  allowOnline,
  windowDays,
}: BookingLinkCardProps) {
  return (
    <Card className="stripe-primary rounded-2xl border-primary/15 bg-gradient-to-br from-primary/18 via-primary/8 to-card">
      <CardHeader className="pb-3">
        <CardTitle className="flex items-center gap-2 text-base">
          <Link2 className="size-4 text-primary" />
          Liên kết đặt lịch
        </CardTitle>
      </CardHeader>
      <CardContent className="grid gap-3">
        <div className="flex items-center gap-2 rounded-lg border border-border/60 bg-muted/30 px-3 py-2">
          <Globe className="size-4 shrink-0 text-muted-foreground" />
          <code className="flex-1 truncate font-mono text-xs">
            {displayUrl}
          </code>
          <Tooltip>
            <TooltipTrigger asChild>
              <Button
                variant="ghost"
                size="icon"
                className="size-7 rounded-md"
                onClick={() => {
                  navigator.clipboard?.writeText(bookingUrl);
                  toast.success("Đã sao chép");
                }}
                aria-label="Sao chép liên kết"
              >
                <Copy className="size-3.5" />
              </Button>
            </TooltipTrigger>
            <TooltipContent>Sao chép</TooltipContent>
          </Tooltip>
        </div>

        <Separator />

        <ul className="grid grid-cols-2 gap-2 text-xs">
          <BookingStat
            icon={Globe}
            label="Múi giờ"
            value={timezone.replace("Asia/", "")}
          />
          <BookingStat
            icon={Check}
            label="Tự xác nhận"
            value={autoConfirm ? "Bật" : "Tắt"}
            active={autoConfirm}
          />
          <BookingStat
            icon={Users}
            label="Online"
            value={allowOnline ? "Có" : "Không"}
            active={allowOnline}
          />
          <BookingStat
            icon={CalendarClock}
            label="Cửa sổ"
            value={`${windowDays}d`}
          />
        </ul>
      </CardContent>
    </Card>
  );
}

function BookingStat({
  icon: Icon,
  label,
  value,
  active,
}: {
  icon: LucideIcon;
  label: string;
  value: string;
  active?: boolean;
}) {
  return (
    <li className="flex items-center gap-2 rounded-lg border border-border/60 bg-muted/30 px-2.5 py-1.5">
      <Icon
        className={cn(
          "size-3.5 shrink-0",
          active === undefined
            ? "text-muted-foreground"
            : active
              ? "text-success"
              : "text-muted-foreground/60"
        )}
      />
      <span className="truncate text-muted-foreground">{label}</span>
      <span className="ml-auto truncate font-mono text-[11px] font-medium">
        {value}
      </span>
    </li>
  );
}
