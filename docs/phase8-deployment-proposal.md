# Phase 8 proposal — Neon + Vercel

Status: proposal only. No accounts, cloud resources, database imports, dependency
installs, Git pushes or deployments have been performed for this phase.

## Result to build

One Next.js application in `web/`, with server-side route handlers on Vercel
reading a small, versioned Postgres dashboard dataset in Neon. This is a new UI;
the existing Python classifier and grading exports remain the source pipeline.
Deploying only `web/` avoids uploading the raw dataset, grading archives, local
state, recordings, human golden labels or private notes. No Git remote is currently
configured, so use a local Vercel CLI deployment; a GitHub push is not assumed.

The dashboard will show:

- A persistent partial-scope banner: 237,722 completed of 660,609 nonempty rows
  (35.985280%), with the declared out-of-scope quarantine and terminal failures
  clearly distinguished. Define denominators on screen.
- Overall topic/intent/severity/sentiment and needs_review metrics, with stored
  flag reasons (overlapping counts explained). Include an original-row versus
  distinct-text distinction rather than implying propagation is new model work.
- Both full issue rankings, switched or compared by scope: propagated baseline
  and seeded random-prefix-only. Show count, severity_sum, mean severity and
  priority definition; retain Other—unspecified first in each view.
- The owner-approved memo, with working compact links to baseline and secondary
  claims. Show the original model draft and owner-edit provenance separately.
- Saved AI outputs: group names, verifier agreement and selected bounded review
  examples with IDs. State agreement is not human accuracy and Luna also supplied
  fallback labels. Raw provider requests/responses are not a public dashboard API.

No live model calls, model SDK, model keys or chat box. Recommendations are read
from saved artifacts; page refreshes do not incur inference charges. Escape review
texts and model prose; render approved Markdown without executing HTML.

## Data and access design

Import a compact dashboard read model, not the entire 660k-row source table or
the 488 MB call log. Tables: `dashboard.runs`, `issue_metrics` (view/scope column),
`claims` (scope and allowed-vs-secondary marker), `summary_metrics`,
`review_examples`, and `saved_artifacts` (approved memo, original memo, group and
verifier summaries). Preserve source hashes, classifier/grouping hashes, dates,
approval status and original review IDs. Full records stay in grading/local
artifacts. This scope meets the requested dashboard without promising a full
corpus review-search service.

The export/import command will be offline and deterministic, with idempotent
transactional import keyed by artifact hash/run ID. Validate row totals, both
rankings, claims and memo hashes against saved files before activating a snapshot.
Compute aggregate metrics offline once, never by rescanning source rows per page.
Expected dashboard payload below 10 MB is an estimate; measure before import and
record actual Postgres size afterward.

Create `dashboard_reader` **via SQL**, without `neon_superuser`, ownership,
CREATE or write privileges. Grant only database CONNECT, dashboard schema USAGE
and SELECT on the specific published tables/views. Set a read-only transaction
default and statement timeout as additional limits, not substitutes for grants.
Test SELECT succeeds and INSERT/UPDATE/DELETE/CREATE fail on the published schema.
Use a separate owner/import credential locally for migrations and imports only.
Do not run migrations during Vercel builds or at request time.

Runtime uses only `DATABASE_URL_READONLY`, a TLS pooled connection for that SQL
role, in server-only code. No `NEXT_PUBLIC_` secret. The browser calls fixed GET
routes with validated scope/filter inputs and bounded pagination; it cannot submit
SQL. Do not return database error details, credentials or private artifacts.
Short server response caching is optional application caching, not provider prompt
caching. A saved snapshot can be cached with its run hash; Neon remains the source.

## Implementation sequence after approval

1. Build the deterministic dashboard exporter, schema/import scripts and a small
   fixture; pin project-local npm/PyPI dependencies and commit the lockfile.
2. Build the app and GET endpoints with loading, empty and unavailable states.
   Show provenance and the partial scope in the primary view, not a hidden footnote.
3. Test numbers against the saved rankings/claims, scope switching, claims links,
   memo rendering, input validation, missing credentials and the absence of model
   calls. Use the read-only role for an actual permission test after provisioning.
4. Link the Vercel project, provision the free Neon database and verify required
   environment variable names before running migrations/import or starting the
   connected dev server. Local fixture tests need no cloud connection.
5. Import one validated snapshot, deploy, then verify API → read-only DB → UI,
   including a signed-out browser. Record the live URL and source/import hashes.
6. Stop at the Phase 8 gate with the URL, screenshots, test results, measured DB
   size, role grants/denials and usage. Final grading gzip refresh and video
   publication remain later submission work.

Estimated implementation effort: 4–6 hours, plus account/login interaction. This
is a planning estimate, not measured runtime.

## What you will do in the consoles

Do these only after the deployment phase is approved and the app/scripts exist.
Labels below follow current official documentation and may vary slightly by account.

