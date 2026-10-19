import { loadSnapshot, snapshotJson } from "../../../lib/data.ts";
export const dynamic = "force-dynamic";
export async function GET(request: Request) {
  const id = new URL(request.url).searchParams.get("id");
  if (!id || !/^[a-f0-9-]{36}$/.test(id))
    return Response.json({ error: "Invalid review ID" }, { status: 400 });
  try {
    const snapshot = await loadSnapshot();
    const row = snapshot.payload.examples.find(
      (r) => r.review_id === id,
    );
    return row
      ? snapshotJson(row, snapshot.meta)
      : Response.json(
          { error: "Review is outside the bounded public examples" },
          { status: 404 },
        );
  } catch {
    return Response.json(
      { error: "Saved examples unavailable" },
      { status: 503 },
    );
  }
}
