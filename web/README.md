# Spotify review dashboard

Local step-1 build only. No Vercel or Neon login, provisioning or deployment yet.
This app reads a small versioned aggregate/sample snapshot, not all records.

From `C:\dev\Spotify`:

```powershell
.venv\Scripts\python.exe -m pipeline.dashboard_snapshot
Set-Location C:\dev\Spotify\web
npm.cmd ci --ignore-scripts
npm.cmd run build
npm.cmd test
npm.cmd run typecheck
npm.cmd run test:e2e
npm.cmd run scan
npm.cmd run preview:local
```

Local production preview: `http://127.0.0.1:3000`. It reads
`web/.local/dashboard.json` explicitly; that mode is forbidden on Vercel. The
default cloud mode requires `DATABASE_URL_READONLY` using the `dashboard_reader`
role over TLS. Missing data returns a sanitized unavailable response, with no
model calls or sample fallback. The browser sees only intended public report data.

## Later deployment session — not performed in step 1

- Use **Berkeley Granata (Hobby)**. The owner will run `vercel login` and complete
  browser login personally. Never request a Vercel token.
- Deploy only this `web/` directory via the local CLI; no GitHub push is needed
  for deployment. `.vercelignore` excludes tests/fixtures, local data, env files,
  import/scanning scripts and build output. Never deploy the whole repository.
- Before import, the owner creates exactly
  **`C:\dev\Spotify\.env.neon-import.local`**, pasting the private owner/import URL
  after **`NEON_IMPORT_DATABASE_URL=`**. The root `.env.*` rule ignores it. The
  app never reads that file or variable. Do not paste the URL in chat or print it.
- `npm.cmd run import:snapshot` is offline validation only. The future explicit
  `npm.cmd run import:snapshot -- --confirm-import` contacts the DB, creates the
  schema and transactionally publishes the immutable snapshot. It reads the
  ignored owner credential locally and reports only snapshot ID and DB size.
- SQL-created `dashboard_reader` initially has NOLOGIN. The owner will privately
  enable LOGIN/set a password during provisioning. Test the resulting role's
  SELECT access and denial of writes/CREATE; no owner URL goes into Vercel.
- Only `DATABASE_URL_READONLY` belongs in Vercel server-side settings. No
  `NEXT_PUBLIC_` DB variable, provider keys or import credentials. The DB uses one
  `dashboard.snapshots` JSONB table to store the versioned small read model,
  simplifying the earlier multi-table proposal without importing full records.
- **Deployment Protection OFF** for the final production URL; owner verifies
  access in incognito while signed out.

The database permission test, measured Postgres disk size and real DB connection
are intentionally deferred. Snapshot file size is not Postgres storage size.
The free plan's allowance must be confirmed in the actual Neon plan picker.

## Submission is a later phase

After deployment: full secrets scan of submitted files **and Git history**, then
the authorized public GitHub push. Complete the README with live URL,
rubric-to-evidence map, end-to-end trace, failed case and limitations. Refresh
grading gzip archives only once at final export; raw originals stay local. Produce
and review the compressed videos for sensitive content before committing them.
Do not treat the step-1 bundle scan as the full submission/history scan.
