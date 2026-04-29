"use client";

import Link from "next/link";
import { Settings, LifeBuoy, LogOut } from "lucide-react";
import { SidebarFooter, SidebarMenuButton } from "@/components/ui/sidebar";
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

export function SidebarUserFooter() {
  const { user, logout } = useAuth();

  return (
    <SidebarFooter className="border-t border-sidebar-border p-2">
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <SidebarMenuButton
            size="lg"
            className="rounded-lg data-[state=open]:bg-sidebar-accent"
          >
            <Avatar className="size-8 rounded-lg ring-2 ring-primary/15">
              <AvatarImage src="/avatar-advisor.jpg" alt="" />
              <AvatarFallback className="rounded-lg bg-primary/10 text-primary uppercase">
                {user?.email?.slice(0, 2) || "US"}
              </AvatarFallback>
            </Avatar>
            <div className="grid flex-1 text-left text-sm leading-tight">
              <span className="truncate font-semibold">
                {user?.email?.split("@")[0] || "Người dùng"}
              </span>
              <span className="truncate text-xs text-muted-foreground uppercase">
                {user?.role || "Khách"}
              </span>
            </div>
          </SidebarMenuButton>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end" side="right" className="w-56">
          <DropdownMenuLabel>Tài khoản</DropdownMenuLabel>
          <DropdownMenuSeparator />
          <DropdownMenuItem asChild>
            <Link href="/dashboard/settings">
              <Settings className="size-4" />
              Cài đặt
            </Link>
          </DropdownMenuItem>
          <DropdownMenuItem asChild>
            <Link href="/dashboard/support">
              <LifeBuoy className="size-4" />
              Hỗ trợ
            </Link>
          </DropdownMenuItem>
          <DropdownMenuSeparator />
          <DropdownMenuItem onClick={() => logout()}>
            <LogOut className="size-4" />
            Đăng xuất
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>
    </SidebarFooter>
  );
}
