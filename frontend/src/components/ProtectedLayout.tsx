import { Navigate, Outlet } from "react-router-dom";
import { Sidebar } from "./Sidebar";
import { useOnboardingStore } from "../store/onboarding";

interface Props {
  onClearChat: () => void;
}

export function ProtectedLayout({ onClearChat }: Props) {
  const completed = useOnboardingStore((s) => s.onboardingCompleted);

  if (!completed) {
    return <Navigate to="/onboarding" replace />;
  }

  return (
    <div className="flex h-screen overflow-hidden bg-page">
      <Sidebar onClear={onClearChat} />
      <main className="flex flex-1 flex-col overflow-hidden">
        <Outlet />
      </main>
    </div>
  );
}
