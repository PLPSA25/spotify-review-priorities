export type Scope = "baseline" | "random_prefix";
export type Ranking = {
  rank: string;
  issue_id: string;
  name: string;
  complaint_count: string;
  severity_sum: string;
  mean_severity: string;
  priority_score: string;
};
export type Claim = {
  claim_id: string;
  issue_id: string;
  metric: string;
  value: string;
  scope?: string;
  source?: string;
};
export type Example = { review_id: string; issue_id: string; text: string };
export type Agreement = {
  n: number;
  fields: Record<
    string,
    { agree: number; denominator: number; agreement: number | null }
  >;
};
export type Snapshot = {
  snapshot_id: string;
  payload: {
    version: number;
    meta: {
      label_config: string;
      grouping_hash: string;
      memo_approval: {
        status: string;
        memo_sha256: string;
        approved_on: string;
      };
      review_period: { from: string; to: string };
      source_hashes: Record<string, string>;
      definitions: Record<string, string>;
      contains_full_records: boolean;
      model_calls_from_dashboard: boolean;
    };
    summary: {
      counts: Record<string, number>;
      distributions: Record<string, Record<string, number>>;
      flag_reasons: Record<string, number>;
      quarantine_reasons: Record<string, number>;
    };
    rankings: Record<Scope, Ranking[]>;
    claims: { baseline: Claim[]; secondary: Claim[] };
    examples: Example[];
    artifacts: {
      memo: string;
      original_memo: Record<string, unknown>;
      groups: Record<string, { issues: { issue_id: string; name: string }[] }>;
      verifier: {
        overall: Agreement;
        flagged: Agreement;
        unflagged: Agreement;
        fallback: Agreement;
        no_fallback: Agreement;
        interpretation: string;
        sampled: number;
        terminal_verifier_items: number;
      };
    };
  };
};

export function parseScope(value: string | null): Scope | null {
  return value === "baseline" || value === "random_prefix" ? value : null;
}
export function filteredRanking(rows: Ranking[], query: string) {
  const needle = query.trim().toLocaleLowerCase();
  const terms = needle.split(/[^a-z0-9]+/).filter(Boolean);
  return rows.filter((row) => {
    const words = (row.name + " " + row.issue_id)
      .toLocaleLowerCase()
      .split(/[^a-z0-9]+/);
    return terms.every((term) =>
      words.some(
        (word) =>
          word.startsWith(term) ||
          (term === "ads" && (word === "ad" || word.startsWith("advert"))),
      ),
    );
  });
}
export function validateSnapshot(value: unknown): asserts value is Snapshot {
  const s = value as Snapshot;
  if (
    !s ||
    !/^[a-f0-9]{64}$/.test(s.snapshot_id) ||
    s.payload?.version !== 1 ||
    s.payload.meta?.contains_full_records !== false ||
    s.payload.meta?.model_calls_from_dashboard !== false ||
    s.payload.meta?.memo_approval?.status !== "owner_approved"
  )
    throw new Error("Invalid public snapshot");
  const counts = s.payload.summary?.counts;
  if (
    !counts ||
    counts.completed_rows +
      counts.out_of_scope_rows +
      counts.terminal_rows +
      counts.empty_rows !==
      counts.total_rows ||
    counts.completed_rows !==
      counts.cache_reused_rows + counts.direct_original_rows
  )
    throw new Error("Coverage does not reconcile");
  for (const scope of ["baseline", "random_prefix"] as const) {
    const rows = s.payload.rankings?.[scope];
    if (!Array.isArray(rows) || !rows.length || rows.length > 1000)
      throw new Error("Invalid rankings");
    for (const [index, row] of rows.entries()) {
      if (
        Number(row.rank) !== index + 1 ||
        row.priority_score !== row.severity_sum ||
        !Number.isFinite(Number(row.mean_severity))
      )
        throw new Error("Invalid issue metric");
      if (
        index &&
        (Number(rows[index - 1].severity_sum) < Number(row.severity_sum) ||
          (rows[index - 1].severity_sum === row.severity_sum &&
            rows[index - 1].issue_id > row.issue_id))
      )
        throw new Error("Invalid ranking order");
    }
  }
  if (
    !Array.isArray(s.payload.examples) ||
    s.payload.examples.length > 200 ||
    s.payload.examples.some(
      (r) => typeof r.text !== "string" || r.text.length > 100000,
    )
  )
    throw new Error("Examples must stay bounded");
}
