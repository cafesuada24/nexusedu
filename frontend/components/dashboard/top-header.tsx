"use client"

import * as React from "react"
import Link from "next/link"
import { usePathname } from "next/navigation"
import { Search } from "lucide-react"
import { SidebarTrigger } from "@/components/ui/sidebar"
import {
  InputGroup,
  InputGroupAddon,
  InputGroupInput,
} from "@/components/ui/input-group"
import { Separator } from "@/components/ui/separator"
import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbLink,
  BreadcrumbList,
  BreadcrumbPage,
  BreadcrumbSeparator,
} from "@/components/ui/breadcrumb"
import { ThemeToggle } from "@/components/theme-toggle"
import { Kbd } from "@/components/ui/kbd"
import { NotificationsDropdown } from "@/components/dashboard/notifications-dropdown"
import { UserDropdown } from "@/components/dashboard/sidebar/user-dropdown"
import { AdvisorScore } from "@/components/dashboard/advisor-score"

const labels: Record<string, string> = {
  dashboard: "Tổng quan",
  import: "Nhập CSV",
  alerts: "Trung tâm cảnh báo",
  metrics: "Báo cáo BGH",
  settings: "Cài đặt",
  support: "Hỗ trợ",
}

export function TopHeader() {
  const pathname = usePathname()
  const segments = pathname.split("/").filter(Boolean)

  return (
    <header className="sticky top-0 z-30 flex h-16 items-center gap-3 border-b border-slate-200/80 bg-background/85 px-4 backdrop-blur md:px-6 dark:border-slate-800 dark:bg-[#020617]/95">
      <SidebarTrigger className="-ml-1 rounded-lg text-slate-600 hover:text-slate-900 dark:text-slate-300 dark:hover:text-slate-100" />
      <Separator orientation="vertical" className="h-5" />

      <Breadcrumb className="hidden md:block">
        <BreadcrumbList className="text-slate-500 dark:text-slate-400">
          <BreadcrumbItem>
            <BreadcrumbLink asChild className="text-slate-600 hover:text-slate-900 dark:text-slate-300 dark:hover:text-slate-100">
              <Link href="/dashboard">NexusEdu</Link>
            </BreadcrumbLink>
          </BreadcrumbItem>
          {segments.slice(1).map((seg, i, arr) => {
            const href = "/" + segments.slice(0, i + 2).join("/")
            const isLast = i === arr.length - 1
            const label = labels[seg] ?? seg
            return (
              <React.Fragment key={href}>
                <BreadcrumbSeparator className="text-slate-400 dark:text-slate-500" />
                <BreadcrumbItem>
                  {isLast ? (
                    <BreadcrumbPage className="font-medium text-slate-800 dark:text-slate-100">{label}</BreadcrumbPage>
                  ) : (
                    <BreadcrumbLink asChild className="text-slate-600 hover:text-slate-900 dark:text-slate-300 dark:hover:text-slate-100">
                      <Link href={href}>{label}</Link>
                    </BreadcrumbLink>
                  )}
                </BreadcrumbItem>
              </React.Fragment>
            )
          })}
          {segments.length === 1 && (
            <>
              <BreadcrumbSeparator className="text-slate-400 dark:text-slate-500" />
              <BreadcrumbItem>
                <BreadcrumbPage className="font-medium text-slate-800 dark:text-slate-100">Tổng quan</BreadcrumbPage>
              </BreadcrumbItem>
            </>
          )}
        </BreadcrumbList>
      </Breadcrumb>

      <div className="ml-auto flex items-center gap-2">
        <div className="hidden w-72 md:block">
          <InputGroup className="h-10 rounded-xl border-slate-200/90 bg-white/90 shadow-sm shadow-slate-200/40 dark:border-slate-700 dark:bg-slate-900/90 dark:shadow-none">
            <InputGroupAddon className="text-slate-500 dark:text-slate-400">
              <Search className="size-4" />
            </InputGroupAddon>
            <InputGroupInput
              placeholder="Tìm sinh viên, cố vấn..."
              aria-label="Tìm kiếm"
              className="text-slate-800 placeholder:text-slate-400 dark:text-slate-100 dark:placeholder:text-slate-500"
            />
            <InputGroupAddon align="inline-end" className="text-slate-500 dark:text-slate-400">
              <Kbd className="bg-slate-100 text-slate-500 dark:bg-slate-800 dark:text-slate-400">⌘K</Kbd>
            </InputGroupAddon>
          </InputGroup>
        </div>

        <NotificationsDropdown />
        <AdvisorScore />
        <UserDropdown />
      </div>
    </header>
  )
}
