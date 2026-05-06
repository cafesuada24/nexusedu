"use client";

import * as React from "react";
import { Bell, CheckCheck, Inbox } from "lucide-react";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Separator } from "@/components/ui/separator";
import { cn } from "@/lib/utils";
import { useNotifications } from "@/hooks/use-notifications";

export function NotificationsDropdown() {
  const { notifications, unreadCount, markAsRead, markAllAsRead } =
    useNotifications();

  return (
    <Popover>
      <PopoverTrigger asChild>
        <Button
          variant="ghost"
          size="icon"
          className="relative rounded-xl text-slate-600 transition-all duration-200 hover:bg-slate-100 hover:text-slate-900 dark:text-slate-200 dark:hover:bg-slate-800 dark:hover:text-slate-100"
          aria-label="Thông báo"
        >
          <Bell className="size-5" />
          {unreadCount > 0 && (
            <Badge className="absolute -top-0.5 -right-0.5 h-4 min-w-4 justify-center rounded-full bg-destructive p-0 text-[10px] text-destructive-foreground animate-in zoom-in duration-300">
              {unreadCount}
            </Badge>
          )}
        </Button>
      </PopoverTrigger>
      <PopoverContent
        align="end"
        className="w-80 overflow-hidden rounded-2xl border border-slate-200/80 bg-white/95 p-0 text-slate-900 shadow-2xl animate-in fade-in slide-in-from-top-2 duration-300 dark:border-slate-800 dark:bg-slate-950 dark:text-slate-100"
      >
        <div className="flex items-center justify-between bg-slate-50/85 px-4 py-3 dark:bg-slate-900/85">
          <h3 className="font-bold text-sm">Thông báo</h3>
          {unreadCount > 0 && (
            <Button
              variant="ghost"
              size="sm"
              className="h-8 rounded-lg px-2 text-[11px] font-semibold text-primary hover:bg-primary/10 hover:text-primary dark:text-blue-300 dark:hover:bg-blue-500/15 dark:hover:text-blue-200"
              onClick={markAllAsRead}
            >
              <CheckCheck className="mr-1 size-3" />
              Đánh dấu tất cả là đã đọc
            </Button>
          )}
        </div>
        <Separator />
        <ScrollArea className="h-[380px]">
          {notifications.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-[300px] gap-2 text-muted-foreground p-4 text-center">
              <div className="grid size-12 place-items-center rounded-2xl bg-muted/50">
                <Inbox className="size-6 opacity-40" />
              </div>
              <p className="text-sm font-medium">Không có thông báo nào</p>
              <p className="text-xs opacity-70">
                Chúng tôi sẽ thông báo cho bạn khi có cập nhật mới.
              </p>
            </div>
          ) : (
            <div className="flex flex-col">
              {notifications.map((notification) => (
                <button
                  key={notification.id}
                  className={cn(
                    "group relative flex flex-col gap-1 overflow-hidden border-b border-slate-200/70 p-4 text-left transition-colors last:border-0 hover:bg-slate-100/70 dark:border-slate-800/70 dark:hover:bg-slate-900/75",
                    !notification.isRead &&
                      "bg-blue-50/60 dark:bg-blue-500/10"
                  )}
                  onClick={() => markAsRead(notification.id)}
                >
                  {!notification.isRead && (
                    <div className="absolute left-0 top-0 bottom-0 w-1 bg-primary" />
                  )}
                  <div className="flex items-start justify-between gap-2">
                    <span
                      className={cn(
                        "text-[13px] font-bold leading-tight transition-colors",
                        notification.isRead
                          ? "text-slate-700 dark:text-slate-300"
                          : "text-slate-900 group-hover:text-primary dark:text-slate-100 dark:group-hover:text-blue-300"
                      )}
                    >
                      {notification.title}
                    </span>
                    <span className="shrink-0 text-[10px] text-muted-foreground whitespace-nowrap pt-0.5">
                      {notification.timestamp}
                    </span>
                  </div>
                  <p
                    className={cn(
                      "text-xs leading-relaxed line-clamp-2 transition-opacity",
                      notification.isRead ? "opacity-60" : "opacity-90"
                    )}
                  >
                    {notification.message}
                  </p>
                </button>
              ))}
            </div>
          )}
        </ScrollArea>
        {notifications.length > 0 && (
          <>
            <Separator />
            <div className="p-2">
              <Button
                variant="ghost"
                className="h-9 w-full rounded-lg text-xs font-semibold hover:bg-slate-100 dark:hover:bg-slate-900"
              >
                Xem tất cả thông báo
              </Button>
            </div>
          </>
        )}
      </PopoverContent>
    </Popover>
  );
}
