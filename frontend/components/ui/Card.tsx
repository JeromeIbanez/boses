import { cn } from "@/lib/utils";

interface CardProps {
  children: React.ReactNode;
  className?: string;
  onClick?: () => void;
}

export default function Card({ children, className, onClick }: CardProps) {
  return (
    <div
      className={cn(
        "bg-white border border-zinc-200 rounded-lg p-5",
        onClick && "cursor-pointer hover:border-indigo-200 card-interactive transition-all",
        className
      )}
      onClick={onClick}
    >
      {children}
    </div>
  );
}
