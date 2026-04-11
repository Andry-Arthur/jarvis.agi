import { describe, expect, it, vi } from "vitest";
import { apiUrl } from "./apiBase";

describe("apiUrl", () => {
  it("returns path-only when VITE_API_ORIGIN unset", () => {
    vi.stubEnv("VITE_API_ORIGIN", "");
    expect(apiUrl("/api/config")).toBe("/api/config");
  });

  it("prefixes origin without double slashes", () => {
    vi.stubEnv("VITE_API_ORIGIN", "https://api.example.com");
    expect(apiUrl("/api/config")).toBe("https://api.example.com/api/config");
  });

  it("strips trailing slash from origin", () => {
    vi.stubEnv("VITE_API_ORIGIN", "https://api.example.com/");
    expect(apiUrl("/api/config")).toBe("https://api.example.com/api/config");
  });
});
