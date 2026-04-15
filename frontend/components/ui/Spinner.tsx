import { cn } from "@/lib/utils";

export default function Spinner({ className }: { className?: string }) {
  return (
    <div
      className={cn(
        "inline-block h-4 w-4 rounded-full border-2 border-zinc-300 border-t-indigo-500 animate-spin",
        className
      )}
    />
  );
}
