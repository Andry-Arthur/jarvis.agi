import { create } from "zustand";
import type { Provider } from "../types";

interface ProviderState {
  provider: Provider;
  setProvider: (provider: Provider) => void;
}

export const useProviderStore = create<ProviderState>((set) => ({
  provider: "openai",
  setProvider: (provider) => set({ provider }),
}));

