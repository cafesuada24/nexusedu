"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  FileSpreadsheet,
  BellRing,
  BarChart3,
  LifeBuoy,
  LogOut,
  Settings,
  CalendarClock,
  LineChart,
  type LucideIcon,
} from "lucide-react";
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuBadge,
  SidebarMenuButton,
  SidebarMenuItem,
} from "@/components/ui/sidebar";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Logo } from "@/components/logo";
import { useDataset } from "@/hooks/use-dataset";
import { cn } from "@/lib/utils";

type Tone = "primary" | "sky" | "cyan" | "indigo" | "destructive" | "slate";

const TONE: Record<
  Tone,
  {
    /** Icon tile background (idle) */
    tile: string;
    /** Icon tile background (active) */
    tileActive: string;
    /** Vertical accent rail when active */
    rail: string;
    /** Subtle row tint when active */
    activeBg: string;
    /** Active label/text color */
    activeText: string;
    /** Badge background tint */
    badge: string;
  }
> = {
  primary: {
    tile: "bg-primary/10 text-primary ring-primary/15",
    tileActive:
      "bg-primary text-primary-foreground ring-primary/40 shadow-sm shadow-primary/30",
    rail: "bg-primary",
    activeBg: "bg-primary/8",
    activeText: "text-primary",
    badge: "bg-primary/15 text-primary",
  },
  sky: {
    tile: "bg-accent-sky/10 text-accent-sky ring-accent-sky/15",
    tileActive:
      "bg-accent-sky text-accent-sky-foreground ring-accent-sky/40 shadow-sm shadow-accent-sky/30",
    rail: "bg-accent-sky",
    activeBg: "bg-accent-sky/8",
    activeText: "text-accent-sky",
    badge: "bg-accent-sky/15 text-accent-sky",
  },
  cyan: {
    tile: "bg-accent-cyan/10 text-accent-cyan ring-accent-cyan/15",
    tileActive:
      "bg-accent-cyan text-accent-cyan-foreground ring-accent-cyan/40 shadow-sm shadow-accent-cyan/30",
    rail: "bg-accent-cyan",
    activeBg: "bg-accent-cyan/8",
    activeText: "text-accent-cyan",
    badge: "bg-accent-cyan/15 text-accent-cyan",
  },
  indigo: {
    tile: "bg-accent-indigo/10 text-accent-indigo ring-accent-indigo/15",
    tileActive:
      "bg-accent-indigo text-accent-indigo-foreground ring-accent-indigo/40 shadow-sm shadow-accent-indigo/30",
    rail: "bg-accent-indigo",
    activeBg: "bg-accent-indigo/8",
    activeText: "text-accent-indigo",
    badge: "bg-accent-indigo/15 text-accent-indigo",
  },
  destructive: {
    tile: "bg-destructive/10 text-destructive ring-destructive/15",
    tileActive:
      "bg-destructive text-destructive-foreground ring-destructive/40 shadow-sm shadow-destructive/30",
    rail: "bg-destructive",
    activeBg: "bg-destructive/8",
    activeText: "text-destructive",
    badge: "bg-destructive/15 text-destructive",
  },
  slate: {
    tile: "bg-accent-slate/10 text-accent-slate ring-accent-slate/15",
    tileActive:
      "bg-accent-slate text-accent-slate-foreground ring-accent-slate/40 shadow-sm shadow-accent-slate/30",
    rail: "bg-accent-slate",
    activeBg: "bg-accent-slate/8",
    activeText: "text-accent-slate",
    badge: "bg-accent-slate/15 text-accent-slate",
  },
};

type NavItem = {
  href: string;
  label: string;
  icon: LucideIcon;
  tone: Tone;
  badge?: string;
};

const mainNav: NavItem[] = [
  {
    href: "/dashboard",
    label: "Tổng quan",
    icon: LayoutDashboard,
    tone: "primary",
  },
  {
    href: "/dashboard/import",
    label: "Nhập dữ liệu (CSV)",
    icon: FileSpreadsheet,
    tone: "sky",
  },
  {
    href: "/dashboard/analysis",
    label: "Phân tích sinh viên",
    icon: LineChart,
    tone: "cyan",
  },
  {
    href: "/dashboard/alerts",
    label: "Trung tâm cảnh báo",
    icon: BellRing,
    tone: "destructive",
  },
  {
    href: "/dashboard/schedule",
    label: "Lịch làm việc",
    icon: CalendarClock,
    tone: "indigo",
  },
  {
    href: "/dashboard/metrics",
    label: "Báo cáo BGH",
    icon: BarChart3,
    tone: "primary",
  },
];

const secondaryNav: NavItem[] = [
  {
    href: "/dashboard/settings",
    label: "Cài đặt",
    icon: Settings,
    tone: "slate",
  },
  { href: "/dashboard/support", label: "Hỗ trợ", icon: LifeBuoy, tone: "sky" },
];

