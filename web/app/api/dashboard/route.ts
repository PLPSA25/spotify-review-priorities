import { loadSnapshot, snapshotJson } from "../../../lib/data.ts";
import { parseScope } from "../../../lib/model.ts";
export const dynamic = "force-dynamic";
export async function GET(request: Request) {
  const scope = new URL(request.url).searchParams.get("scope");
  if (scope !== null && !parseScope(scope))
    return Response.json({ error: "Invalid ranking scope" }, { status: 400 });
  try {
    const snapshot = await loadSnapshot();
    return snapshotJson(snapshot, snapshot.meta);
  } catch {
    return Response.json(
      {
        error:
          "Dashboard data is unavailable. No live classification was attempted.",
      },
      { status: 503, headers: { "Cache-Control": "no-store" } },
    );
  }
}
