import { describe, expect, it } from "vitest";
import type { EnvVarStatus, EnvVarsResponse } from "../types";
import { isLlmSetupSatisfied, providerEnvFields } from "./llmSetup";

function vars(partial: Partial<Record<string, Partial<EnvVarStatus>>>): EnvVarsResponse["vars"] {
  const base = (key: string): EnvVarStatus => ({
    label: key,
    section: "LLM",
    secret: key.includes("KEY"),
    is_set: false,
    masked_value: null,
    placeholder: "",
  });
  return {
    OPENAI_API_KEY: { ...base("OPENAI_API_KEY"), ...partial.OPENAI_API_KEY },
    ANTHROPIC_API_KEY: { ...base("ANTHROPIC_API_KEY"), ...partial.ANTHROPIC_API_KEY },
    OLLAMA_BASE_URL: { ...base("OLLAMA_BASE_URL"), ...partial.OLLAMA_BASE_URL },
    OLLAMA_MODEL: { ...base("OLLAMA_MODEL"), ...partial.OLLAMA_MODEL },
  } as EnvVarsResponse["vars"];
}

describe("isLlmSetupSatisfied", () => {
  it("requires OpenAI key when set", () => {
    expect(isLlmSetupSatisfied("openai", vars({ OPENAI_API_KEY: { is_set: true } }))).toBe(true);
    expect(isLlmSetupSatisfied("openai", vars({ OPENAI_API_KEY: { is_set: false } }))).toBe(false);
  });

  it("requires Anthropic key when set", () => {
    expect(isLlmSetupSatisfied("anthropic", vars({ ANTHROPIC_API_KEY: { is_set: true } }))).toBe(
      true
    );
    expect(isLlmSetupSatisfied("anthropic", vars({}))).toBe(false);
  });

  it("treats Ollama as satisfied when vars exist", () => {
    expect(isLlmSetupSatisfied("ollama", vars({}))).toBe(true);
  });

  it("returns false when vars undefined", () => {
    expect(isLlmSetupSatisfied("openai", undefined)).toBe(false);
  });
});

describe("providerEnvFields", () => {
  it("returns expected keys per provider", () => {
    expect(providerEnvFields("openai")).toEqual(["OPENAI_API_KEY"]);
    expect(providerEnvFields("anthropic")).toEqual(["ANTHROPIC_API_KEY"]);
    expect(providerEnvFields("ollama")).toEqual(["OLLAMA_BASE_URL", "OLLAMA_MODEL"]);
  });
});
