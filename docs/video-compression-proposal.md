# Proposed local video compression — no encoding or commit authorized yet

No video contents have been opened, decoded or inspected. The following are planning targets derived from existing file sizes, not measured encoding results. The owner must review the compressed videos for sensitive content and readability before any commit.

Use a pinned PyPI package with a bundled ffmpeg executable installed only inside `.venv` (candidate: `imageio-ffmpeg==0.6.0`, subject to wheel/architecture compatibility checks). No global install, no direct-URL download or install script. This Windows Python is ARM64; confirm a usable bundled wheel/executable first. If unavailable, stop and propose a compatible PyPI-only alternative rather than silently downloading ffmpeg elsewhere. No package was installed for this proposal.

Proposed encoding: H.264 video, AAC audio if present, preserve aspect ratio, maximum 1280×720 initially, two-pass average bitrate based on metadata-only duration, target sizes below. Set total target bitrate from target_bytes × 8 / duration, reserve audio and mux overhead, then verify the actual result is below 50,000,000 bytes. Keep original recordings unchanged. If terminal text becomes unreadable, prefer original/unlisted delivery instead of sacrificing evidence quality.

- `Recording 2026-10-14 200325.mp4`: original **281,644,901 bytes**; proposed target **45,000,000 bytes** (45.00 MB), not a measured size.
- `Recording 2026-10-14 225019.mp4`: original **156,550,325 bytes**; proposed target **45,000,000 bytes** (45.00 MB), not a measured size.
- `Recording 2026-10-15 120822.mp4`: original **7,246,223 bytes**; proposed target **5,796,978 bytes** (5.80 MB), not a measured size.

Duration, bitrate and screen-text legibility have not been measured; the target-size calculation is not a promise of acceptable quality. Stage outputs under ignored runtime artifacts, never overwrite originals. Ask for owner review before changing `*.mp4` exclusions or committing videos. This work remains a proposal while the owner reviews cohort v2.
