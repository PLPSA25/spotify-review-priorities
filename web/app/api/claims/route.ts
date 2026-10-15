import { loadSnapshot } from "../../../lib/data";
export const dynamic = "force-dynamic";
export async function GET(request: Request) {
  const scope = new URL(request.url).searchParams.get("scope") ?? "baseline";
  if (!["baseline", "secondary"].includes(scope))
    return Response.json({ error: "Invalid claims scope" }, { status: 400 });
  try {
    const rows = (await loadSnapshot()).payload.claims[
      scope as "baseline" | "secondary"
    ];
    const fields = [
      "claim_id",
      "issue_id",
      "metric",
      "value",
      ...(scope === "secondary" ? ["scope", "source"] : []),
    ];
    const quote = (v: string) => '"' + v.replaceAll('"', '""') + '"';
    const body = [
      fields.join(","),
      ...rows.map((row) =>
        fields
          .map((key) =>
            quote(
              String((row as unknown as Record<string, string>)[key] ?? ""),
            ),
          )
          .join(","),
      ),
    ].join("\r\n");
    return new Response(body, {
      headers: {
        "Content-Type": "text/csv; charset=utf-8",
        "Content-Disposition": `attachment; filename="${scope}-claims.csv"`,
        "Cache-Control": "no-store",
      },
    });
  } catch {
    return Response.json(
      { error: "Saved claims unavailable" },
      { status: 503 },
    );
  }
}
