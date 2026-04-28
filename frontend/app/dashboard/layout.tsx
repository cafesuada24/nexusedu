import type { ReactNode } from "react"
import { SidebarInset, SidebarProvider } from "@/components/ui/sidebar"
import { AppSidebar } from "@/components/dashboard/app-sidebar"
import { TopHeader } from "@/components/dashboard/top-header"
import { DashboardFooter } from "@/components/dashboard/dashboard-footer"

export default function DashboardLayout({ children }: { children: ReactNode }) {
  return (
    <SidebarProvider defaultOpen>
      <AppSidebar />
      <SidebarInset className="dashboard-canvas">
        <TopHeader />
        <div className="flex w-full flex-1 flex-col p-4 md:p-6 lg:px-8">{children}</div>
        <DashboardFooter />
      </SidebarInset>
    </SidebarProvider>
  )
}
