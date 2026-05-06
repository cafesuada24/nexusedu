"use client";

import Link from "next/link";
import { Settings, LifeBuoy, LogOut } from "lucide-react";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { useAuth } from "@/hooks/use-auth";
import { Button } from "@/components/ui/button";

export function UserDropdown() {
  const { user, logout } = useAuth();

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button
          variant="ghost"
          size="icon"
          className="size-9 rounded-full ring-1 ring-slate-200/80 hover:bg-slate-100 dark:ring-slate-700/70 dark:hover:bg-slate-800"
        >
          <Avatar className="size-9">
            <AvatarImage src="/avatar-advisor.jpg" alt="" />
            <AvatarFallback className="bg-primary/10 text-primary uppercase dark:bg-slate-800 dark:text-slate-200">
              {user?.email?.slice(0, 2) || "US"}
            </AvatarFallback>
          </Avatar>
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent
        align="end"
        className="w-56 rounded-xl border border-slate-200/80 bg-white/95 text-slate-900 shadow-lg dark:border-slate-800 dark:bg-slate-950 dark:text-slate-100"
      >
        <DropdownMenuLabel>
          <div className="flex flex-col space-y-1">
            <p className="text-sm font-medium leading-none">{user?.email?.split("@")[0] || "Người dùng"}</p>
            <p className="text-xs leading-none uppercase text-muted-foreground">{user?.role || "Khách"}</p>
          </div>
        </DropdownMenuLabel>
        <DropdownMenuSeparator />
        <DropdownMenuItem asChild>
          <Link href="/dashboard/settings">
            <Settings className="size-4 mr-2" />
            Cài đặt
          </Link>
        </DropdownMenuItem>
        <DropdownMenuItem asChild>
          <Link href="/dashboard/support">
            <LifeBuoy className="size-4 mr-2" />
            Hỗ trợ
          </Link>
        </DropdownMenuItem>
        <DropdownMenuSeparator />
        <DropdownMenuItem onClick={() => logout()}>
          <LogOut className="size-4 mr-2" />
          Đăng xuất
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
