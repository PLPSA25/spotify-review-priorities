import "server-only";
import { readFile } from "node:fs/promises";
import { neon } from "@neondatabase/serverless";
import { checkedSnapshot, selectMode } from "./integrity";

export async function loadSnapshot() {
  if (selectMode(process.env) === "local") {
    return checkedSnapshot(
      JSON.parse(await readFile(process.env.DASHBOARD_SNAPSHOT_PATH!, "utf8")),
    );
  }
  const sql = neon(process.env.DATABASE_URL_READONLY!);
  const rows =
    await sql`SELECT payload FROM dashboard.snapshots WHERE published = true ORDER BY imported_at DESC, snapshot_id ASC LIMIT 1`;
  if (rows.length !== 1) throw new Error("Published data unavailable");
  return checkedSnapshot(rows[0].payload);
}
