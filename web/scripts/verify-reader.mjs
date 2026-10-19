// Explicit operator command only. Never invoked by app/build/tests.
import { readFile } from "node:fs/promises";
import { fileURLToPath } from "node:url";
import { resolve } from "node:path";

const web = fileURLToPath(new URL("..", import.meta.url));
let step = "read credential";
let client;
let failed = false;
const passed = new Set();
function fail(err) {
  failed = true;
  process.exitCode = 1;
  const code = typeof err?.code === "string" && /^(?:E[A-Z0-9_]{2,31}|[0-9A-Z]{5})$/.test(err.code) ? ` ${err.code}` : "";
  console.error(`FAIL: ${step}${code}`);
}

// Only fixed, locally defined probe labels may reach the notice output.
const probes = [
  ["INSERT INTO dashboard.snapshots", "INSERT dashboard.snapshots"],
  ["UPDATE dashboard.snapshots", "UPDATE dashboard.snapshots"],
  ["DELETE FROM dashboard.snapshots", "DELETE dashboard.snapshots"],
  ["CREATE TABLE dashboard.", "CREATE TABLE dashboard"],
  ["CREATE TABLE public.", "CREATE TABLE public"],
  ["CREATE SCHEMA ", "CREATE SCHEMA"],
  ["CREATE TEMP TABLE ", "CREATE TEMP TABLE"],
];

try {
  const raw = await readFile(resolve(web, "../.env.neon-reader.local"), "utf8");
  const line = raw.split(/\r?\n/).find((s) => s.startsWith("NEON_READER_DATABASE_URL="));
  const connectionString = line?.slice("NEON_READER_DATABASE_URL=".length).trim().replace(/^(['"])(.*)\1$/, "$2");
  if (!connectionString) throw new Error();
  step = "TLS check";
  const url = new URL(connectionString);
  if (
    !["postgres:", "postgresql:"].includes(url.protocol) ||
    !["require", "verify-full"].includes(url.searchParams.get("sslmode") ?? "") ||
    decodeURIComponent(url.username) !== "dashboard_reader"
  ) throw new Error();

  const { Client } = await import("pg");
  client = new Client({ connectionString, connectionTimeoutMillis: 15000, statement_timeout: 30000 });
  client.on("error", fail);
  client.on("notice", (notice) => {
    const prefix = "PASS: denied (42501): ";
    const probe = typeof notice.message === "string" && notice.message.startsWith(prefix)
      ? probes.find(([sql]) => notice.message.slice(prefix.length).startsWith(sql))
      : undefined;
    if (probe) {
      passed.add(probe[1]);
      console.log(`PASS: denied (42501): ${probe[1]}`);
    } else if (/^FAIL/i.test(notice.message ?? "")) {
      fail();
    } else {
      console.log("NOTICE: detail withheld");
    }
  });
  step = "connect";
  await client.connect();
  step = "verification";
  const sql = await readFile(resolve(web, "db/02-verify-reader.sql"), "utf8");
  // One simple-query script, including its own BEGIN and final ROLLBACK.
  const response = await client.query(sql);
  const results = Array.isArray(response) ? response : [response];
  const fields = new Set([
    "current_user", "session_user", "rolname", "rolcanlogin", "rolsuper",
    "rolcreaterole", "rolcreatedb", "rolbypassrls", "rolreplication", "rolinherit",
    "direct_or_transitive_membership", "direct_membership_count", "neon_superuser_member",
    "default_transaction_read_only", "statement_timeout", "snapshot_id", "imported_at",
  ]);
  function safeValue(key, value) {
    if (typeof value === "boolean" || typeof value === "number" || value === null) return value;
    if (key === "imported_at" && value instanceof Date) return value.toISOString();
    if (typeof value !== "string") throw new Error();
    if (key === "snapshot_id" && /^[a-f0-9]{64}$/.test(value)) return value;
    if (key === "imported_at" && /^\d{4}-\d\d-\d\d[T ][\d:.+Z-]+$/.test(value)) return value;
    if (key !== "snapshot_id" && key !== "imported_at" && /^[A-Za-z0-9_$-]{1,63}$/.test(value)) return value;
    throw new Error();
  }
  for (const [index, result] of results.entries()) {
    if (!result.fields?.length) continue;
    if (result.fields.some((field) => !fields.has(field.name))) throw new Error();
    const rows = result.rows.map((row) => Object.fromEntries(
      Object.entries(row).map(([key, value]) => [key, safeValue(key, value)]),
    ));
    console.log(JSON.stringify({ result_set: index + 1, columns: result.fields.map((field) => field.name), rows }));
  }
  if (passed.size !== probes.length) throw new Error();
  if (!failed) console.log("PASS: reader verification complete (7/7 denial probes)");
} catch (err) {
  fail(err);
} finally {
  if (client) {
    try { await client.end(); } catch (err) { fail(err); }
  }
}
