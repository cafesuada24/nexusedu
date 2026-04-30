"use client";

import Link from "next/link";
import { type LucideIcon } from "lucide-react";
import { cn } from "@/lib/utils";
import {
  SidebarMenuItem,
  SidebarMenuButton,
  SidebarMenuBadge,
} from "@/components/ui/sidebar";

export type Tone = "primary" | "sky" | "cyan" | "indigo" | "destructive" | "slate";

export const TONE_CONFIG: Record<
  Tone,
  {
    tile: string;
    tileActive: string;
    rail: string;
    activeBg: string;
    activeText: string;
    badge: string;
  }
> = {
  primary: {
    tile: "bg-primary/10 text-primary ring-primary/15",
    tileActive: "bg-primary text-primary-foreground ring-primary/40 shadow-sm shadow-primary/30",
    rail: "bg-primary",
    activeBg: "bg-primary/8",
    activeText: "text-primary",
    badge: "bg-primary/15 text-primary",
  },
  sky: {
    tile: "bg-accent-sky/10 text-accent-sky ring-accent-sky/15",
    tileActive: "bg-accent-sky text-accent-sky-foreground ring-accent-sky/40 shadow-sm shadow-accent-sky/30",
    rail: "bg-accent-sky",
    activeBg: "bg-accent-sky/8",
    activeText: "text-accent-sky",
    badge: "bg-accent-sky/15 text-accent-sky",
  },
  cyan: {
    tile: "bg-accent-cyan/10 text-accent-cyan ring-accent-cyan/15",
    tileActive: "bg-accent-cyan text-accent-cyan-foreground ring-accent-cyan/40 shadow-sm shadow-accent-cyan/30",
    rail: "bg-accent-cyan",
    activeBg: "bg-accent-cyan/8",
    activeText: "text-accent-cyan",
    badge: "bg-accent-cyan/15 text-accent-cyan",
  },
  indigo: {
    tile: "bg-accent-indigo/10 text-accent-indigo ring-accent-indigo/15",
    tileActive: "bg-accent-indigo text-accent-indigo-foreground ring-accent-indigo/40 shadow-sm shadow-accent-indigo/30",
    rail: "bg-accent-indigo",
    activeBg: "bg-accent-indigo/8",
    activeText: "text-accent-indigo",
    badge: "bg-accent-indigo/15 text-accent-indigo",
  },
  destructive: {
    tile: "bg-destructive/10 text-destructive ring-destructive/15",
    tileActive: "bg-destructive text-destructive-foreground ring-destructive/40 shadow-sm shadow-destructive/30",
    rail: "bg-destructive",
    activeBg: "bg-destructive/8",
    activeText: "text-destructive",
    badge: "bg-destructive/15 text-destructive",
  },
  slate: {
    tile: "bg-accent-slate/10 text-accent-slate ring-accent-slate/15",
    tileActive: "bg-accent-slate text-accent-slate-foreground ring-accent-slate/40 shadow-sm shadow-accent-slate/30",
    rail: "bg-accent-slate",
    activeBg: "bg-accent-slate/8",
    activeText: "text-accent-slate",
    badge: "bg-accent-slate/15 text-accent-slate",
  },
};

export type NavItem = {
  href: string;
  label: string;
  icon: LucideIcon;
  tone: Tone;
  badge?: string;
};

export function NavRow({ item, active }: { item: NavItem; active: boolean }) {
  const tone = TONE_CONFIG[item.tone];
  const Icon = item.icon;

  return (
    <SidebarMenuItem>
      <SidebarMenuButton
        asChild
        isActive={active}
        tooltip={item.label}
        className={cn(
          "group/nav relative h-12 rounded-xl transition-all duration-200",
          "group-data-[collapsible=icon]:justify-center group-data-[collapsible=icon]:px-0",
          active && tone.activeBg,
          active &&
            "data-[active=true]:bg-transparent data-[active=true]:text-sidebar-foreground hover:bg-transparent",
          !active && "hover:bg-sidebar-accent/60",
        )}
      >
        <Link
          href={item.href}
          className="flex w-full items-center gap-3 group-data-[collapsible=icon]:justify-center"
        >
          <span
            aria-hidden
            className={cn(
              "absolute left-0 top-1/2 h-7 w-1.5 -translate-y-1/2 rounded-r-full transition-all duration-200",
              tone.rail,
              active ? "opacity-100" : "opacity-0",
              "group-data-[collapsible=icon]:h-5",
            )}
          />
          <span
            aria-hidden
            className={cn(
              "grid size-8 shrink-0 place-items-center rounded-xl ring-1 transition-all duration-200",
              active ? tone.tileActive : tone.tile,
              "group-hover/nav:ring-2",
            )}
          >
            <Icon className="size-4" />
          </span>
          <span
            className={cn(
              "truncate text-sm font-medium transition-all duration-200",
              active
                ? cn(tone.activeText, "font-bold")
                : "text-sidebar-foreground",
              "group-data-[collapsible=icon]:hidden",
            )}
          >
            {item.label}
          </span>
        </Link>
      </SidebarMenuButton>
      {item.badge && (
        <SidebarMenuBadge
          className={cn(
            "rounded-md font-mono text-[11px] transition-all duration-200",
            tone.badge,
            "group-data-[collapsible=icon]:hidden",
          )}
        >
          {item.badge}
        </SidebarMenuBadge>
      )}
    </SidebarMenuItem>
  );
}
