"use client";

import * as React from "react";
import { useRouter } from "next/navigation";
import { ClipboardList } from "lucide-react";
import { useAuth } from "@/hooks/use-auth";
import { CaseManagementBoard } from "@/components/dashboard/case-management/case-management-board";

export default function CasesPage() {
    const router = useRouter();
    const { user, loading } = useAuth();

    React.useEffect(() => {
        if (!loading && user && user.role !== "admin") {
            router.replace("/dashboard/alerts");
        }
    }, [user, loading, router]);

    if (loading || !user || user.role !== "admin") {
        return null;
    }

    return (
        <div className="flex h-full min-h-0 w-full min-w-0 max-w-full flex-1 flex-col gap-4 overflow-hidden">
            <div className="flex flex-wrap items-center gap-3">
                <div className="grid size-10 place-items-center rounded-xl bg-primary/10 text-primary ring-1 ring-primary/20 shadow-sm shadow-primary/10">
                    <ClipboardList className="size-5" />
                </div>
                <h1 className="font-serif text-2xl font-bold tracking-tight md:text-3xl">
                    Quản lý case sinh viên
                </h1>
            </div>

            <div
                aria-hidden
                className="h-px w-full bg-gradient-to-r from-primary/40 via-info/30 to-transparent"
            />

            <div className="flex-1 overflow-auto pr-1">
                <CaseManagementBoard />
            </div>
        </div>
    );
}
