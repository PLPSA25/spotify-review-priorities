# Final submission — after deployment

This is a later phase, not authorized for execution by the step-1 app build.

1. Verify live URL with **Deployment Protection OFF**, incognito/signed-out.
2. Finish README: live URL; results; rubric-to-evidence map; architecture; one
   original review traced through labels, group, rank, claim and recommendation;
   one failed/ambiguous case; partial scope, accuracy and engineering limitations.
3. Refresh final grading exports including production verify/group/memo calls;
   recompress grading/*.gz once at maximum compression. Run all required checks,
   keep full required fields and disclose every legitimate remaining flag.
4. Compress the three local videos using the approved project-local pinned
   package approach if supported. Measure sizes/readability, then have the owner
   review every clip for sensitive content before any video commit or upload.
   Preserve the paste-error/reconstructed-checkpoint disclosure.
5. Run the **full secrets scan of final files and Git history** before any public
   push, including allowed binary archives/video handling. The local dashboard
   deployment/client-bundle scan is narrower and does not replace this scan.
6. Review exactly what will be published: approved source, lockfiles, small
   evidence/docs, final grading gzip exports, cost artifacts and owner-reviewed
   compressed videos/links. Exclude .env files, credentials, raw CSV/PDF, backups,
   private notes, local databases, caches, node_modules and build output.
7. Publish/push the public GitHub repository only after those checks and the final
   submission phase gate. No GitHub push is required for the local CLI deployment.

Later credentials: owner performs Vercel browser login personally; no token
request. Neon import secret goes only into ignored
`C:\dev\Spotify\.env.neon-import.local`, variable `NEON_IMPORT_DATABASE_URL`,
entered by the owner, never into chat. Vercel runtime uses only the restricted
`DATABASE_URL_READONLY` server-side variable.
