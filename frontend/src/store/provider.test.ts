import { beforeEach, describe, expect, it } from "vitest";
import { useProviderStore } from "./provider";

describe("useProviderStore", () => {
  beforeEach(() => {
    localStorage.clear();
    useProviderStore.setState({ provider: "openai" });
  });

  it("defaults to openai", () => {
    expect(useProviderStore.getState().provider).toBe("openai");
  });

  it("setProvider updates the selected model", () => {
    useProviderStore.getState().setProvider("anthropic");
    expect(useProviderStore.getState().provider).toBe("anthropic");
    useProviderStore.getState().setProvider("ollama");
    expect(useProviderStore.getState().provider).toBe("ollama");
  });
});
