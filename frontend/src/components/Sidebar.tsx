import {
  Bot,
  Laptop,
  LayoutDashboard,
  Plug,
  Settings,
  Sparkles,
  Trash2,
  Wrench,
} from "lucide-react";
import { NavLink } from "react-router-dom";

interface SidebarProps {
  onClear: () => void;
}

const navItems = [
  { to: "/", icon: LayoutDashboard, label: "Dashboard" },
  { to: "/integrations", icon: Plug, label: "Integrations" },
  { to: "/tools", icon: Wrench, label: "Tools" },
  { to: "/settings", icon: Settings, label: "Settings" },
];

export function Sidebar({ onClear }: SidebarProps) {
  return (
    <aside className="flex h-full w-16 flex-col items-center border-r border-border bg-surface py-4 shadow-sm md:w-56 md:items-start md:px-3">
      <div className="mb-8 flex items-center gap-2 px-1">
        <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-jarvis-600 shadow-sm">
          <Bot className="h-5 w-5 text-white" />
        </div>
        <span className="hidden text-lg font-bold tracking-tight text-fg md:block">
          JARVIS<span className="text-jarvis-600">.AGI</span>
        </span>
      </div>

      <nav className="flex w-full flex-1 flex-col gap-1">
        <NavLink
          to="/install"
          className={({ isActive }) =>
            `flex items-center gap-3 rounded-lg px-2 py-2.5 text-sm font-medium transition-colors ${
              isActive
                ? "bg-accent-muted text-jarvis-700"
                : "text-muted hover:bg-surface-muted hover:text-fg"
            }`
          }
        >
          <Laptop className="h-5 w-5 shrink-0" />
          <span className="hidden md:block">Install</span>
        </NavLink>
        <NavLink
          to="/onboarding?review=1"
          className={({ isActive }) =>
            `flex items-center gap-3 rounded-lg px-2 py-2.5 text-sm font-medium transition-colors ${
              isActive
                ? "bg-accent-muted text-jarvis-700"
                : "text-muted hover:bg-surface-muted hover:text-fg"
            }`
          }
        >
          <Sparkles className="h-5 w-5 shrink-0" />
          <span className="hidden md:block">Setup guide</span>
        </NavLink>
        {navItems.map(({ to, icon: Icon, label }) => (
          <NavLink
            key={to}
            to={to}
            end={to === "/"}
            className={({ isActive }) =>
              `flex items-center gap-3 rounded-lg px-2 py-2.5 text-sm font-medium transition-colors ${
                isActive
                  ? "bg-accent-muted text-jarvis-700"
                  : "text-muted hover:bg-surface-muted hover:text-fg"
              }`
            }
          >
            <Icon className="h-5 w-5 shrink-0" />
            <span className="hidden md:block">{label}</span>
          </NavLink>
        ))}
      </nav>

      <button
        onClick={onClear}
        className="flex w-full items-center gap-3 rounded-lg px-2 py-2.5 text-sm font-medium text-muted transition-colors hover:bg-red-50 hover:text-red-600"
        title="Clear conversation"
      >
        <Trash2 className="h-5 w-5 shrink-0" />
        <span className="hidden md:block">Clear chat</span>
      </button>
    </aside>
  );
}
