"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { Sidebar } from "./Sidebar";
import { useOnboardingStore } from "../store/onboarding";

export function ProtectedShell({
  children,
  onClearChat,
}: {
  children: React.ReactNode;
  onClearChat: () => void;
}) {
  const router = useRouter();
  const completed = useOnboardingStore((s) => s.onboardingCompleted);

  useEffect(() => {
    if (!completed) router.replace("/onboarding");
  }, [completed, router]);

  if (!completed) return null;

  return (
    <div className="flex h-screen overflow-hidden bg-page">
      <Sidebar onClear={onClearChat} />
      <main className="flex flex-1 flex-col overflow-hidden">{children}</main>
    </div>
  );
}

