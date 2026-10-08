import { describe, expect, it } from "vitest";
import { base64Url, codeChallenge, tokenExpiry } from "./pkce";

describe("PKCE", () => {
  it("computes the RFC 7636 appendix B challenge", async () => {
    expect(await codeChallenge("dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk")).toBe(
      "E9Melhoa2OwvFrEMTJguCHaoeK1t8URWbuGJSstw-cM",
    );
  });

  it("encodes base64url without padding", () => {
    expect(base64Url(new Uint8Array([251, 255]))).toBe("-_8");
  });

  it("reads a token expiry and tolerates garbage", () => {
    const payload = base64Url(new TextEncoder().encode(JSON.stringify({ exp: 1700000000 })));
    expect(tokenExpiry(`h.${payload}.s`)).toBe(1700000000 * 1000);
    expect(tokenExpiry("not-a-token")).toBeNull();
  });
});
