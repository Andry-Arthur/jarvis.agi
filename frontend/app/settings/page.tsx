"use client";

import { ProtectedShell } from "../../components/ProtectedShell";
import { Settings } from "../../components/pages/Settings";

export default function SettingsPage() {
  return (
    <ProtectedShell onClearChat={() => {}}>
      <Settings />
    </ProtectedShell>
  );
}

