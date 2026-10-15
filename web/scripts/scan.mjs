// Limited step-1 scan: deployment inputs + built browser assets, not Git history.
import { readdir, readFile, stat, writeFile, mkdir } from "node:fs/promises";
import { resolve, relative, join } from "node:path";
const root = resolve("..");
const skipped = new Set([
  "node_modules",
  ".next",
  ".local",
  ".vercel",
  "tests",
  "test-results",
  "playwright-report",
  "scripts",
]);
const files = [];
async function walk(path, destination, filter = () => true) {
  for (const name of await readdir(path)) {
    const target = join(path, name),
      info = await stat(target);
    if (info.isDirectory()) {
      if (filter(name)) await walk(target, destination, filter);
    } else destination.push(target);
  }
}
async function deploymentFiles(path) {
  for (const name of await readdir(path)) {
    if (
      skipped.has(name) ||
      name.startsWith(".env") ||
      name.endsWith(".tsbuildinfo") ||
      ["playwright.config.ts", "README.md"].includes(name)
    )
      continue;
    const target = join(path, name),
      info = await stat(target);
    if (info.isDirectory()) await deploymentFiles(target);
    else files.push(target);
  }
}
const known = [];
// Existing local secrets are read only for equality scanning; never printed.
for (const filename of [
  ".env",
  ".env.neon-import.local",
  ".env.neon-reader.local",
  "web/.env.local",
]) {
  try {
    const raw = await readFile(resolve(root, filename), "utf8");
    for (const line of raw.split(/\r?\n/)) {
      const index = line.indexOf("=");
      if (index < 1 || line.trim().startsWith("#")) continue;
      const value = line
        .slice(index + 1)
        .trim()
        .replace(/^(['"])(.*)\1$/, "$2");
      if (value.length > 12) known.push(value);
    }
  } catch (error) {
    if (error.code !== "ENOENT")
      throw new Error("Cannot read a local secret file safely");
  }
}
const canary = "BUILD_CANARY_NOT_A_SECRET_8f91d0f5";
const markers = [
  "DATABASE_URL_READONLY",
  "NEON_IMPORT_DATABASE_URL",
  "OPENAI_API_KEY",
  "TYPESAFE_API_KEY",
  canary,
];
await deploymentFiles(process.cwd());
const client = [];
await walk(resolve(".next/static"), client);
const findings = [];
function inspect(file, body, browser) {
  for (const value of known) {
    const variants = [
      value,
      encodeURIComponent(value),
      Buffer.from(value).toString("base64"),
    ];
    if (variants.some((v) => body.includes(v)))
      findings.push({
        file: relative(root, file).replaceAll("\\", "/"),
        type: "local secret value match",
      });
  }
  if (/sk-(?:proj-)?[A-Za-z0-9_-]{24,}/.test(body))
    findings.push({
      file: relative(root, file).replaceAll("\\", "/"),
      type: "provider key pattern",
    });
  if (browser)
    for (const marker of markers)
      if (body.includes(marker))
        findings.push({
          file: relative(root, file).replaceAll("\\", "/"),
          type: "server-only marker in client bundle",
          marker,
        });
}
for (const file of files) inspect(file, await readFile(file, "utf8"), false);
for (const file of client) inspect(file, await readFile(file, "utf8"), true);
const forbidden = files.filter(
  (file) =>
    /\.(?:mp4|pdf|gz|sqlite3)$/.test(file) ||
    /(?:HANDOFF_NOTES|golden_50_human|spotify_reviews_18months)/.test(
      relative(process.cwd(), file),
    ),
);
for (const file of forbidden)
  findings.push({
    file: relative(root, file),
    type: "forbidden deployment artifact",
  });
const report = {
  scope:
    "Step 1 deployment source and browser bundle scan only; full files + Git-history scan remains final submission work",
  deployment_files: files.length,
  client_bundle_files: client.length,
  local_secret_values_compared: known.length,
  findings,
  source_scan_passed: findings.length === 0,
  full_git_history_scan_performed: false,
  canary:
    "Build uses a fake DB canary; neither its value nor server env variable names may enter client bundles",
};
await mkdir(resolve(root, "artifacts/dashboard"), { recursive: true });
await writeFile(
  resolve(root, "artifacts/dashboard/secret-scan.json"),
  JSON.stringify(report, null, 2) + "\n",
);
await writeFile(
  resolve(root, "docs/phase8-secret-scan.json"),
  JSON.stringify(report, null, 2) + "\n",
);
console.log(JSON.stringify(report));
if (findings.length) process.exitCode = 1;
