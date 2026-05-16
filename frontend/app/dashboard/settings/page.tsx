import { Settings as SettingsIcon } from "lucide-react"
import { SettingsView } from "@/components/dashboard/settings-view"

export default function SettingsPage() {
  return (
    <div className="flex w-full flex-1 flex-col gap-6">
      <div className="flex items-center gap-3">
        <div className="grid size-10 place-items-center rounded-xl bg-accent-slate/10 text-accent-slate ring-1 ring-accent-slate/20 shadow-sm shadow-accent-slate/10">
          <SettingsIcon className="size-5" />
        </div>
        <h1 className="font-serif text-2xl font-bold tracking-tight md:text-3xl">
          Cài đặt
        </h1>
      </div>
      <div
        aria-hidden
        className="h-px w-full bg-gradient-to-r from-accent-slate/40 via-primary/20 to-transparent"
      />
      <SettingsView />
    </div>
  )
}
