"use client";

import * as React from "react";
import { Search } from "lucide-react";
import {
    InputGroup,
    InputGroupAddon,
    InputGroupInput,
} from "@/components/ui/input-group";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { problemLabels, type Problem } from "@/lib/csv";

type AlertSearchProps = {
    query: string;
    onQueryChange: (q: string) => void;
    problemFilter: "all" | Problem;
    onProblemFilterChange: (v: "all" | Problem) => void;
    totalAlerts: number;
    problemCounts: Record<Problem, number>;
};

export function AlertSearch({
    query,
    onQueryChange,
    problemFilter,
    onProblemFilterChange,
    totalAlerts,
    problemCounts,
}: AlertSearchProps) {
    return (
        <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
            <InputGroup className="h-9 w-full rounded-lg sm:w-64">
                <InputGroupAddon>
                    <Search className="size-4 text-muted-foreground" />
                </InputGroupAddon>
                <InputGroupInput
                    placeholder="Tìm sinh viên, cố vấn..."
                    value={query}
                    onChange={(e) => onQueryChange(e.target.value)}
                    aria-label="Tìm cảnh báo"
                />
            </InputGroup>
            <Tabs
                value={problemFilter}
                onValueChange={(v) =>
                    onProblemFilterChange(v as "all" | Problem)
                }
                className="w-full sm:w-auto"
            >
                <div className="hide-scrollbar w-full overflow-x-auto">
                    <TabsList className="h-9 w-max min-w-full rounded-lg sm:w-auto sm:min-w-0">
                        <TabsTrigger
                            value="all"
                            className="rounded-md px-2.5 text-xs sm:text-sm"
                        >
                            Tất cả{" "}
                            <span className="ml-1 font-mono text-muted-foreground">
                                {totalAlerts}
                            </span>
                        </TabsTrigger>
                        <TabsTrigger
                            value="failed_final"
                            className="rounded-md px-2.5 text-xs sm:text-sm"
                            title={problemLabels.failed_final}
                        >
                            Cuối kỳ{" "}
                            <span className="ml-1 font-mono text-muted-foreground">
                                {problemCounts.failed_final}
                            </span>
                        </TabsTrigger>
                        <TabsTrigger
                            value="failed_midterm"
                            className="rounded-md px-2.5 text-xs sm:text-sm"
                            title={problemLabels.failed_midterm}
                        >
                            Giữa kỳ{" "}
                            <span className="ml-1 font-mono text-muted-foreground">
                                {problemCounts.failed_midterm}
                            </span>
                        </TabsTrigger>
                        <TabsTrigger
                            value="low_average"
                            className="rounded-md px-2.5 text-xs sm:text-sm"
                            title={problemLabels.low_average}
                        >
                            TB thấp{" "}
                            <span className="ml-1 font-mono text-muted-foreground">
                                {problemCounts.low_average}
                            </span>
                        </TabsTrigger>
                    </TabsList>
                </div>
            </Tabs>
        </div>
    );
}
