import { create } from "zustand";
import { persist } from "zustand/middleware";

interface OnboardingState {
  onboardingCompleted: boolean;
  /** True if user chose "Skip setup" */
  skippedSetup: boolean;
  complete: () => void;
  skip: () => void;
  /** Clear completion so first-run flow can show again (e.g. after reset) */
  resetProgress: () => void;
}

export const useOnboardingStore = create<OnboardingState>()(
  persist(
    (set) => ({
      onboardingCompleted: false,
      skippedSetup: false,
      complete: () =>
        set({ onboardingCompleted: true, skippedSetup: false }),
      skip: () =>
        set({ onboardingCompleted: true, skippedSetup: true }),
      resetProgress: () =>
        set({ onboardingCompleted: false, skippedSetup: false }),
    }),
    { name: "jarvis_onboarding" }
  )
);
