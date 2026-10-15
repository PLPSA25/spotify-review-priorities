import assert from "node:assert/strict";
import { test } from "node:test";
import { readFileSync } from "node:fs";
import { checkedSnapshot, selectMode } from "../lib/integrity.ts";
import { filteredRanking, parseScope } from "../lib/model.ts";

const value = JSON.parse(
  readFileSync(new URL("./snapshot.json", import.meta.url), "utf8"),
);
test("Python snapshot hash is valid in the server runtime", () => {
  const s = checkedSnapshot(value);
  assert.equal(s.payload.summary.counts.completed_rows, 237722);
  assert.equal(s.payload.meta.contains_full_records, false);
  assert.equal(s.payload.rankings.baseline[0].issue_id, "other--unspecified");
  assert.equal(s.payload.rankings.random_prefix[1].complaint_count, "4440");
  assert.equal(s.payload.rankings.baseline[1].complaint_count, "4444");
  assert.equal(s.payload.examples.length, 71);
});
test("Tampered data fails closed even when counts still reconcile", () => {
  const copy = structuredClone(value);
  copy.payload.examples[0].text = "Tampered";
  assert.throws(() => checkedSnapshot(copy), /hash mismatch/);
});
test("Local snapshot mode is explicit and forbidden on Vercel", () => {
  assert.equal(
    selectMode({
      DASHBOARD_DATA_MODE: "local",
      DASHBOARD_SNAPSHOT_PATH: "fixture",
    }),
    "local",
  );
  assert.throws(
    () =>
      selectMode({
        DASHBOARD_DATA_MODE: "local",
        DASHBOARD_SNAPSHOT_PATH: "fixture",
        VERCEL: "1",
      }),
    /forbidden/,
  );
  assert.throws(() => selectMode({}), /missing/);
  assert.throws(
    () =>
      selectMode({
        DATABASE_URL_READONLY: "postgresql://reader:dummy@example.invalid/db",
      }),
    /TLS/,
  );
});
test("Server-only connection requires the intended restricted role", () => {
  assert.throws(
    () =>
      selectMode({
        DATABASE_URL_READONLY:
          "postgresql://owner:dummy@example.invalid/db?sslmode=require",
      }),
    /role/,
  );
  assert.equal(
    selectMode({
      DATABASE_URL_READONLY:
        "postgresql://dashboard_reader:dummy@example.invalid/db?sslmode=require",
    }),
    "database",
  );
});
test("Filters are scoped and invalid scopes are rejected", () => {
  assert.equal(parseScope("baseline"), "baseline");
  assert.equal(parseScope("random_prefix"), "random_prefix");
  assert.equal(parseScope("random_prefix;DROP TABLE"), null);
  assert.equal(
    filteredRanking(value.payload.rankings.baseline, " ADS ").length,
    1,
  );
  assert.equal(
    filteredRanking(value.payload.rankings.baseline, "zzzzzz").length,
    0,
  );
  assert.equal(value.payload.rankings.baseline.length, 35);
});
test("Approved quote and claim derivations survive export", () => {
  const p = checkedSnapshot(value).payload;
  assert.match(p.artifacts.memo, /Owner-approved revision/);
  assert.ok(
    p.examples
      .find((r) => r.review_id.startsWith("7e271329"))
      ?.text.includes("to play in order buy premium"),
  );
  assert.equal(
    p.claims.secondary.find((c) => c.claim_id === "S11")?.value,
    "1949",
  );
  assert.equal(
    p.claims.secondary.find((c) => c.claim_id === "S12")?.value,
    "4",
  );
  assert.equal(
    p.claims.baseline.find((c) => c.claim_id === "B6")?.value,
    "3.122637",
  );
});
