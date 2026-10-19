# Final submission checklist

- [x] Live alias and signed-out incognito access: owner-verified 2026-10-19.
- [x] Phone access: owner-verified 2026-10-19. Standard Protection, access confirmed
  signed out; owner screenshots 2026-10-19. These are owner, not machine checks.
- [x] Current README: setup/check commands, rubric map, traced review, failed case,
  costs, limitations and disclosures; [README](../README.md), [STATUS](STATUS.md).
- [x] Final grading export includes Phase 7 calls, fixed gzip metadata and maximum
  compression; profile/reference/check flags disclosed. Ten final export files
  matched the independent replay; [evidence](phase8-deployment-evidence.md#final-export).
- [x] Three selected compressed recordings copied with original files preserved;
  links and frame-reviewed timestamp index in [README](../README.md#recordings-and-timestamp-index).
  Clip 1 is unedited. Preserve the unrecorded gap and reconstructed-checkpoint disclosure.
- [ ] Inspect Vercel production build log.
- [ ] Verify Neon/Vercel billing consoles and current plan settings.
- [ ] Complete the full secrets/personal-details scan of final files and Git history,
  including gzip contents and document/video review. Earlier bundle scans are narrower.
- [ ] Review the exact staged publication surface and all binary evidence.
- [ ] Owner approves a local commit; no commit is implied by staging.
- [ ] Final authorized public push after full secrets scan and publication review.

Exclude credentials, .env files, raw CSV/PDF, backups, private notes, local databases,
caches, node_modules and build output. Only the three explicitly approved clips
belong in evidence/recordings/. No owner/import credential belongs in Vercel;
DATABASE_URL_READONLY is the restricted server-side runtime variable.
