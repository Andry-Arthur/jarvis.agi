import { beforeEach, describe, expect, it } from "vitest";
import { useOnboardingStore } from "./onboarding";

describe("useOnboardingStore", () => {
  beforeEach(() => {
    localStorage.clear();
    useOnboardingStore.setState({
      onboardingCompleted: false,
      skippedSetup: false,
    });
  });

  it("starts incomplete", () => {
    expect(useOnboardingStore.getState().onboardingCompleted).toBe(false);
    expect(useOnboardingStore.getState().skippedSetup).toBe(false);
  });

  it("complete marks finished without skipped", () => {
    useOnboardingStore.getState().complete();
    expect(useOnboardingStore.getState().onboardingCompleted).toBe(true);
    expect(useOnboardingStore.getState().skippedSetup).toBe(false);
  });

  it("skip marks finished with skipped", () => {
    useOnboardingStore.getState().skip();
    expect(useOnboardingStore.getState().onboardingCompleted).toBe(true);
    expect(useOnboardingStore.getState().skippedSetup).toBe(true);
  });

  it("resetProgress clears completion flags", () => {
    useOnboardingStore.getState().complete();
    useOnboardingStore.getState().resetProgress();
    expect(useOnboardingStore.getState().onboardingCompleted).toBe(false);
    expect(useOnboardingStore.getState().skippedSetup).toBe(false);
  });
});
