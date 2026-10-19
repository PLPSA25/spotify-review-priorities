import "server-only";
import { readFile } from "node:fs/promises";
import { neon } from "@neondatabase/serverless";
import { checkedSnapshot, selectMode } from "./integrity.ts";

type Environment = Record<string, string | undefined>;
type Row = { payload: unknown; imported_at: string | Date };
export type SourceMeta = {
  source: "neon" | "local-file";
  snapshot_id: string;
  imported_at: string | null;
};
const queryPublished = async (env: Environment): Promise<Row[]> => {
  const sql = neon(env.DATABASE_URL_READONLY!);
  return await sql`SELECT payload, imported_at FROM dashboard.snapshots WHERE published = true ORDER BY imported_at DESC, snapshot_id ASC LIMIT 1` as Row[];
};
export async function loadSnapshot(
  env: Environment = process.env,
  query: (env: Environment) => Promise<Row[]> = queryPublished,
  read: (path: string) => Promise<string> = (path) => readFile(path, "utf8"),
) {
  const mode = selectMode(env);
  if (mode === "local") {
    const snapshot = checkedSnapshot(JSON.parse(await read(env.DASHBOARD_SNAPSHOT_PATH!)));
    return { ...snapshot, meta: { source: "local-file" as const, snapshot_id: snapshot.snapshot_id, imported_at: null } };
  }
  const rows = await query(env);
  if (rows.length !== 1) throw new Error("Published data unavailable");
  const snapshot = checkedSnapshot(rows[0].payload);
  const imported_at = new Date(rows[0].imported_at).toISOString();
  return { ...snapshot, meta: { source: "neon" as const, snapshot_id: snapshot.snapshot_id, imported_at } };
}

export function sourceHeaders(meta: SourceMeta) {
  return {
    "Cache-Control": "no-store",
    "X-Dashboard-Data-Source": meta.source,
    "X-Dashboard-Snapshot-Id": meta.snapshot_id,
  };
}
export function snapshotJson(body: object, meta: SourceMeta) {
  return Response.json({ ...body, meta }, { headers: sourceHeaders(meta) });
}
