"use client";
import { useEffect, useState } from "react";
import Markdown from "react-markdown";
import { filteredRanking, type Scope, type Snapshot } from "../lib/model";

const CONTROLS = "cross-topic--free-tier-premium-controls";
const ADS = "usability--ad-interruptions";
const number = (value: number | string) =>
  Number(value).toLocaleString("en-US");
const percent = (numerator: number, denominator: number) =>
  ((100 * numerator) / denominator).toFixed(1) + "%";
const pretty = (value: string) =>
  value.replaceAll("_", " ").replaceAll("--", " · ");
const reasonNames: Record<string, string> = {
  language_non_english: "Non-English language",
  language_not_understood: "Language not understood",
  missing_context: "Missing context",
  low_confidence: "Low confidence",
};

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
  const [data, setData] = useState<Snapshot | null>(null);
  const [error, setError] = useState(false);
  const [reload, setReload] = useState(0);
  const [scope, setScope] = useState<Scope>("baseline");
  const [query, setQuery] = useState("");
  const [selected, setSelected] = useState(CONTROLS);
  useEffect(() => {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 20000);
    let active = true;
    setError(false);
    fetch("/api/dashboard", { signal: controller.signal })
      .then(async (r) => {
        if (!r.ok) throw new Error("Unavailable");
        const value: Snapshot = await r.json();
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
    if (href === "phase7/claims.csv")
      return <a href="/api/claims?scope=baseline">{children}</a>;
    if (href === "phase7/secondary-claims.csv")
      return <a href="/api/claims?scope=secondary">{children}</a>;
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
              {p.meta.review_period.to.slice(0, 10)} · frozen classification and
              final grouping rules
            </p>
          </div>
          <a href="#memo" className="button-link">
            Read the approved memo <span aria-hidden="true">↗</span>
          </a>
        </div>
        <aside className="scope-banner" aria-label="Partial scope disclosure">
          <strong>
            Partial scope ·{" "}
            {percent(counts.completed_rows, counts.nonempty_rows)} coverage
          </strong>
          <span>
            {number(counts.completed_rows)} of {number(counts.nonempty_rows)}{" "}
            nonempty rows classified. {number(counts.out_of_scope_rows)} outside
            the classified scope; {number(counts.terminal_rows)} terminal
            failures; {number(counts.empty_rows)} empty texts. Missing
            predictions remain a limitation.
          </span>
        </aside>
        <section className="kpis" aria-label="Dataset summary">
          <div>
            <span>Classified original rows</span>
            <strong>{number(counts.completed_rows)}</strong>
            <small>Includes exact-text propagated rows</small>
          </div>
          <div>
            <span>Direct result originals</span>
            <strong>{number(counts.direct_original_rows)}</strong>
            <small>
              {number(counts.cache_reused_rows)} additional cache aliases
            </small>
          </div>
          <div>
            <span>Complaint / cancellation rows</span>
            <strong>
              {number(
                p.rankings.baseline.reduce(
                  (n, r) => n + Number(r.complaint_count),
                  0,
                ),
              )}
            </strong>
            <small>Eligible for the baseline ranking</small>
          </div>
          <div>
            <span>Needs human review</span>
            <strong>
              {percent(counts.needs_review_rows, counts.completed_rows)}
            </strong>
            <small>
              {number(counts.needs_review_rows)} classified rows flagged
            </small>
          </div>
        </section>
        <section className="comparison" aria-labelledby="comparison-heading">
          <div className="section-head">
            <div>
              <h2 id="comparison-heading">
                Controls stay ahead of ads in both views
              </h2>
              <p>
                Severity-weighted complaint points · count × mean severity =
                severity_sum
              </p>
            </div>
            <div className="legend">
              <span className="baseline-key">Propagated baseline</span>
              <span className="sample-key">Random prefix only</span>
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
                          points · {number(row.complaint_count)} rows
                        </small>
                      </span>
                    </div>
                  );
                })}
              </div>
            </div>
          ))}
          <p className="caption">
            Same linear scale for both views. Comparison shows two specific
            issues; Other—unspecified ranks first overall. The baseline adds
            exact-text matches outside the random prefix, weighting repeated
            texts more heavily.
          </p>
        </section>
        <section id="rankings" className="ranking-section">
          <div className="section-head">
            <div>
              <h2>Issue ranking</h2>
              <p>
                Completed complaints and cancellations only · click an issue to
                inspect selected examples
              </p>
            </div>
            <div className="switch" aria-label="Ranking view">
              <button
                aria-pressed={scope === "baseline"}
                onClick={() => setScope("baseline")}
              >
                Propagated baseline
              </button>
              <button
                aria-pressed={scope === "random_prefix"}
                onClick={() => setScope("random_prefix")}
              >
                Random prefix only
              </button>
            </div>
          </div>
          <div className="table-tools">
            <label>
              Search issues
              <input
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="e.g. controls, ads, login"
              />
            </label>
            <span>
              {issues.length} of {p.rankings[scope].length} issues · priority =
              severity_sum
            </span>
          </div>
          <div className="table-scroll">
            <table>
              <caption className="sr-only">
                {scope === "baseline"
                  ? "Propagated baseline"
                  : "Random prefix only"}{" "}
                issue ranking
              </caption>
              <thead>
                <tr>
                  <th scope="col">Rank</th>
                  <th scope="col">Issue</th>
                  <th scope="col">Reviews</th>
                  <th scope="col">Severity sum / priority</th>
                  <th scope="col">Mean severity</th>
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
                    </th>
                    <td>{number(row.complaint_count)}</td>
                    <td>{number(row.severity_sum)}</td>
                    <td>{Number(row.mean_severity).toFixed(2)}</td>
                  </tr>
                ))}
                {!issues.length && (
                  <tr>
                    <td colSpan={5}>
                      No issues match this search. Clear the search to restore
                      the ranking.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
          <p className="caption">
            Baseline counts every completed original row, including aliases.
            Random prefix uses classified members of the seeded first 100,000
            nonempty IDs; 40 terminally failed IDs are absent. Sort:
            severity_sum descending, then issue ID ascending.
          </p>
          <div className="examples" id="examples">
            <h3>Selected examples · {current?.name}</h3>
            <p>
              Bounded, selected evidence. These examples are not a random
              accuracy sample.
            </p>
            <div className="quote-grid">
              {examples.map((row) => (
                <blockquote
                  id={"review-" + row.review_id.slice(0, 8)}
                  key={row.review_id}
                >
                  <p>{row.text}</p>
                  <cite>{row.review_id}</cite>
                </blockquote>
              ))}
            </div>
          </div>
        </section>
        <section className="breakdowns">
          <div className="section-head">
            <div>
              <h2>What the classified rows contain</h2>
              <p>
                Each distribution uses {number(counts.completed_rows)} completed
                original rows. Cache aliases count separately.
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
              title="Sentiment sign"
              rows={p.summary.distributions.sentiment_sign}
              denominator={counts.completed_rows}
            />
          </div>
        </section>
        <section className="review-quality">
          <div>
            <h2>Review flags</h2>
            <p>
              Final stored reasons among {number(counts.needs_review_rows)}{" "}
              flagged rows. Reasons overlap; they do not sum to the number of
              flagged rows.
            </p>
            <ul className="reason-list">
              {Object.entries(p.summary.flag_reasons)
                .sort((a, b) => b[1] - a[1])
                .map(([reason, count]) => (
                  <li key={reason}>
                    <span>{reasonNames[reason] ?? pretty(reason)}</span>
                    <strong>{number(count)}</strong>
                  </li>
                ))}
            </ul>
          </div>
          <div>
            <h2>Blinded verifier comparison</h2>
            <p>
              {p.artifacts.verifier.sampled} final records;{" "}
              {p.artifacts.verifier.terminal_verifier_items} terminal verifier
              items. Agreement ≠ human accuracy. Verifier and fallback use Luna,
              so agreement partly reflects self-agreement. Entities excluded.
            </p>
            <table>
              <caption className="sr-only">Verifier agreement by field</caption>
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
                      <th>{pretty(field)}</th>
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
          </div>
        </section>
        <section id="memo" className="memo-section">
          <div className="section-head">
            <div>
              <h2>Product decision</h2>
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
          <div className="downloads">
            <a href="/api/claims?scope=baseline">Baseline claims CSV</a>
            <a href="/api/claims?scope=secondary">Secondary evidence CSV</a>
          </div>
        </section>
        <section className="provenance">
          <h2>Stored outputs and provenance</h2>
          <p>
            This page reads a saved aggregate snapshot. No model is called on
            page load, refresh, search or scope switching. Full records and
            provider call logs are not included in this public snapshot.
          </p>
          <details>
            <summary>Group-call outputs</summary>
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
            <pre>{JSON.stringify(p.artifacts.verifier, null, 2)}</pre>
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
        </section>
        <footer>
          Partial-scope course analysis · exact-text result caching · frozen
          labels and final v3 lexical grouping
        </footer>
      </main>
    </>
  );
}
