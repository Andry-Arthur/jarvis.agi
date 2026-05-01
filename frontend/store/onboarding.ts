import { create } from "zustand";
import { persist } from "zustand/middleware";

interface OnboardingState {
  onboardingCompleted: boolean;
  skippedSetup: boolean;
  complete: () => void;
  skip: () => void;
  resetProgress: () => void;
}

export const useOnboardingStore = create<OnboardingState>()(
  persist(
    (set) => ({
      onboardingCompleted: false,
      skippedSetup: false,
      complete: () => set({ onboardingCompleted: true, skippedSetup: false }),
      skip: () => set({ onboardingCompleted: true, skippedSetup: true }),
      resetProgress: () => set({ onboardingCompleted: false, skippedSetup: false }),
    }),
    { name: "jarvis_onboarding" }
  )
);

