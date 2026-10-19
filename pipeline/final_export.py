r"""Build an offline final grading-export candidate from saved production evidence.

Purpose: export frozen classification records, append saved Phase 7 calls, copy
approved membership/ranking/claims, and package reproducible gzip level 9 files.
Inputs: grading/ (read only), artifacts/scope-100k/state.sqlite3 and checkpoints,
data/spotify_reviews_18months.csv and course helpers/manifest,
artifacts/phase7/{membership.csv,calls.jsonl}, and docs/phase7/{ranking.csv,claims.csv}.
Outputs: artifacts/export-dryrun/raw/, submission/, grading-before.json, and
build-result.json. Creates no ingestion.json; run the course profile separately.
Offline: blocks socket connections, makes zero API/paid calls, never reads .env
files, and verifies grading/ bytes remain unchanged. Refuses existing raw/ or
submission/ outputs. Create artifacts/export-dryrun/ beforehand if absent.
Exact command from C:/dev/Spotify:
    .\.venv\Scripts\python.exe -B -m pipeline.final_export
This preserves the dry-run adapter behavior; it does not promote or commit files.
"""
import gzip
import hashlib
import json
from pathlib import Path
import shutil
import socket
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "artifacts/export-dryrun"
if Path.cwd().resolve() != ROOT:
    raise SystemExit('Run from the repository root')
sys.path.insert(0, str(ROOT))

def no_network(*args, **kwargs):
    raise RuntimeError('Network disabled for offline export')

socket.socket.connect = no_network
socket.socket.connect_ex = no_network
socket.create_connection = no_network
from pipeline.scope_export import export
from pipeline.schema import canonical

def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()

def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False)+'\n', encoding='utf-8', newline='\n')

started = time.monotonic()
before = {p.name: sha(p) for p in Path('grading').iterdir() if p.is_file()}
raw, dest = BASE/'raw', BASE/'submission'
if raw.exists() or dest.exists():
    raise SystemExit('Refusing to overwrite an existing dry run')
raw.mkdir()
dest.mkdir()
write_json(BASE/'grading-before.json', before)
export(destination=raw)
print('Fresh offline base export complete', flush=True)

# Saved owner-approved Phase 7 numerical evidence; never rerun paid stages.
for source, name in [
    ('artifacts/phase7/membership.csv', 'membership.csv'),
    ('docs/phase7/ranking.csv', 'ranking.csv'),
    ('docs/phase7/claims.csv', 'claims.csv'),
]:
    shutil.copyfile(source, dest/name)
for name in ('checkpoint_before.json', 'checkpoint_after.json',
             'checkpoint_before.provenance.json', 'coverage.json'):
    shutil.copyfile(raw/name, dest/name)
run = json.loads((raw/'run.json').read_text(encoding='utf-8'))
run['business_stages'] = 'completed: production verify/group/rank/claims/memo; owner-approved memo'
write_json(dest/'run.json', run)
with (raw/'calls.jsonl').open('a', encoding='utf-8', newline='\n') as out:
    for line in Path('artifacts/phase7/calls.jsonl').read_text(encoding='utf-8').splitlines():
        out.write(canonical(json.loads(line))+'\n')

for name in ('records', 'calls'):
    path = dest/(name+'.jsonl.gz')
    with (raw/(name+'.jsonl')).open('rb') as src, path.open('wb') as target:
        with gzip.GzipFile(filename='', mode='wb', fileobj=target, compresslevel=9, mtime=0) as gz:
            shutil.copyfileobj(src, gz, 1024*1024)
    # Repeat to a digest sink: same inputs/runtime must produce identical bytes.
    class DigestSink:
        def __init__(self): self.digest = hashlib.sha256()
        def write(self, b): self.digest.update(b); return len(b)
        def flush(self): pass
    sink = DigestSink()
    with (raw/(name+'.jsonl')).open('rb') as src:
        with gzip.GzipFile(filename='', mode='wb', fileobj=sink, compresslevel=9, mtime=0) as gz:
            shutil.copyfileobj(src, gz, 1024*1024)
    if sink.digest.hexdigest() != sha(path):
        raise RuntimeError('Nonidentical repeat gzip')
    print(name+' compressed; repeat bytes identical', flush=True)

after = {p.name: sha(p) for p in Path('grading').iterdir() if p.is_file()}
if before != after:
    raise RuntimeError('Tracked grading inputs changed')
write_json(BASE/'build-result.json', {
    'elapsed_seconds': round(time.monotonic()-started, 3),
    'grading_unchanged': before == after,
    'repeat_gzip_identical': True,
    'gzip_mtime': 0, 'gzip_filename': '', 'compresslevel': 9,
    'new_api_calls': 0, 'cost_usd': 0,
})
print('Candidate complete; grading unchanged', flush=True)
