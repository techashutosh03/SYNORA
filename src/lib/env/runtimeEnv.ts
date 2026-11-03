import { validateSecrets } from "../../shared/utils/secretsValidator.ts";

export interface EnvValidationError {
  name: string;
  issue: string;
  hint?: string;
}

export interface WebRuntimeEnvValidationResult {
  valid: boolean;
  errors: EnvValidationError[];
  data: Record<string, any>;
}

const BOOLEAN_KEYS = [
  "AUTH_COOKIE_SECURE",
  "REQUIRE_API_KEY",
  "PRICING_SYNC_ENABLED",
  "OMNIROUTE_DISABLE_BACKGROUND_SERVICES",
];

const PORT_KEYS = ["API_PORT", "DASHBOARD_PORT", "OMNIROUTE_PORT"];

const URL_KEYS = ["CLOUD_URL", "NEXT_PUBLIC_CLOUD_URL", "NEXT_PUBLIC_BASE_URL"];

export function formatRuntimeEnvValidationErrors(errors: EnvValidationError[]): string {
  const lines = errors.map((err) => {
    const hintPart = err.hint ? ` (${err.hint})` : "";
    return `• ${err.name}: ${err.issue}${hintPart}`;
  });
  return `Runtime Environment Configuration Errors:\n${lines.join("\n")}`;
}

export function validateWebRuntimeEnv(env: Record<string, any> = process.env): WebRuntimeEnvValidationResult {
  const secretValidation = validateSecrets(env);
  const errors = [...secretValidation.errors];
  const data: Record<string, any> = { ...env };

  for (const key of BOOLEAN_KEYS) {
    const val = env[key];
    if (val !== undefined && val !== null && val !== "") {
      const s = String(val).trim().toLowerCase();
      if (s !== "true" && s !== "false") {
        errors.push({
          name: key,
          issue: `Invalid boolean value "${val}" for ${key}. Expected "true" or "false".`,
          hint: `Set ${key}=true or ${key}=false`,
        });
      }
    }
  }

  for (const key of PORT_KEYS) {
    const val = env[key];
    if (val !== undefined && val !== null && val !== "") {
      const portNum = Number(val);
      if (!Number.isInteger(portNum) || portNum < 1 || portNum > 65535) {
        errors.push({
          name: key,
          issue: `Invalid port value "${val}" for ${key}. Expected integer between 1 and 65535.`,
          hint: `Choose a valid port between 1 and 65535`,
        });
      }
    }
  }

  for (const key of URL_KEYS) {
    const val = env[key];
    if (val !== undefined && val !== null && val !== "") {
      try {
        const parsed = new URL(String(val));
        if (parsed.protocol !== "http:" && parsed.protocol !== "https:") {
          errors.push({
            name: key,
            issue: `Invalid URL protocol "${parsed.protocol}" for ${key}. Expected http: or https:.`,
            hint: `Use a valid http:// or https:// URL`,
          });
        }
      } catch {
        errors.push({
          name: key,
          issue: `Malformed URL "${val}" for ${key}.`,
          hint: `Must be a valid URL starting with http:// or https://`,
        });
      }
    }
  }

  return {
    valid: errors.length === 0,
    errors,
    data,
  };
}

export function getWebRuntimeEnv(env: Record<string, any> = process.env): Record<string, any> {
  const result = validateWebRuntimeEnv(env);
  if (!result.valid) {
    throw new Error(formatRuntimeEnvValidationErrors(result.errors));
  }
  return result.data;
}

export function enforceWebRuntimeEnv(env: Record<string, any> = process.env): Record<string, any> {
  const result = validateWebRuntimeEnv(env);
  if (!result.valid) {
    console.error(formatRuntimeEnvValidationErrors(result.errors));
    process.exit(1);
  }
  return result.data;
}
