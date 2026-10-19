"use client";
import { Children, useEffect, useRef, useState } from "react";
import Markdown from "react-markdown";
import humanCheck from "../lib/human-check.json";
import { filteredRanking, type Scope, type Snapshot } from "../lib/model";

const CONTROLS = "cross-topic--free-tier-premium-controls";
const ADS = "usability--ad-interruptions";
const metricLabels: Record<string, string> = {
  complaint_count: "Complaint/cancellation reviews",
  severity_sum: "Severity sum",
  mean_severity: "Mean severity",
  rank: "Rank",
  controls_to_ads_severity_ratio: "Controls / ads severity ratio",
  coverage_percent: "Completed share of nonempty reviews (%)",
  unspecified_percent: "Complaint/cancellation rows with no specific cause (%)",
  additional_complaint_rows: "Additional complaint rows (baseline minus random prefix)",
};
const number = (value: number | string) =>
  Number(value).toLocaleString("en-US");
const percent = (numerator: number, denominator: number) =>
  ((100 * numerator) / denominator).toFixed(1) + "%";
const readable: Record<string, string> = {
  other: "Other / no specific topic",
  usability: "Usability",
  catalog: "Catalog & lyrics",
  billing: "Billing & Premium",
  playback: "Playing music",
  access: "Account access",
  downloads: "Downloads & offline listening",
  support: "Customer support",
  severity: "Severity — exact",
  severity_exact: "Severity — exact",
  severity_within_one: "Severity — within one level",
  sentiment_sign: "Sentiment",
  needs_review: "Flag for a human check",
};
const pretty = (value: string) =>
  readable[value] ??
  value
    .replaceAll("_", " ")
    .replaceAll("--", " · ")
    .replace(/^./, (c) => c.toUpperCase());

function Distribution({
  title,
  rows,
  denominator,
}: {
  title: string;
  rows: Record<string, number>;
  denominator: number;
}) {
  return (
    <section className="distribution">
      <h3>{title}</h3>
      <ul>
        {Object.entries(rows)
          .sort((a, b) => b[1] - a[1])
          .map(([label, count]) => (
            <li key={label}>
              <div>
                <span>{pretty(label)}</span>
                <span>
                  {number(count)} <small>({percent(count, denominator)})</small>
                </span>
              </div>
              <meter
                min={0}
                max={denominator}
                value={count}
                aria-label={`${label}: ${count} of ${denominator}`}
              />
            </li>
          ))}
      </ul>
    </section>
  );
}

