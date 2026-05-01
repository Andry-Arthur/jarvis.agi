"use client";

import { ProtectedShell } from "../../components/ProtectedShell";
import { Integrations } from "../../components/pages/Integrations";

export default function IntegrationsPage() {
  return (
    <ProtectedShell onClearChat={() => {}}>
      <Integrations />
    </ProtectedShell>
  );
}

