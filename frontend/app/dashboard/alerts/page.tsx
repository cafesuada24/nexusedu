"use client";

import * as React from "react";
import { useRouter } from "next/navigation";
import { BellRing } from "lucide-react";
import { useAuth } from "@/hooks/use-auth";
import { AlertCenter } from "@/components/dashboard/alert-center";

export default function AlertsPage() {
  const router = useRouter();
  const { user, loading } = useAuth();

  React.useEffect(() => {
    if (!loading && user?.role === "admin") {
      router.replace("/dashboard/cases");
    }
  }, [user, loading, router]);

  if (loading || user?.role === "admin") {
    return null;
  }

  return (
    <div className="flex h-full min-h-0 w-full min-w-0 max-w-full flex-1 flex-col gap-4 overflow-hidden">
      <div className="flex flex-wrap items-center gap-3">
        <div className="grid size-10 place-items-center rounded-xl bg-destructive/10 text-destructive ring-1 ring-destructive/20 shadow-sm shadow-destructive/10">
          <BellRing className="size-5" />
        </div>
        <h1 className="font-serif text-2xl font-bold tracking-tight md:text-3xl">
          Trung tâm cảnh báo
        </h1>
      </div>

      <div
        aria-hidden
        className="h-px w-full bg-gradient-to-r from-destructive/40 via-warning/30 to-transparent"
      />

      <AlertCenter />
    </div>
  );
}
