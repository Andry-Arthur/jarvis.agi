import type { EnvVarsResponse } from "../types";
import type { Provider } from "../types";

/**
 * Whether the selected provider has minimum config for chat (keys / Ollama fields).
 */
export function isLlmSetupSatisfied(
  provider: Provider,
  vars: EnvVarsResponse["vars"] | undefined
): boolean {
  if (!vars) return false;
  switch (provider) {
    case "openai":
      return vars.OPENAI_API_KEY?.is_set === true;
    case "anthropic":
      return vars.ANTHROPIC_API_KEY?.is_set === true;
    case "ollama":
      // Local Ollama has no API key; optional URL/model in .env
      return true;
    default:
      return false;
  }
}

/** Env keys to PATCH together with DEFAULT_LLM for each provider (non-empty values only). */
export function providerEnvFields(provider: Provider): string[] {
  switch (provider) {
    case "openai":
      return ["OPENAI_API_KEY"];
    case "anthropic":
      return ["ANTHROPIC_API_KEY"];
    case "ollama":
      return ["OLLAMA_BASE_URL", "OLLAMA_MODEL"];
    default:
      return [];
  }
}