1. **Vercel:** sign in and choose your personal Hobby scope. We will prepare the
   pinned project-local CLI and link `web/` to a new `spotify-review-priorities`
   project, or inspect/reuse an explicitly suitable existing project. With no Git
   remote, a local CLI deployment avoids requiring a repository push. The project
   will then appear in the Vercel console. Do not import the whole project root.
2. **Vercel → project → Storage:** choose Create Database / Marketplace → Neon,
   then Install. Choose the free plan shown by the console, a database name, and
   a region matching the application's Functions region. Do not select Pro trials,
   paid storage or an automatic paid upgrade. If no free plan is offered, stop
   and report that screen before provisioning a paid resource.
3. **Vercel Storage → database → Connect Project:** select this project and the
   intended Development/Preview/Production environments. For this read-only
   demonstration, use one stable published snapshot; automatic preview database
   branching is unnecessary initially. Keep the native integration's credential
   injection in mind: its default owner URL is **not** our runtime credential.
4. **Vercel Storage → Open in Neon:** confirm the project/database/branch, free
   plan and region. Use SQL Editor as the owner to run the supplied schema and
   least-privilege role SQL. We will provide a local credential bootstrap/import
   helper so passwords need not be pasted into chat or printed in logs. Do not
   create the supposedly read-only role using Neon’s Roles UI: roles created by
   console/API/CLI receive elevated `neon_superuser` membership; use SQL instead.
5. **Neon → Connect:** select the published branch/database and SQL-created
   `dashboard_reader` role; enable pooling and TLS. Copy that connection string
   directly into Vercel's secret input, not into a message or tracked file.
   The separate owner/import URL stays in an ignored local deployment env file.
   Run the prepared one-time import locally with owner permissions; confirm its
   aggregate reconciliation and hash report, then perform the read-only-role test.
6. **Vercel → Settings → Environment Variables:** add `DATABASE_URL_READONLY`
   for the intended environments. Remove owner/import connection variables
   automatically injected by the integration from runtime environments (or detach
   credential injection while retaining the database). The deployment must not
   inherit team-level owner URLs. Never add OpenAI, TypeSafe or other model keys.
7. **Vercel → Settings → Build and Deployment / Functions:** confirm Next.js,
   the `web/` deployment root and the matching region. Use the scripts we provide;
   the build must not import data, migrate the database or invoke any model.
   Deploy the prepared local app via the linked CLI. After changing env variables,
   create a new deployment/redeploy; old deployments do not receive changed values.
8. **Vercel → Deployments:** open the Ready deployment; verify both rankings,
   coverage banner, claims links, saved memo and AI outputs. Check Runtime Logs
   for sanitized errors, and Neon Monitoring/Usage for connection/size figures.
9. **Vercel → Settings → Deployment Protection:** ensure the final submitted
   production URL is accessible to the instructor without your account, as already
   required by the approved project plan. Confirm in a signed-out/incognito window.
   Keep secrets server-side; the public page contains only the intended report data.
10. **Vercel and Neon usage/billing:** confirm free plans and record actual usage.
    Keep scale-to-zero enabled. Save the live URL in README; no custom paid domain
    is needed. Do not enable a keep-awake job just to avoid cold starts.

## Cost proposal and stopping conditions

New inference cost: **$0**. Target hosting/database charge: **$0** on Vercel Hobby
and Neon Free for this personal course demonstration. No paid plan is authorized.
The current official Neon page lists a Free allowance of 1 GB storage and 100
CU-hours per project/month; the Vercel-managed offer must be confirmed in its
actual plan picker. A small aggregate-only dataset is expected to fit, but that
has not been measured. Hobby is restricted to personal/noncommercial use and can
pause features on quota exhaustion. This is a quota-limited deployment, not a
promise of unlimited free availability. No paid upgrades or overage-based plan.

Project model spend stays **$5.629964013 / $10**. Hosting is a separate cost category;
it is not charged through the model ledger. If free provisioning is unavailable
or measured size/usage exceeds the selected free allowance, stop and report it
rather than silently spending. No service has been provisioned at this gate.

## Official references checked 2026-10-15

- [Next.js on Vercel](https://vercel.com/docs/frameworks/full-stack/nextjs)
- [Local CLI deployment](https://vercel.com/docs/projects/deploy-from-cli)
- [Neon native integration and console flow](https://neon.com/docs/guides/vercel-managed-integration)
- [SQL-created least-privilege roles](https://neon.com/docs/manage/database-access)
- [Neon connection pooling](https://neon.com/docs/connect/connection-pooling)
- [Vercel environment variables and redeployment](https://vercel.com/docs/environment-variables/managing-environment-variables)
- [Neon pricing](https://neon.com/pricing)
- [Vercel Hobby scope, quotas and free-plan behavior](https://vercel.com/docs/plans/hobby)
