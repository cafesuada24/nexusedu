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
    <SidebarFooter className="border-t border-sidebar-border p-2 transition-all duration-300 group-data-[collapsible=icon]:items-center group-data-[collapsible=icon]:px-0">
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <SidebarMenuButton
            size="lg"
            tooltip={user?.email?.split("@")[0] || "Người dùng"}
            className="rounded-xl transition-all duration-300 data-[state=open]:bg-sidebar-accent group-data-[collapsible=icon]:justify-center group-data-[collapsible=icon]:px-0"
          >
            <Avatar className="size-9 shrink-0 rounded-xl ring-2 ring-primary/15 transition-all duration-300">
              <AvatarImage src="/avatar-advisor.jpg" alt="" />
              <AvatarFallback className="rounded-xl bg-primary/10 text-primary uppercase">
                {user?.email?.slice(0, 2) || "US"}
              </AvatarFallback>
            </Avatar>
            <div className="grid flex-1 text-left text-sm leading-tight group-data-[collapsible=icon]:hidden">
              <span className="truncate font-bold">
                {user?.email?.split("@")[0] || "Người dùng"}
              </span>
              <span className="truncate text-[10px] font-medium text-muted-foreground uppercase tracking-wider">
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
