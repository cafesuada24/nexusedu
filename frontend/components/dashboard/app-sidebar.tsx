"use client";

import { usePathname } from "next/navigation";
import {
    LayoutDashboard,
    FileSpreadsheet,
    BellRing,
    BarChart3,
    LifeBuoy,
    Settings,
    CalendarClock,
    LineChart,
    Sparkles,
    Users,
} from "lucide-react";
import {
    Sidebar,
    SidebarContent,
    SidebarGroup,
    SidebarGroupContent,
    SidebarGroupLabel,
    SidebarHeader,
    SidebarMenu,
} from "@/components/ui/sidebar";
import { Logo } from "@/components/logo";
import { useAuth } from "@/hooks/use-auth";
import { NavRow, type NavItem } from "./sidebar/nav-item";

const baseMainNav: NavItem[] = [
    {
        href: "/dashboard",
        label: "Tổng quan",
        icon: LayoutDashboard,
        tone: "primary",
    },
    {
        href: "/dashboard/stories",
        label: "Câu chuyện thành công",
        icon: Sparkles,
        tone: "success",
    },
    {
        href: "/dashboard/import",
        label: "Nhập dữ liệu (CSV)",
        icon: FileSpreadsheet,
        tone: "sky",
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
    {
        href: "/dashboard/advisors",
        label: "Cố vấn",
        icon: Users,
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
    {
        href: "/dashboard/support",
        label: "Hỗ trợ",
        icon: LifeBuoy,
        tone: "sky",
    },
];

export function AppSidebar() {
    const pathname = usePathname();
    const { user } = useAuth();
    const isAdmin = user?.role === "admin";
    const mainNav = baseMainNav.filter((item) => {
        if (item.href === "/dashboard/import") return isAdmin;
        if (item.href === "/dashboard/advisors") return isAdmin;
        return true;
    });

    const isActive = (href: string) => {
        if (href === "/dashboard") return pathname === "/dashboard";
        return pathname.startsWith(href);
    };

    return (
        <Sidebar
            collapsible="icon"
            className="border-r border-sidebar-border transition-all duration-300"
        >
            <SidebarHeader className="border-b border-sidebar-border bg-gradient-to-b from-primary/5 to-transparent px-3 py-4 transition-all duration-300 group-data-[collapsible=icon]:items-center group-data-[collapsible=icon]:px-0">
                <Logo size="sm" />
            </SidebarHeader>

            <SidebarContent className="gap-1 px-1.5 py-2">
                <SidebarGroup>
                    <SidebarGroupLabel className="px-2 text-[10px] font-semibold uppercase tracking-wider text-muted-foreground/70">
                        Điều hướng
                    </SidebarGroupLabel>
                    <SidebarGroupContent>
                        <SidebarMenu className="gap-0.5">
                            {mainNav.map((item) => (
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
        </Sidebar>
    );
}
