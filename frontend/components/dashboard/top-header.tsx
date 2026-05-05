"use client"

import * as React from "react"
import Link from "next/link"
import { usePathname } from "next/navigation"
import { Bell, Search } from "lucide-react"
import { SidebarTrigger } from "@/components/ui/sidebar"
import {
  InputGroup,
  InputGroupAddon,
  InputGroupInput,
} from "@/components/ui/input-group"
import { Button } from "@/components/ui/button"
import { Separator } from "@/components/ui/separator"
import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbLink,
  BreadcrumbList,
  BreadcrumbPage,
  BreadcrumbSeparator,
} from "@/components/ui/breadcrumb"
import { Badge } from "@/components/ui/badge"
import { ThemeToggle } from "@/components/theme-toggle"
import { Kbd } from "@/components/ui/kbd"
import { NotificationsDropdown } from "@/components/dashboard/notifications-dropdown"
import { UserDropdown } from "@/components/dashboard/sidebar/user-dropdown"
import { AdvisorScore } from "@/components/dashboard/advisor-score"

const labels: Record<string, string> = {
  dashboard: "Tổng quan",
  import: "Nhập CSV",
  alerts: "Alert Center",
  metrics: "BGH Dashboard",
  settings: "Cài đặt",
  support: "Hỗ trợ",
}

export function TopHeader() {
  const pathname = usePathname()
  const segments = pathname.split("/").filter(Boolean)

  return (
    <header className="sticky top-0 z-30 flex h-16 items-center gap-3 border-b border-border/60 glass-strong px-4 md:px-6">
      <SidebarTrigger className="-ml-1 rounded-lg" />
      <Separator orientation="vertical" className="h-5" />

      <Breadcrumb className="hidden md:block">
        <BreadcrumbList>
          <BreadcrumbItem>
            <BreadcrumbLink asChild>
              <Link href="/dashboard">NexusEdu</Link>
            </BreadcrumbLink>
          </BreadcrumbItem>
          {segments.slice(1).map((seg, i, arr) => {
            const href = "/" + segments.slice(0, i + 2).join("/")
            const isLast = i === arr.length - 1
            const label = labels[seg] ?? seg
            return (
              <React.Fragment key={href}>
                <BreadcrumbSeparator />
                <BreadcrumbItem>
                  {isLast ? (
                    <BreadcrumbPage>{label}</BreadcrumbPage>
                  ) : (
                    <BreadcrumbLink asChild>
                      <Link href={href}>{label}</Link>
                    </BreadcrumbLink>
                  )}
                </BreadcrumbItem>
              </React.Fragment>
            )
          })}
          {segments.length === 1 && (
            <>
              <BreadcrumbSeparator />
              <BreadcrumbItem>
                <BreadcrumbPage>Tổng quan</BreadcrumbPage>
              </BreadcrumbItem>
            </>
          )}
        </BreadcrumbList>
      </Breadcrumb>

      <div className="ml-auto flex items-center gap-2">
        <div className="hidden w-72 md:block">
          <InputGroup className="h-10 rounded-xl">
            <InputGroupAddon>
              <Search className="size-4 text-muted-foreground" />
            </InputGroupAddon>
            <InputGroupInput
              placeholder="Tìm sinh viên, cố vấn..."
              aria-label="Tìm kiếm"
            />
            <InputGroupAddon align="inline-end">
              <Kbd>⌘K</Kbd>
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
