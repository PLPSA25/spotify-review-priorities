// OFFLINE by default. Never invoked by the app, build or test commands.
import { readFile } from "node:fs/promises";
import { resolve } from "node:path";
import { checkedSnapshot } from "../lib/integrity.ts";
const root = resolve("..");
const snapshot = checkedSnapshot(
  JSON.parse(await readFile(resolve(".local/dashboard.json"), "utf8")),
);
if (!process.argv.includes("--confirm-import")) {
  console.log(
    JSON.stringify({
      mode: "offline validation only",
      snapshot_id: snapshot.snapshot_id,
      database_contacted: false,
    }),
  );
} else {
  try {
    const raw = await readFile(resolve(root, ".env.neon-import.local"), "utf8");
    const line = raw
      .split(/\r?\n/)
      .find((s) => s.startsWith("NEON_IMPORT_DATABASE_URL="));
    const connectionString = line
      ?.slice("NEON_IMPORT_DATABASE_URL=".length)
      .trim()
      .replace(/^(['"])(.*)\1$/, "$2");
    if (!connectionString) throw new Error("Missing local import credential");
    const url = new URL(connectionString);
    if (
      !["require", "verify-full"].includes(
        url.searchParams.get("sslmode") ?? "",
      )
    )
      throw new Error("Import connection must use TLS");
    const { Client } = await import("pg");
    const client = new Client({
      connectionString,
      connectionTimeoutMillis: 15000,
      statement_timeout: 30000,
    });
    try {
      await client.connect();
      await client.query("BEGIN");
      await client.query("SELECT pg_advisory_xact_lock(18273645)");
      await client.query(
        await readFile(resolve("deployment/schema.sql"), "utf8"),
      );
      await client.query(
        "UPDATE dashboard.snapshots SET published=false WHERE published=true",
      );
      await client.query(
        "INSERT INTO dashboard.snapshots(snapshot_id,payload,published) VALUES($1,$2::jsonb,true) ON CONFLICT(snapshot_id) DO UPDATE SET published=true",
        [snapshot.snapshot_id, JSON.stringify(snapshot)],
      );
      const result = await client.query(
        "SELECT payload,pg_database_size(current_database()) AS database_bytes FROM dashboard.snapshots WHERE snapshot_id=$1",
        [snapshot.snapshot_id],
      );
      checkedSnapshot(result.rows[0].payload);
      await client.query("COMMIT");
      console.log(
        JSON.stringify({
          imported: true,
          snapshot_id: snapshot.snapshot_id,
          database_bytes: result.rows[0].database_bytes,
        }),
      );
    } finally {
      await client.end();
    }
  } catch {
    // Do not include provider exceptions: they may contain credentials/DSNs.
    console.error(
      "Import failed safely. Check the local credential, TLS settings and database grants; no credentials are logged.",
    );
    process.exitCode = 1;
  }
}
