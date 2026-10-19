# Spotify review dashboard

Live report: https://spotify-review-priorities.vercel.app — open signed out.
Owner verified incognito and phone access on 2026-10-19. Standard Protection is
configured; access was confirmed signed out (owner screenshots 2026-10-19).
Production deployment 2026-10-19 19:04-19:05 UTC: `next build --webpack` on Next.js 16.4.2, Compiled successfully in 6.5s, TypeScript finished, 3/3 static pages, routes /, /api/claims, /api/dashboard, /api/examples, status Ready; alias response headers X-Dashboard-Data-Source: neon and snapshot id 2d295662...0282e unchanged (owner-run `vercel inspect --logs` and curl, 2026-10-19). See [deployment evidence](../docs/phase8-deployment-evidence.md).

The backend reads the saved aggregate/sample snapshot from Neon, not the full
production row store. Human-evaluation figures are bundled separately. There are
no page-load model calls, and no fallback when the database is unavailable.
Only server-side `DATABASE_URL_READONLY` is used in Production (Sensitive);
no NEXT_PUBLIC database variable or owner credential belongs in deployment.
The footer and API headers expose the data source and snapshot ID.

## Local setup and verification

Use Node 24.x and the committed lockfile, from web/:
```powershell
npm.cmd ci
npm.cmd test
npm.cmd run typecheck
npm.cmd run build
npm.cmd run test:e2e
npm.cmd run preview:local
```
POSIX: replace npm.cmd with npm. Dependency installation requires network access.
Explicit local preview reads web/.local/dashboard.json (not in the repository);
that mode is prohibited on Vercel. Snapshot regeneration is an offline owner
operation: `python -B -m pipeline.dashboard_snapshot` from the repository root.

## Database setup and snapshot publication

1. Owner imports from web/ with `npm.cmd run import:snapshot -- --confirm-import`.
   Without --confirm-import the command validates offline only. The owner privately
   sets NEON_IMPORT_DATABASE_URL in the ignored root credential file; never print
   that value. The import creates dashboard.snapshots and publishes the immutable
   JSONB snapshot transactionally, checking its hash and readback.
2. In Neon SQL Editor, run [reader role SQL](db/01-reader-role.sql). It creates a
   restricted LOGIN role and checks dangerous flags/memberships fail closed. The
   owner sets its password privately; there is no password in the SQL. Do not use
   the earlier NOLOGIN instruction or broad managed-schema privilege sweep.
3. Owner supplies NEON_READER_DATABASE_URL in the ignored root reader credential
   file, then runs `npm.cmd run verify:reader` from web/. The helper requires
   dashboard_reader and TLS, sanitizes failures, and executes informational SQL
   separately from BEGIN/ROLLBACK transaction probes. All seven denial probes,
   dangerous-role flags, memberships and snapshot identity must pass.
4. Configure only DATABASE_URL_READONLY in Production as Sensitive. Use the reader
   credential, never the owner/import credential. The owner runs Vercel login,
   link and deploy personally with the CLI's default configuration location.
   Deploy web/ only; [.vercelignore](.vercelignore) limits its upload surface.
5. Re-save response headers and compare snapshot IDs after any payload change.
   Follow the [re-import rule](../docs/phase8-deployment-evidence.md).

Read-only default/timeout are secondary safeguards; grants are the boundary.
Database size measured during import: 8,257,536 bytes. Reader verification passed
7/7 denials, dangerous flags false, zero memberships; see the
[reader transcript](../docs/phase8-reader-verification.txt).

Vercel and Neon billing-console checks remain open (not verified by the owner; disclosed). The final text scan of tracked files and Git history was run 2026-10-19; only previously triaged benign matches remained (see [docs/final-submission-checklist.md](../docs/final-submission-checklist.md)).
