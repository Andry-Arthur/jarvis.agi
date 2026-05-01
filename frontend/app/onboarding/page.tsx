"use client";

import { Onboarding } from "../../components/pages/Onboarding";
import { Suspense } from "react";

export default function OnboardingPage() {
  return (
    <Suspense fallback={null}>
      <Onboarding />
    </Suspense>
  );
}