export default function Dashboard() {
  type Report = Snapshot & { meta: { source: "neon" | "local-file"; snapshot_id: string; imported_at: string | null } };
  const [data, setData] = useState<Report | null>(null);
  const [error, setError] = useState(false);
  const [reload, setReload] = useState(0);
  const [scope, setScope] = useState<Scope>("baseline");
  const [query, setQuery] = useState("");
  const [selected, setSelected] = useState(CONTROLS);
  const claimsDetails = useRef<HTMLDetailsElement>(null);
  useEffect(() => {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 20000);
    let active = true;
    setError(false);
    fetch("/api/dashboard", { signal: controller.signal })
      .then(async (r) => {
        if (!r.ok) throw new Error("Unavailable");
        const value: Report = await r.json();
        if (active) setData(value);
      })
      .catch(() => {
        if (active) setError(true);
      })
      .finally(() => clearTimeout(timer));
    return () => {
      active = false;
      clearTimeout(timer);
      controller.abort();
    };
  }, [reload]);
  const shell = (
    <header className="top">
      <div className="brand-mark" aria-hidden="true">
        s
      </div>
      <span>Spotify review priorities</span>
      <span className="stored-label">Saved analysis · no live AI calls</span>
    </header>
  );
  if (error)
    return (
      <>
        {shell}
        <main className="status">
          <h1>Saved analysis unavailable</h1>
          <p>
            The dashboard could not load its saved snapshot. No new
            classification or model call was attempted.
          </p>
          <button onClick={() => setReload((n) => n + 1)}>
            Retry saved data
          </button>
        </main>
      </>
    );
  if (!data)
    return (
      <>
        {shell}
        <main className="status" role="status">
          <h1>Loading saved review analysis…</h1>
        </main>
      </>
    );
  const p = data.payload,
    counts = p.summary.counts;
  const issues = filteredRanking(p.rankings[scope], query);
  const current = p.rankings[scope].find((r) => r.issue_id === selected)!;
  const examples = p.examples.filter((r) => r.issue_id === selected);
  const titleById = Object.fromEntries(
    p.rankings.baseline.map((r) => [r.issue_id, r.name]),
  );
  const citedIds = [...new Set(
    [...p.artifacts.memo.matchAll(/\[([BS]\d+)\]\(phase7\/(?:secondary-)?claims\.csv\)/g)]
      .map((match) => match[1]),
  )];
  const claimsById = new Map(
    (["baseline", "secondary"] as const).flatMap((csvScope) =>
      p.claims[csvScope].map((claim) => [claim.claim_id, { claim, csvScope }] as const),
    ),
  );
  const maximum = Math.max(
    ...p.rankings.baseline
      .filter((r) => [CONTROLS, ADS].includes(r.issue_id))
      .map((r) => Number(r.severity_sum)),
  );
  const anchor = ({
    href,
    children,
  }: {
    href?: string;
    children?: React.ReactNode;
  }) => {
    const claimId = Children.toArray(children).join("");
    if ((href === "phase7/claims.csv" || href === "phase7/secondary-claims.csv") &&
        citedIds.includes(claimId))
      return (
        <sup className="claim-reference">
          <a href={`#claim-${claimId}`} onClick={() => {
            if (claimsDetails.current) claimsDetails.current.open = true;
          }}>{children}</a>
        </sup>
      );
    if (href?.includes("phase7-cohort-spotcheck-v3"))
      return (
        <a
          href="/api/examples?id=7e271329-4c82-403b-a59a-7fd8b6c40405"
          target="_blank"
          rel="noreferrer"
        >
          {children}
        </a>
      );
    return <span>{children}</span>;
  };
  return (
    <>
      {shell}
      <main>
        <div className="page-heading">
          <div>
            <h1>What should Spotify fix first?</h1>
            <p>
              Reviews from {p.meta.review_period.from.slice(0, 10)} to{" "}
              {p.meta.review_period.to.slice(0, 10)} · Spotify Google Play
              reviews
            </p>
          </div>
        </div>
        <section className="answer-card" data-section="01-answer">
          <p>
            <strong>Biggest fixable complaint:</strong> free users lost basic
            playback controls (forced shuffle; can't go back, skip forward,
            seek, repeat or pick a song). <strong>Recommendation:</strong> test
            restoring some of these controls for free users, weighing Premium
            conversion against complaints. Ads are a close second.
          </p>
          <a href="#memo">Read the full product memo →</a>
        </section>
        <section className="reading-guide" data-section="02-how-to-read">
          <h2>How to read this page</h2>
          <p>
            We analyzed {number(counts.completed_rows)} of{" "}
            {number(counts.nonempty_rows)} Spotify Google Play reviews (36%)
            with AI labels for topic, intent, severity (1 = No reported problem;
            5 = Explicit serious financial, privacy or data harm) and sentiment.
          </p>
          <p>
            Complaints were grouped into 35 themes and ranked by
            severity-weighted total (number of complaints × average severity).
          </p>
          <p>
            Two views are shown: all analyzed reviews, and a random sample of
            100,000 reviews, which is the most representative because the first
            view counts identical copies of short reviews like 'Too many ads'
            many times.
          </p>
        </section>
        <aside
          className="scope-banner"
          aria-label="Partial scope disclosure"
          data-section="03-scope"
        >
          <strong>Partial analysis: 36% of reviews.</strong>
          <span>
            {number(counts.completed_rows)} reviews analyzed;{" "}
            {number(counts.out_of_scope_rows)} not analyzed (outside our
            budgeted scope); {number(counts.terminal_rows)} could not be
            processed; {number(counts.empty_rows)} were empty. Results describe
            the analyzed reviews, not every review.
          </span>
        </aside>
        <section
          className="kpis"
          aria-label="Dataset summary"
          data-section="04-key-numbers"
        >
          <div>
            <span>Reviews analyzed</span>
            <strong>{number(counts.completed_rows)} (36%)</strong>
            <small>
              {number(counts.direct_original_rows)} unique texts read by AI;
              labels reused for {number(counts.cache_reused_rows)} identical
              copies
            </small>
          </div>
          <div>
            <span>Complaints and cancellations</span>
            <strong>
              {number(
                p.rankings.baseline.reduce(
                  (n, r) => n + Number(r.complaint_count),
                  0,
                ),
              )}
            </strong>
            <small>Used for the ranking</small>
          </div>
        </section>
        <section
          className="comparison"
          aria-labelledby="comparison-heading"
          data-section="05-controls-vs-ads"
        >
          <div className="section-head">
            <div>
              <h2 id="comparison-heading">
                Free users' lost playback controls outrank ads in both views
              </h2>
              <p>
                Severity-weighted total = number of complaints × average
                severity (1–5)
              </p>
            </div>
            <div className="legend">
              <span className="baseline-key">All analyzed reviews</span>
              <span className="sample-key">
                Random sample (most representative)
              </span>
            </div>
          </div>
          {[CONTROLS, ADS].map((id) => (
            <div className="compare-row" key={id}>
              <h3>{titleById[id]}</h3>
              <div className="bar-pair">
                {(["baseline", "random_prefix"] as const).map((view) => {
                  const row = p.rankings[view].find((r) => r.issue_id === id)!;
                  return (
                    <div className="bar-line" key={view}>
                      <div className="bar-track">
                        <div
                          className={"bar " + view}
                          style={{
                            width:
                              (100 * Number(row.severity_sum)) / maximum + "%",
                          }}
                        />
                      </div>
                      <span>
                        {number(row.severity_sum)}{" "}
                        <small>
                          total · {number(row.complaint_count)} reviews
                        </small>
                      </span>
                    </div>
                  );
                })}
              </div>
            </div>
          ))}
          <p className="caption">
            Ads complaints shrink in the random sample because short identical
            reviews ('Too many ads') are counted many times in the all-reviews
            view; controls complaints are long and unique, so they barely
            change.
          </p>
        </section>
        <section
          id="rankings"
          className="ranking-section"
          data-section="06-ranking"
        >
          <div className="section-head">
            <div>
              <h2>Complaint themes, ranked</h2>
              <p>
                Complaints and cancellations only · choose a theme to inspect
                selected examples
              </p>
            </div>
            <div className="switch" aria-label="Ranking view">
              <button
                aria-pressed={scope === "baseline"}
                onClick={() => setScope("baseline")}
              >
                All analyzed reviews
              </button>
              <button
                aria-pressed={scope === "random_prefix"}
                onClick={() => setScope("random_prefix")}
              >
                Random sample
              </button>
            </div>
          </div>
          <div className="table-tools">
            <label>
              Search themes
              <input
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="e.g. controls, ads, login"
              />
            </label>
            <span>
              {issues.length} of {p.rankings[scope].length} themes
            </span>
          </div>
          <div className="table-scroll">
            <table>
              <caption className="sr-only">
                {scope === "baseline"
                  ? "All analyzed reviews"
                  : "Random sample"}{" "}
                issue ranking
              </caption>
              <thead>
                <tr>
                  <th scope="col">Rank</th>
                  <th scope="col">Complaint theme</th>
                  <th scope="col">Reviews</th>
                  <th scope="col">Severity-weighted total</th>
                  <th scope="col">Average severity (1–5)</th>
                </tr>
              </thead>
              <tbody>
                {issues.map((row) => (
                  <tr
                    key={row.issue_id}
                    className={selected === row.issue_id ? "selected" : ""}
                  >
                    <td>{row.rank}</td>
                    <th scope="row">
                      <button
                        className="issue-button"
                        aria-pressed={selected === row.issue_id}
                        onClick={() => setSelected(row.issue_id)}
                      >
                        {row.name}
                      </button>
                      {row.rank === "1" && (
                        <span className="rank-tag">
                          general — not a fix target
                        </span>
                      )}
                      {row.issue_id === CONTROLS && (
                        <span className="rank-tag recommended">
                          recommended
                        </span>
                      )}
                    </th>
                    <td>{number(row.complaint_count)}</td>
                    <td>{number(row.severity_sum)}</td>
                    <td>{Number(row.mean_severity).toFixed(2)}</td>
                  </tr>
                ))}
                {!issues.length && (
                  <tr>
                    <td colSpan={5}>
                      No themes match this search. Clear the search to restore
                      the ranking.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
          <p className="caption">
            Sorted by severity-weighted total, as required by the course
            contract.
          </p>
          <p className="watch-list">
            <strong>Watch list: rare but severe.</strong> Hacked or compromised
            accounts (
            {number(
              p.rankings.baseline.find(
                (r) => r.issue_id === "access--account-security",
              )!.complaint_count,
            )}{" "}
            reviews, average severity{" "}
            {Number(
              p.rankings.baseline.find(
                (r) => r.issue_id === "access--account-security",
              )!.mean_severity,
            ).toFixed(2)}
            ); login problems (average{" "}
            {Number(
              p.rankings.baseline.find(
                (r) => r.issue_id === "access--login-credentials",
              )!.mean_severity,
            ).toFixed(2)}
            ). All analyzed reviews.
          </p>
        </section>
        <section className="examples" id="examples" data-section="07-examples">
          <h2>
            Example reviews (chosen to illustrate the theme; not a random
            sample)
          </h2>
          <p>{current?.name}</p>
          <div className="quote-grid">
            {examples.map((row) => (
              <blockquote
                id={"review-" + row.review_id.slice(0, 8)}
                key={row.review_id}
              >
                <p>{row.text}</p>
                <cite>{row.review_id.slice(0, 8)}</cite>
              </blockquote>
            ))}
          </div>
        </section>
        <section className="breakdowns" data-section="08-review-mix">
          <div className="section-head">
            <div>
              <h2>What the analyzed reviews say</h2>
              <p>
                Most reviews are short praise like 'Great app', which is why
                'Other' and 'Praise' dominate.
              </p>
            </div>
          </div>
          <div className="distribution-grid">
            <Distribution
              title="Topic"
              rows={p.summary.distributions.topic}
              denominator={counts.completed_rows}
            />
            <Distribution
              title="Intent"
              rows={p.summary.distributions.intent}
              denominator={counts.completed_rows}
            />
            <Distribution
              title="Severity level"
              rows={p.summary.distributions.severity}
              denominator={counts.completed_rows}
            />
            <Distribution
              title="Sentiment"
              rows={p.summary.distributions.sentiment_sign}
              denominator={counts.completed_rows}
            />
          </div>
          <div className="severity-legend">
            <strong>Severity scale (from the label guide)</strong>
            <ol>
              <li>
                No reported problem: praise, neutral/unclear text or a pure
                feature request.
              </li>
              <li>
                Dislike, generic criticism, minor annoyance or cosmetic issue
                without functional loss.
              </li>
              <li>
                Degraded/restricted function, with some use or workaround
                remaining.
              </li>
              <li>
                Clearly blocked core task, such as inability to log in or play
                music.
              </li>
              <li>
                Explicit serious financial, privacy or data harm. High price,
                crashes, anger and cancellation intent alone do not support
                level 5.
              </li>
            </ol>
          </div>
        </section>
        <section className="human-flags" data-section="09-human-flags">
          <h2>Reviews flagged for a human check (78%)</h2>
          <p>
            Most flags ({number(p.summary.flag_reasons.missing_context)}) are
            'missing context': very short reviews that don't say why, which the
            course contract requires us to flag. Others: low model confidence (
            {number(p.summary.flag_reasons.low_confidence)}), language not
            understood ({number(p.summary.flag_reasons.language_not_understood)}
            ), non-English (
            {number(p.summary.flag_reasons.language_non_english)}). Reasons
            overlap.
          </p>
        </section>
        <section className="quality-section" data-section="10-quality">
          <h2>How accurate are the labels?</h2>
          <div className="quality-grid">
            <div>
              <h3>Human check: 50 reviews hand-labeled by the author</h3>
              <table>
                <caption className="sr-only">
                  Human-label agreement by field
                </caption>
                <thead>
                  <tr>
                    <th>Field</th>
                    <th>Agreement</th>
                  </tr>
                </thead>
                <tbody>
                  {Object.entries(humanCheck.fields).map(([field, v]) => (
                    <tr key={field}>
                      <th scope="row">{pretty(field)}</th>
                      <td>
                        {Math.round(100 * v.agreement)}%{" "}
                        <small>
                          ({v.agree}/{v.denominator})
                        </small>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              <p className="caption">
                Saved human evaluation; a small, fixed set of 50 reviews.
                Entities are excluded.
              </p>
            </div>
            <div>
              <h3>
                Consistency check: a second AI model re-labeled 500 random
                reviews
              </h3>
              <table>
                <caption className="sr-only">
                  Verifier agreement by field
                </caption>
                <thead>
                  <tr>
                    <th>Field</th>
                    <th>Agreement</th>
                  </tr>
                </thead>
                <tbody>
                  {Object.entries(p.artifacts.verifier.overall.fields).map(
                    ([field, v]) => (
                      <tr key={field}>
                        <th scope="row">{pretty(field)}</th>
                        <td>
                          {percent(v.agree, v.denominator)}{" "}
                          <small>
                            ({v.agree}/{v.denominator})
                          </small>
                        </td>
                      </tr>
                    ),
                  )}
                </tbody>
              </table>
              <p className="caption">
                Agreement shows consistency between models, not correctness. The
                second model also handled fallback classifications, so some
                agreement is self-agreement. Entities are excluded.
              </p>
            </div>
          </div>
        </section>
        <section id="memo" className="memo-section" data-section="11-memo">
          <div className="section-head">
            <div>
              <h2>Full product memo</h2>
              <p>
                Owner-approved revision of the saved model draft · approved{" "}
                {p.meta.memo_approval.approved_on}
              </p>
            </div>
            <span className="approval">Owner approved</span>
          </div>
          <article className="memo">
            <Markdown skipHtml components={{ a: anchor }}>
              {p.artifacts.memo.replace(/^# .+\n/, "")}
            </Markdown>
          </article>
          <details ref={claimsDetails} id="cited-claims">
            <summary>Claims cited in the recommendation</summary>
            <div className="table-scroll">
              <table>
                <caption className="sr-only">Claims cited in the recommendation</caption>
                <thead>
                  <tr>
                    {["ID", "Issue", "Metric", "Scope", "Value", "Source"].map((label) => (
                      <th scope="col" key={label}>{label}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {citedIds.map((id) => {
                    const entry = claimsById.get(id);
                    if (!entry) return null;
                    const { claim, csvScope } = entry;
                    return (
                      <tr key={id} id={`claim-${id}`} tabIndex={-1}>
                        <th scope="row">{id}</th>
                        <td>{claim.issue_id === "scope" ? "All classified reviews" : titleById[claim.issue_id]}</td>
                        <td>{metricLabels[claim.metric] ?? claim.metric}</td>
                        <td>{csvScope === "baseline" ? "baseline" : claim.scope}</td>
                        <td>{claim.value}</td>
                        <td><a href={`/api/claims?scope=${csvScope}`}>
                          {csvScope === "baseline" ? `Baseline claims CSV (${id})` : claim.source}
                        </a></td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </details>
          <div className="downloads">
            <span>
              Claim references: B ={" "}
              <a href="/api/claims?scope=baseline">Download full baseline claims CSV</a>; S ={" "}
              <a href="/api/claims?scope=secondary">
                Download full secondary claims CSV
              </a>
              .
            </span>
            <a href="/api/claims?scope=baseline">Download full baseline claims CSV</a>
            <a href="/api/claims?scope=secondary">Download full secondary claims CSV</a>
          </div>
        </section>
        <section className="provenance" data-section="12-methodology">
          <details id="methodology">
            <summary>
              <h2>Methodology &amp; definitions</h2>
            </summary>
            <p>
              Frozen classification: the saved prompt, thresholds and label
              configuration were held fixed. Exact-text result caching reuses
              completed labels for identical text; this is our result cache, not
              provider prompt caching. Complaint themes use final lexical
              grouping v3, based on text rules and random spot-checks.
            </p>
            <h3>Glossary</h3>
            <dl className="glossary">
              <dt>Propagated baseline</dt>
              <dd>
                The all-analyzed-reviews view: direct AI results plus labels
                reused for identical copies, including copies outside the random
                sample.
              </dd>
              <dt>Random prefix</dt>
              <dd>
                The seeded, uniformly drawn first 100,000 nonempty review IDs.
                The ranking includes successfully analyzed members; 40 failed
                items are absent.
              </dd>
              <dt>Cache alias</dt>
              <dd>
                A review whose text exactly matches another review and reuses
                its saved labels.
              </dd>
              <dt>Terminal failure</dt>
              <dd>
                A review that could not be processed after the permitted repair
                and retry policy. It is excluded from the results.
              </dd>
              <dt>Cohort</dt>
              <dd>
                A complaint theme formed by a final text-matching rule; each
                complaint belongs to one theme.
              </dd>
              <dt>severity_sum</dt>
              <dd>
                The sum of severity levels in a theme: complaint count × average
                severity. This is the severity-weighted total used for ranking.
              </dd>
            </dl>
            <p>
              This page reads a saved aggregate snapshot. No model is called on
              page load, refresh, search or scope switching. Full records and
              provider call logs are not included in this public snapshot.
            </p>
            <details>
              <summary>Group-call outputs</summary>
              <p>
                Display names were finalized by the owner; the model's proposed
                names are shown here.
              </p>
              {Object.entries(p.artifacts.groups).map(([stage, value]) => (
                <div key={stage}>
                  <h3>{stage}</h3>
                  <ul>
                    {value.issues.map((row) => (
                      <li key={row.issue_id}>
                        <code>{row.issue_id}</code> — {row.name}
                      </li>
                    ))}
                  </ul>
                </div>
              ))}
            </details>
            <details>
              <summary>Original model memo and owner-edit provenance</summary>
              <p>
                The approved memo above includes owner-directed editorial edits.
                The original response below is preserved as generated.
              </p>
              <pre>{JSON.stringify(p.artifacts.original_memo, null, 2)}</pre>
            </details>
            <details>
              <summary>Verifier agreement by flag and fallback split</summary>
              <p>
                Agreement with the second AI model, grouped by the final
                record's flag and fallback status. These are overlapping
                comparisons, not separate samples.
              </p>
              <div className="table-scroll">
                <table>
                  <caption className="sr-only">
                    Verifier agreement by flag and fallback split
                  </caption>
                  <thead>
                    <tr>
                      <th scope="col">Field</th>
                      {(
                        [
                          ["flagged", "Flagged for a human check"],
                          ["unflagged", "Not flagged"],
                          ["fallback", "With fallback"],
                          ["no_fallback", "Without fallback"],
                        ] as const
                      ).map(([key, label]) => (
                        <th scope="col" key={key}>
                          {label}
                          <br />
                          <small>{p.artifacts.verifier[key].n} reviews</small>
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {Object.keys(p.artifacts.verifier.overall.fields).map(
                      (field) => (
                        <tr key={field}>
                          <th scope="row">{pretty(field)}</th>
                          {(
                            [
                              "flagged",
                              "unflagged",
                              "fallback",
                              "no_fallback",
                            ] as const
                          ).map((key) => {
                            const v = p.artifacts.verifier[key].fields[field];
                            return (
                              <td key={key}>
                                {v && v.denominator ? (
                                  <>
                                    {percent(v.agree, v.denominator)}{" "}
                                    <small>
                                      ({v.agree}/{v.denominator})
                                    </small>
                                  </>
                                ) : (
                                  "Not available"
                                )}
                              </td>
                            );
                          })}
                        </tr>
                      ),
                    )}
                  </tbody>
                </table>
              </div>
              <p className="caption">
                Agreement shows consistency, not human accuracy. Verifier and
                fallback use the same model.
              </p>
            </details>
            <details>
              <summary>Definitions and source hashes</summary>
              <dl>
                {Object.entries(p.meta.definitions).map(([key, value]) => (
                  <div key={key}>
                    <dt>{pretty(key)}</dt>
                    <dd>{value}</dd>
                  </div>
                ))}
              </dl>
              <p>
                Snapshot <code>{data.snapshot_id}</code>
              </p>
              <p>
                Classifier <code>{p.meta.label_config}</code>
              </p>
              <p>
                Grouping <code>{p.meta.grouping_hash}</code>
              </p>
              <pre>{JSON.stringify(p.meta.source_hashes, null, 2)}</pre>
            </details>
            <p>
              Human-evaluation figures are a bundled saved summary, not read from the database. Source: <code>{humanCheck.source}</code>;
              SHA-256 <code>{humanCheck.source_sha256}</code>.
            </p>
          </details>
        </section>
        <footer>
          Spotify Google Play reviews · partial analysis · no live AI calls
          <p>Report data: {data.meta.source === "neon" ? "Neon" : "local file"} · snapshot {data.meta.snapshot_id} · imported {data.meta.imported_at ?? "not applicable (local file)"}</p>
        </footer>
      </main>
    </>
  );
}
