import { create } from "zustand";
import { persist } from "zustand/middleware";
import type { Provider } from "../types";

interface ProviderState {
  provider: Provider;
  setProvider: (p: Provider) => void;
}

export const useProviderStore = create<ProviderState>()(
  persist(
    (set) => ({
      provider: "openai",
      setProvider: (provider) => set({ provider }),
    }),
    { name: "jarvis_provider" }
  )
);
