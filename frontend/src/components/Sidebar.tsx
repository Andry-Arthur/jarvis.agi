import {
  Bot,
  LayoutDashboard,
  Plug,
  Settings,
  Trash2,
} from "lucide-react";
import { NavLink } from "react-router-dom";

interface SidebarProps {
  onClear: () => void;
}

const navItems = [
  { to: "/", icon: LayoutDashboard, label: "Dashboard" },
  { to: "/integrations", icon: Plug, label: "Integrations" },
  { to: "/settings", icon: Settings, label: "Settings" },
];

export function Sidebar({ onClear }: SidebarProps) {
  return (
    <aside className="flex h-full w-16 flex-col items-center border-r border-gray-800 bg-gray-900 py-4 md:w-56 md:items-start md:px-3">
      {/* Logo */}
      <div className="mb-8 flex items-center gap-2 px-1">
        <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-jarvis-600">
          <Bot className="h-5 w-5 text-white" />
        </div>
        <span className="hidden text-lg font-bold tracking-tight text-white md:block">
          JARVIS<span className="text-jarvis-400">.AGI</span>
        </span>
      </div>

      {/* Nav */}
      <nav className="flex flex-1 flex-col gap-1 w-full">
        {navItems.map(({ to, icon: Icon, label }) => (
          <NavLink
            key={to}
            to={to}
            end={to === "/"}
            className={({ isActive }) =>
              `flex items-center gap-3 rounded-lg px-2 py-2.5 text-sm font-medium transition-colors ${
                isActive
                  ? "bg-jarvis-600/20 text-jarvis-400"
                  : "text-gray-400 hover:bg-gray-800 hover:text-gray-100"
              }`
            }
          >
            <Icon className="h-5 w-5 shrink-0" />
            <span className="hidden md:block">{label}</span>
          </NavLink>
        ))}
      </nav>

      {/* Clear chat */}
      <button
        onClick={onClear}
        className="flex items-center gap-3 rounded-lg px-2 py-2.5 text-sm font-medium text-gray-500 transition-colors hover:bg-gray-800 hover:text-red-400 w-full"
        title="Clear conversation"
      >
        <Trash2 className="h-5 w-5 shrink-0" />
        <span className="hidden md:block">Clear chat</span>
      </button>
    </aside>
  );
}
