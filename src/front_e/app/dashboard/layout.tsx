import type { ReactNode } from "react"
import { SidebarInset, SidebarProvider } from "@/components/ui/sidebar"
import { AppSidebar } from "@/components/dashboard/app-sidebar"
import { TopHeader } from "@/components/dashboard/top-header"
import { DashboardFooter } from "@/components/dashboard/dashboard-footer"

export default function DashboardLayout({ children }: { children: ReactNode }) {
  return (
    <SidebarProvider defaultOpen>
      <AppSidebar />
      <SidebarInset className="bg-background">
        <TopHeader />
        <div className="flex-1 p-4 md:p-6">{children}</div>
        <DashboardFooter />
      </SidebarInset>
    </SidebarProvider>
  )
}