function NavRow({ item, active }: { item: NavItem; active: boolean }) {
  const tone = TONE[item.tone];
  const Icon = item.icon;

  return (
    <SidebarMenuItem>
      <SidebarMenuButton
        asChild
        isActive={active}
        tooltip={item.label}
        className={cn(
          "group/nav relative h-10 rounded-lg pl-2.5 pr-2 transition-colors",
          active && tone.activeBg,
          active &&
            "data-[active=true]:bg-transparent data-[active=true]:text-sidebar-foreground hover:bg-transparent",
          !active && "hover:bg-sidebar-accent/60",
        )}
      >
        <Link href={item.href} className="flex w-full items-center gap-2.5">
          {/* Vertical color rail when active */}
          <span
            aria-hidden
            className={cn(
              "absolute left-0 top-1/2 h-6 w-1 -translate-y-1/2 rounded-r-full transition-opacity",
              tone.rail,
              active ? "opacity-100" : "opacity-0",
            )}
          />
          <span
            aria-hidden
            className={cn(
              "grid size-7 shrink-0 place-items-center rounded-md ring-1 transition-colors",
              active ? tone.tileActive : tone.tile,
              "group-hover/nav:ring-2",
            )}
          >
            <Icon className="size-3.5" />
          </span>
          <span
            className={cn(
              "truncate text-sm font-medium transition-colors",
              active
                ? cn(tone.activeText, "font-semibold")
                : "text-sidebar-foreground",
            )}
          >
            {item.label}
          </span>
        </Link>
      </SidebarMenuButton>
      {item.badge && (
        <SidebarMenuBadge
          className={cn("rounded-md font-mono text-[11px]", tone.badge)}
        >
          {item.badge}
        </SidebarMenuBadge>
      )}
    </SidebarMenuItem>
  );
}

export function AppSidebar() {
  const pathname = usePathname();
  const { dataset } = useDataset();

  // Sidebar badge for "Alert Center" reflects the live "Nguy cơ cao"
  // count from the Analysis dataset — the primary signal advisors act on.
  // Falls back to undefined (no badge) when the dataset hasn't loaded yet
  // so we never display a stale hard-coded number.
  const alertBadgeCount = dataset ? dataset.highRisk : undefined;

  const navWithLiveBadges: NavItem[] = mainNav.map((item) =>
    item.href === "/dashboard/alerts" && alertBadgeCount && alertBadgeCount > 0
      ? { ...item, badge: alertBadgeCount.toLocaleString("vi-VN") }
      : item,
  );

  const isActive = (href: string) => {
    if (href === "/dashboard") return pathname === "/dashboard";
    return pathname.startsWith(href);
  };

  return (
    <Sidebar collapsible="icon" className="border-r border-sidebar-border">
      <SidebarHeader className="border-b border-sidebar-border bg-gradient-to-b from-primary/5 to-transparent px-3 py-3">
        <Logo size="sm" />
      </SidebarHeader>

      <SidebarContent className="gap-1 px-1.5 py-2">
        <SidebarGroup>
          <SidebarGroupLabel className="px-2 text-[10px] font-semibold uppercase tracking-wider text-muted-foreground/70">
            Điều hướng
          </SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu className="gap-0.5">
              {navWithLiveBadges.map((item) => (
                <NavRow
                  key={item.href}
                  item={item}
                  active={isActive(item.href)}
                />
              ))}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>

        <SidebarGroup>
          <SidebarGroupLabel className="px-2 text-[10px] font-semibold uppercase tracking-wider text-muted-foreground/70">
            Khác
          </SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu className="gap-0.5">
              {secondaryNav.map((item) => (
                <NavRow
                  key={item.href}
                  item={item}
                  active={isActive(item.href)}
                />
              ))}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
      </SidebarContent>

      <SidebarFooter className="border-t border-sidebar-border p-2">
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <SidebarMenuButton
              size="lg"
              className="rounded-lg data-[state=open]:bg-sidebar-accent"
            >
              <Avatar className="size-8 rounded-lg ring-2 ring-primary/15">
                <AvatarImage src="/avatar-advisor.jpg" alt="" />
                <AvatarFallback className="rounded-lg bg-primary/10 text-primary">
                  LH
                </AvatarFallback>
              </Avatar>
              <div className="grid flex-1 text-left text-sm leading-tight">
                <span className="truncate font-semibold">TS. Lê Hà</span>
                <span className="truncate text-xs text-muted-foreground">
                  Cố vấn · Khoa CNTT
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
            <DropdownMenuItem asChild>
              <Link href="/login">
                <LogOut className="size-4" />
                Đăng xuất
              </Link>
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </SidebarFooter>
    </Sidebar>
  );
}
