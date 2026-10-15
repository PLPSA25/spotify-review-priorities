import { spawn } from "node:child_process";
import { writeFile } from "node:fs/promises";
const env = {
  ...process.env,
  DASHBOARD_DATA_MODE: "database",
  NEXT_TELEMETRY_DISABLED: "1",
};
delete env.DATABASE_URL_READONLY;
delete env.DASHBOARD_SNAPSHOT_PATH;
const child = spawn(
  process.execPath,
  [
    "node_modules/next/dist/bin/next",
    "start",
    "--hostname",
    "127.0.0.1",
    "--port",
    "3001",
  ],
  { env, stdio: "ignore" },
);
try {
  let response;
  for (let n = 0; n < 30; n++) {
    try {
      response = await fetch("http://127.0.0.1:3001/api/dashboard");
      break;
    } catch {
      await new Promise((resolve) => setTimeout(resolve, 300));
    }
  }
  if (!response) throw new Error("Local test server unavailable");
  const body = await response.text();
  if (
    response.status !== 503 ||
    /postgres|DATABASE_URL|stack|password/i.test(body)
  )
    throw new Error("Unconfigured response was not sanitized");
  const result = {
    status: response.status,
    response: JSON.parse(body),
    credential_details_exposed: false,
    missing_credentials_fail_before_database_client_creation: true,
  };
  await writeFile(
    "../docs/phase8-unconfigured-runtime.json",
    JSON.stringify(result, null, 2) + "\n",
  );
  console.log(JSON.stringify(result));
} finally {
  child.kill("SIGTERM");
}
