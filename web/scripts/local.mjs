import { spawn } from "node:child_process";
import { resolve } from "node:path";
if (process.env.VERCEL) throw new Error("Local preview is not a cloud runtime");
const child = spawn(
  process.execPath,
  [
    "node_modules/next/dist/bin/next",
    "start",
    "--hostname",
    "127.0.0.1",
    "--port",
    process.env.PORT ?? "3000",
  ],
  {
    stdio: "inherit",
    env: {
      ...process.env,
      DASHBOARD_DATA_MODE: "local",
      DASHBOARD_SNAPSHOT_PATH: resolve(".local/dashboard.json"),
      NEXT_TELEMETRY_DISABLED: "1",
    },
  },
);
for (const sig of ["SIGINT", "SIGTERM"]) process.on(sig, () => child.kill(sig));
child.on("exit", (code) => process.exit(code ?? 1));
