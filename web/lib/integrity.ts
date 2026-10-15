import { createHash } from "node:crypto";
import { validateSnapshot, type Snapshot } from "./model.ts";

export function canonical(value: unknown): string {
  if (Array.isArray(value)) return "[" + value.map(canonical).join(",") + "]";
  if (value !== null && typeof value === "object")
    return (
      "{" +
      Object.keys(value)
        .sort()
        .map(
          (key) =>
            JSON.stringify(key) +
            ":" +
            canonical((value as Record<string, unknown>)[key]),
        )
        .join(",") +
      "}"
    );
  return JSON.stringify(value);
}
export function checkedSnapshot(value: unknown): Snapshot {
  validateSnapshot(value);
  if (
    createHash("sha256").update(canonical(value.payload)).digest("hex") !==
    value.snapshot_id
  )
    throw new Error("Snapshot hash mismatch");
  return value;
}
export function selectMode(env: Record<string, string | undefined>) {
  if (env.DASHBOARD_DATA_MODE === "local") {
    if (env.VERCEL || !env.DASHBOARD_SNAPSHOT_PATH)
      throw new Error("Local data mode is forbidden on Vercel");
    return "local";
  }
  if (env.DASHBOARD_DATA_MODE && env.DASHBOARD_DATA_MODE !== "database")
    throw new Error("Unknown data mode");
  if (!env.DATABASE_URL_READONLY)
    throw new Error("Read-only data connection missing");
  const url = new URL(env.DATABASE_URL_READONLY);
  if (
    !["postgres:", "postgresql:"].includes(url.protocol) ||
    !["require", "verify-full"].includes(url.searchParams.get("sslmode") ?? "")
  )
    throw new Error("Read-only connection requires TLS");
  if (decodeURIComponent(url.username) !== "dashboard_reader")
    throw new Error("Unexpected runtime database role");
  return "database";
}
