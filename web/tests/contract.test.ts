import assert from "node:assert/strict";
import { test } from "node:test";
import { readFileSync } from "node:fs";
import { spawnSync } from "node:child_process";
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

// A separate Node process selects server-only's server condition. All successful
// DB reads below use an injected in-memory query; no network or credentials.
function serverTest(code: string, setup = "") {
  const result = spawnSync(process.execPath, [
    "--conditions=react-server", "--experimental-test-module-mocks", "--experimental-strip-types", "--input-type=module", "-e",
    `import assert from 'node:assert/strict';
     import {readFileSync} from 'node:fs';
     const fixture=JSON.parse(readFileSync('./tests/snapshot.json','utf8'));
     const db={DATABASE_URL_READONLY:'postgresql://dashboard_reader@example.invalid/db?sslmode=require'};
     ${setup}
     const {loadSnapshot, snapshotJson, sourceHeaders}=await import('./lib/data.ts');
     ${code}`,
  ], { cwd: new URL("..", import.meta.url), encoding: "utf8", env: { ...process.env, DATABASE_URL_READONLY: "", DASHBOARD_DATA_MODE: "", DASHBOARD_SNAPSHOT_PATH: "" } });
  assert.equal(result.status, 0, result.stderr || result.stdout);
}

test("Database success reports Neon headers and matching JSON meta after validation", () => {
  serverTest(`
    const s=await loadSnapshot(db, async()=>[{payload:fixture,imported_at:'2026-10-19T12:00:00Z'}]);
    for(const body of [s,s.payload.examples[0]]) {
      const r=snapshotJson(body,s.meta); const json=await r.json();
      assert.equal(r.headers.get('X-Dashboard-Data-Source'),'neon');
      assert.equal(r.headers.get('X-Dashboard-Snapshot-Id'),fixture.snapshot_id);
      assert.deepEqual(json.meta,{source:'neon',snapshot_id:fixture.snapshot_id,imported_at:'2026-10-19T12:00:00.000Z'});
    }
    assert.equal(sourceHeaders(s.meta)['X-Dashboard-Data-Source'],'neon');
    Object.assign(process.env,db);
    for(const [path,url] of [
      ['./app/api/dashboard/route.ts','http://localhost/api/dashboard'],
      ['./app/api/examples/route.ts','http://localhost/api/examples?id=7e271329-4c82-403b-a59a-7fd8b6c40405'],
      ['./app/api/claims/route.ts','http://localhost/api/claims']
    ]) {
      const {GET}=await import(path); const r=await GET(new Request(url));
      assert.equal(r.status,200);
      assert.equal(r.headers.get('X-Dashboard-Data-Source'),'neon');
      assert.equal(r.headers.get('X-Dashboard-Snapshot-Id'),fixture.snapshot_id);
      if(!path.includes('claims')) assert.deepEqual((await r.json()).meta,s.meta);
    }
    await assert.rejects(loadSnapshot(db,async()=>[{payload:{...fixture,snapshot_id:'0'.repeat(64)},imported_at:'2026-10-19'}]));
  `, `
    const {mock}=await import('node:test');
    mock.module('@neondatabase/serverless',{namedExports:{neon:()=>async()=>[{payload:fixture,imported_at:'2026-10-19T12:00:00Z'}]}});
  `);
});

test("Explicit local success reports local-file headers and meta, never Neon", () => {
  serverTest(`
    let queried=false;
    const s=await loadSnapshot({DASHBOARD_DATA_MODE:'local',DASHBOARD_SNAPSHOT_PATH:'fixture'},async()=>{queried=true;throw Error('must not query')},async()=>JSON.stringify(fixture));
    assert.equal(queried,false);
    const r=snapshotJson(s,s.meta); const json=await r.json();
    assert.equal(r.headers.get('X-Dashboard-Data-Source'),'local-file');
    assert.equal(r.headers.get('X-Dashboard-Snapshot-Id'),fixture.snapshot_id);
    assert.deepEqual(json.meta,{source:'local-file',snapshot_id:fixture.snapshot_id,imported_at:null});
    process.env.DASHBOARD_DATA_MODE='local';
    process.env.DASHBOARD_SNAPSHOT_PATH='./tests/snapshot.json';
    delete process.env.VERCEL;
    for(const [path,url] of [
      ['./app/api/dashboard/route.ts','http://localhost/api/dashboard'],
      ['./app/api/examples/route.ts','http://localhost/api/examples?id=7e271329-4c82-403b-a59a-7fd8b6c40405'],
      ['./app/api/claims/route.ts','http://localhost/api/claims']
    ]) {
      const {GET}=await import(path); const response=await GET(new Request(url));
      assert.equal(response.status,200);
      assert.equal(response.headers.get('X-Dashboard-Data-Source'),'local-file');
      assert.equal(response.headers.get('X-Dashboard-Snapshot-Id'),fixture.snapshot_id);
      if(!path.includes('claims')) assert.deepEqual((await response.json()).meta,s.meta);
    }
    await assert.rejects(loadSnapshot({DASHBOARD_DATA_MODE:'local',DASHBOARD_SNAPSHOT_PATH:'fixture',VERCEL:'1'},async()=>[],async()=>JSON.stringify(fixture)),/forbidden/);
  `);
});

test("Missing connection and query failures never fall back or claim a source", () => {
  serverTest(`
    let read=false;
    await assert.rejects(loadSnapshot({},async()=>[],async()=>{read=true;return JSON.stringify(fixture)}),/missing/);
    await assert.rejects(loadSnapshot(db,async()=>{throw Error('query failed')},async()=>{read=true;return JSON.stringify(fixture)}),/query failed/);
    assert.equal(read,false);
    const routes=[
      ['./app/api/dashboard/route.ts','http://localhost/api/dashboard'],
      ['./app/api/examples/route.ts','http://localhost/api/examples?id=7e271329-4c82-403b-a59a-7fd8b6c40405'],
      ['./app/api/claims/route.ts','http://localhost/api/claims']
    ];
    for(const env of [{DATABASE_URL_READONLY:''},db]) {
      Object.assign(process.env,env);
      for(const [path,url] of routes) {
      const {GET}=await import(path); const r=await GET(new Request(url));
      assert.equal(r.status,503);
      assert.equal(r.headers.get('X-Dashboard-Data-Source'),null);
      assert.equal(r.headers.get('X-Dashboard-Snapshot-Id'),null);
      const json=await r.json(); assert.deepEqual(Object.keys(json),['error']);
      assert.doesNotMatch(json.error,/postgresql|example.invalid|query failed/);
      }
    }
  `, `
    const {mock}=await import('node:test');
    mock.module('@neondatabase/serverless',{namedExports:{neon:()=>async()=>{throw Error('query failed')}}});
  `);
});
