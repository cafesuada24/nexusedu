import { Skeleton } from "@/components/ui/skeleton";

export default function DashboardLoading() {
  return (
    <div className="flex flex-col gap-6 p-6">
      <div className="flex items-center justify-between">
        <Skeleton className="h-10 w-[250px]" />
        <Skeleton className="h-10 w-[150px]" />
      </div>
      <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-4">
        <Skeleton className="h-[120px] rounded-xl" />
        <Skeleton className="h-[120px] rounded-xl" />
        <Skeleton className="h-[120px] rounded-xl" />
        <Skeleton className="h-[120px] rounded-xl" />
      </div>
      <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-7">
        <Skeleton className="col-span-4 h-[400px] rounded-xl" />
        <Skeleton className="col-span-3 h-[400px] rounded-xl" />
      </div>
    </div>
  );
}
