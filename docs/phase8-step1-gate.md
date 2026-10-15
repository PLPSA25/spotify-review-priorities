# Phase 8, step 1 — local app and dashboard snapshot

Completed locally; stop before cloud steps. No Vercel login, account changes,
Neon provisioning/connection/import, deployment, GitHub push or model calls.

## Measured snapshot

- Import file: `artifacts/dashboard/snapshot.json` (ignored local output).
- **72,076 bytes** (about 70.4 KiB); **35 issues in each ranking**, **71 bounded
  selected review examples**, aggregate metrics, baseline/secondary claims, saved
  verifier/group outputs, original memo and owner-approved memo.
- Full records, raw CSV, call logs and human golden labels are **not included**.
- Deterministic regeneration produced identical bytes. File SHA-256:
  `70bed5f69d9f3515bc252bd5cf50fc541658b4ed9adfd62ef1365904e23b419b`.
- Payload identity:
  `2d29566238c93179d4518f4eb08cc5c0e45e0f125fe1a9d103a0ce0ff6b0282e`.
- Source identity, counts and per-file hashes:
  [snapshot manifest](phase8-snapshot-manifest.json).
- Current documented Neon Free storage allowance is **1 GB per project**; confirm
  the actual Vercel-managed plan picker later. Payload size is below that limit,
  but it is **not a measurement of Postgres tables/indexes/disk usage**. Measure
  `pg_database_size` after import; no database exists for this app yet.

## App and validation

Next.js 16.4.2, React 19.3.1, TypeScript 7.0.2, Neon serverless driver 1.2.0,
Node 24.19.0; project-local pinned packages and npm lockfile. No model SDK.

- Optimized production build passed; three dynamic GET endpoints plus the page.
- TypeScript check passed; **6 Node contract tests passed**.
- **4 browser tests passed** using installed Microsoft Edge: real page → API →
  saved snapshot → UI; both ranking views and search; claims downloads and quote
  lookup; invalid scopes and write-method rejection; mobile viewport/keyboard;
  unavailable-data UI; malicious review/Markdown HTML remains inert. Happy-path
  browser requests to external hosts were blocked; none were attempted.
- **223 Python tests passed**, including aggregate coverage/alias/reason checks;
  Ruff checks passed.
- Python-generated payload hashes validate in the Node runtime. The owner-approved
  memo's exact hash is checked on export. Source classifier and final grouping
  hashes, grading gzip files, config and prompts remain unchanged.
- `npm audit --omit=dev --json` reported **0 production vulnerabilities** at this
  build. This is the registry result, not a guarantee of absence of vulnerabilities.
- Import command was run in its default **offline validation-only** mode; it
  reported `database_contacted: false`. No real database permission test or
  Postgres size measurement has been performed. Those remain later steps.
- In default database mode, a missing credential must produce a sanitized 503,
  never a silent local/sample fallback. Local snapshot mode is explicitly blocked
  when `VERCEL` is set. Runtime requires the `dashboard_reader` username and TLS;
  actual SQL role privileges must still be verified against Neon later.
  A separate unconfigured runtime check actually returned **503** with no
  credential details; [saved response](phase8-unconfigured-runtime.json).

Desktop/mobile screenshots are local ignored outputs under `web/test-results/`.
The app displays partial scope, both rankings, distributions, overlapping flag
reasons, stored verifier agreement, approved memo, source examples and provenance.
It uses one versioned JSONB snapshot table rather than six small tables, retaining
the proposed read-model content with a simpler atomic import.

## Secret/deployment scan

[Actual scan output](phase8-secret-scan.json): **19 deployment source/input files
and 25 browser assets** scanned; **0 findings**. Compared existing local secret
values without printing or storing them. A fake DB URL canary was present during
the build; its value and server-only credential variable names were absent from
client assets. Browser assets total 1,062,315 uncompressed bytes.

Deploy only `web/`. Its deployment ignore excludes local/env files, test fixtures,
import scripts, dependencies and build/test output; raw project artifacts are
outside that directory. Credential code is server-only, model Markdown skips raw
HTML, and review text is escaped. The API sanitizes failures and exposes only
intended public report data. No owner/import credential is a runtime setting.

This is the limited step-1 scan. The **full submitted-files and Git-history scan
before the final public GitHub push remains required**.

## Later session handoff

- Use **Berkeley Granata (Hobby)**. The owner runs `vercel login` and completes
  browser login; never ask for a token.
- Owner creates exactly **`C:\dev\Spotify\.env.neon-import.local`** and privately
  pastes the Neon owner/import URL into **`NEON_IMPORT_DATABASE_URL=`**. The file
  is verified ignored by `.env.*`; it has not been created by this build. The
  template is `web/deployment/import-env.example`. Never paste the URL in chat.
- Import credentials stay local. Only `DATABASE_URL_READONLY` goes into Vercel's
  server-side runtime environment; no `NEXT_PUBLIC_` secret. Remove injected
  owner/import URLs from Vercel before deployment.
- **Deployment Protection OFF**, then verify the final URL in incognito while
  signed out. This has not been attempted locally or claimed complete.
- After deployment: full secrets scan of files + history, public GitHub push,
  final README (live URL, rubric map, end-to-end trace, failed case, limitations),
  final grading export and owner-reviewed compressed videos. See
  [the final checklist](final-submission-checklist.md).

Local preview command from `C:\dev\Spotify\web`: `npm.cmd run preview:local`.
It serves only `http://127.0.0.1:3000`; Ctrl+C stops it. No live model calls.
