"use client";

import { Link2, Copy } from "lucide-react";
import { toast } from "sonner";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";

interface BookingLinkCardProps {
  displayUrl: string;
  bookingUrl: string;
}

export function BookingLinkCard({
  displayUrl,
  bookingUrl,
}: BookingLinkCardProps) {
  return (
    <Card className="stripe-primary rounded-2xl border-primary/15 bg-gradient-to-br from-primary/18 via-primary/8 to-card">
      <CardHeader className="pb-4 text-center">
        <CardTitle className="flex items-center justify-center gap-2 text-base">
          <Link2 className="size-4 text-primary" />
          Liên kết đặt lịch
        </CardTitle>
      </CardHeader>
      <CardContent className="flex flex-col items-center">
        <div className="flex w-full max-w-md items-center gap-2 rounded-xl border border-primary/20 bg-muted/30 px-4 py-2.5 shadow-sm transition-all hover:border-primary/40">
          <code className="flex-1 truncate font-mono text-xs text-foreground/80">
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
                  toast.success("Đã sao chép liên kết", {
                    description: "Thông tin đã được lưu vào bộ nhớ tạm của bạn",
                  });
                }}
                aria-label="Sao chép liên kết"
              >
                <Copy className="size-3.5" />
              </Button>
            </TooltipTrigger>
            <TooltipContent>Sao chép</TooltipContent>
          </Tooltip>
        </div>
      </CardContent>
    </Card>
  );
}
