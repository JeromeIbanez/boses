import { LucideIcon } from "lucide-react";

interface EmptyStateProps {
  icon: LucideIcon;
  title: string;
  description?: string;
  action?: React.ReactNode;
}

export default function EmptyState({ icon: Icon, title, description, action }: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center py-16 text-center">
      <div className="w-10 h-10 rounded-xl bg-zinc-100 flex items-center justify-center mb-4">
        <Icon size={18} className="text-zinc-400" strokeWidth={1.5} />
      </div>
      <h3 className="text-sm font-medium text-zinc-800">{title}</h3>
      {description && <p className="text-sm text-zinc-400 mt-1 max-w-xs">{description}</p>}
      {action && <div className="mt-5">{action}</div>}
    </div>
  );
}
