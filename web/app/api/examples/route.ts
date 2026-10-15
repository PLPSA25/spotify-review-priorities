import { loadSnapshot } from "../../../lib/data";
export const dynamic = "force-dynamic";
export async function GET(request: Request) {
  const id = new URL(request.url).searchParams.get("id");
  if (!id || !/^[a-f0-9-]{36}$/.test(id))
    return Response.json({ error: "Invalid review ID" }, { status: 400 });
  try {
    const row = (await loadSnapshot()).payload.examples.find(
      (r) => r.review_id === id,
    );
    return row
      ? Response.json(row)
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
