"use client";

import { ProtectedShell } from "../../components/ProtectedShell";
import { Tools } from "../../components/pages/Tools";

export default function ToolsPage() {
  return (
    <ProtectedShell onClearChat={() => {}}>
      <Tools />
    </ProtectedShell>
  );
}

