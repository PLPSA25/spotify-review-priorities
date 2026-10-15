import { test, expect } from "@playwright/test";
import { mkdirSync, writeFileSync, readFileSync } from "node:fs";

test("Saved data flow, both rankings, claims and memo work without external calls", async ({
  page,
  request,
}) => {
  const external: string[] = [];
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  await page.route("**/*", (route) => {
    const url = new URL(route.request().url());
    if (!["127.0.0.1", "localhost"].includes(url.hostname)) {
      external.push(url.origin);
      return route.abort();
    }
    return route.continue();
  });
  await page.goto("/");
  await expect(
    page.getByRole("heading", { name: "What should Spotify fix first?" }),
  ).toBeVisible();
  await expect(page.getByLabel("Partial scope disclosure")).toContainText(
    "Partial analysis: 36%",
  );
  await expect(page.getByLabel("Partial scope disclosure")).toContainText(
    "422,845",
  );
  const row = page.getByRole("row").filter({
    has: page.getByRole("button", {
      name: "Free-tier playback controls locked behind Premium",
      exact: true,
    }),
  });
  await expect(row).toContainText("4,444");
  await page
    .getByRole("button", { name: "Random sample", exact: true })
    .click();
  await expect(row).toContainText("4,440");
  await expect(row).toContainText("13,865");
  await page
    .getByRole("button", { name: "All analyzed reviews", exact: true })
    .click();
  await page.getByLabel("Search themes").fill("ads");
  await expect(page.getByText("1 of 35 themes")).toBeVisible();
  await page.getByLabel("Search themes").fill("zzzzzz");
  await expect(
    page.getByText("No themes match this search.", { exact: false }),
  ).toBeVisible();
  await page.getByLabel("Search themes").fill("");
  await expect(
    page.getByText("Owner-approved revision of the saved model draft.", {
      exact: false,
    }),
  ).toBeVisible();
  await expect(
    page.getByRole("link", { name: "review 7e271329" }),
  ).toHaveAttribute(
    "href",
    "/api/examples?id=7e271329-4c82-403b-a59a-7fd8b6c40405",
  );
  const example = await request.get(
    "/api/examples?id=7e271329-4c82-403b-a59a-7fd8b6c40405",
  );
  expect((await example.json()).text).toContain("to play in order buy premium");
  expect((await request.get("/api/dashboard?scope=invalid")).status()).toBe(
    400,
  );
  expect((await request.get("/api/claims?scope=invalid")).status()).toBe(400);
  expect((await request.post("/api/dashboard")).status()).toBe(405);
  const baseline = await request.get("/api/claims?scope=baseline");
  expect(await baseline.text()).toContain(
    '"B6","cross-topic--free-tier-premium-controls","mean_severity","3.122637"',
  );
  expect(
    await (await request.get("/api/claims?scope=secondary")).text(),
  ).toContain('"S11"');
  expect(external).toEqual([]);
  expect(errors).toEqual([]);
  await page.screenshot({
    path: "test-results/dashboard-desktop.png",
    fullPage: true,
  });
});
test("Mobile view stays within the viewport and controls are keyboard accessible", async ({
  page,
}) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/");
  await expect(
    page.getByRole("heading", {
      name: "Complaint themes, ranked",
      exact: true,
    }),
  ).toBeVisible();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBe(true);
  const button = page.getByRole("button", {
    name: "Random sample",
    exact: true,
  });
  await button.focus();
  await page.keyboard.press("Enter");
  await expect(button).toHaveAttribute("aria-pressed", "true");
  await page.screenshot({
    path: "test-results/dashboard-mobile.png",
    fullPage: true,
  });
});
test("Unavailable data presents a retry state without a fake fallback", async ({
  page,
}) => {
  await page.route("**/api/dashboard", (route) =>
    route.fulfill({
      status: 503,
      contentType: "application/json",
      body: JSON.stringify({ error: "Unavailable" }),
    }),
  );
  await page.goto("/");
  await expect(
    page.getByRole("heading", { name: "Saved analysis unavailable" }),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Retry saved data" }),
  ).toBeVisible();
  await expect(
    page.getByRole("heading", {
      name: "Complaint themes, ranked",
      exact: true,
    }),
  ).toHaveCount(0);
});

test("Untrusted review text and model Markdown cannot execute HTML", async ({
  page,
  request,
}) => {
  const snapshot = await (await request.get("/api/dashboard")).json();
  const attack =
    '<img src="https://example.invalid/x" onerror="window.__review_xss=true">';
  const selected = snapshot.payload.examples.find(
    (row: { issue_id: string }) =>
      row.issue_id === "cross-topic--free-tier-premium-controls",
  );
  selected.text = attack;
  snapshot.payload.artifacts.memo =
    attack + "\n\n" + snapshot.payload.artifacts.memo;
  await page.route("**/api/dashboard", (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(snapshot),
    }),
  );
  await page.goto("/");
  await expect(
    page.getByRole("heading", { name: "What should Spotify fix first?" }),
  ).toBeVisible();
  await expect(
    page.locator("blockquote").filter({ hasText: attack }),
  ).toHaveCount(1);
  await expect(page.locator("img")).toHaveCount(0);
  expect(await page.evaluate(() => "__review_xss" in window)).toBe(false);
});

test("Plain-language sections preserve evidence and expose technical details on demand", async ({
  page,
}) => {
  await page.goto("/");
  const answer = page.locator('[data-section="01-answer"]');
  await expect(answer).toContainText("Biggest fixable complaint:");
  await expect(answer.getByRole("link")).toHaveAttribute("href", "#memo");
  await expect(page.locator(".kpis > div")).toHaveCount(2);
  await expect(page.locator(".kpis")).toContainText("237,722 (36%)");
  await expect(page.locator(".kpis")).toContainText("77,874 unique texts");
  await expect(page.locator(".kpis")).toContainText("159,848 identical copies");
  await expect(page.locator(".kpis")).toContainText("70,239");
  await expect(page.locator(".watch-list")).toContainText(
    "31 reviews, average severity 4.81",
  );
  await expect(page.locator(".watch-list")).toContainText("3.93");
  await expect(page.locator("#examples > p")).toHaveText(
    "Free-tier playback controls locked behind Premium",
  );
  for (const id of await page.locator("#examples cite").allTextContents())
    expect(id).toMatch(/^[a-f0-9]{8}$/);
  const human = page.getByRole("table", {
    name: "Human-label agreement by field",
  });
  for (const [field, value] of [
    ["Topic", "74% (37/50)"],
    ["Intent", "84% (42/50)"],
    ["Severity — exact", "72% (36/50)"],
    ["Severity — within one level", "96% (48/50)"],
    ["Sentiment", "82% (41/50)"],
  ]) {
    await expect(
      human.getByRole("row").filter({
        has: page.getByRole("rowheader", { name: field, exact: true }),
      }),
    ).toContainText(value);
  }
  await expect(page.locator(".claim-reference").first()).toBeVisible();
  await expect(page.locator(".claim-reference a").first()).toHaveAttribute(
    "href",
    /\/api\/claims\?scope=/,
  );
  const method = page.locator("#methodology");
  expect(await method.getAttribute("open")).toBeNull();
  await expect(
    page.getByText("Cache alias", { exact: true }),
  ).not.toBeVisible();
  await method.locator(":scope > summary").click();
  await expect(page.getByText("Cache alias", { exact: true })).toBeVisible();
  await expect(method).toContainText("not provider prompt caching");
});

test("Capture every revised section for owner review", async ({ page }) => {
  await page.goto("/");
  await expect(page.locator('[data-section="10-quality"]')).toBeVisible();
  mkdirSync("test-results/sections", { recursive: true });
  const names = await page
    .locator("[data-section]")
    .evaluateAll((nodes) => nodes.map((n) => n.getAttribute("data-section")!));
  expect(names).toHaveLength(12);
  for (const name of names)
    await page
      .locator(`[data-section="${name}"]`)
      .screenshot({ path: `test-results/sections/${name}.png` });
  await page.locator("#methodology > summary").click();
  await page
    .locator('[data-section="12-methodology"]')
    .screenshot({ path: "test-results/sections/13-methodology-expanded.png" });
  const images = [...names, "13-methodology-expanded"];
  writeFileSync(
    "test-results/sections/index.html",
    `<!doctype html><meta charset="utf-8"><title>Dashboard section screenshots</title><style>body{font:16px Arial;background:#f5f6f2;margin:24px}section{margin:36px auto;max-width:1200px}img{width:100%;border:1px solid #ccc}a{color:#245e3f}</style><h1>Dashboard copy and layout review</h1>${images.map((n) => `<section><h2>${n}</h2><a href="${n}.png"><img src="${n}.png" alt="${n}"></a></section>`).join("")}`,
  );
});

test("Approved fixes: one memo link, exact label-guide scale and collapsed readable methodology at phone width", async ({
  page,
}) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/");
  await expect(
    page.getByRole("link", { name: /Read the full product memo/ }),
  ).toHaveCount(1);
  const guide = readFileSync("../docs/labels.md", "utf8")
    .split(
      "## Severity (supported impact, independent of intent and sentiment)",
    )[1]
    .split("Missing context")[0];
  const levels = guide
    .replace(/\r?\n(?=   )/g, " ")
    .split(/\r?\n/)
    .filter((line) => /^\d\./.test(line))
    .map((line) =>
      line
        .replace(/^\d\. /, "")
        .replace(/\s+/g, " ")
        .trim(),
    );
  expect(levels).toHaveLength(5);
  const shown = await page.locator(".severity-legend li").allTextContents();
  expect(shown.map((line) => line.replace(/\s+/g, " ").trim())).toEqual(levels);
  const method = page.locator("#methodology");
  for (const details of await method.locator("..").locator("details").all())
    expect(await details.getAttribute("open")).toBeNull();
  await method.locator(":scope > summary").click();
  const split = method
    .locator("details")
    .filter({
      has: page
        .locator("summary")
        .filter({ hasText: "Verifier agreement by flag and fallback split" }),
    });
  await split.locator("summary").click();
  await expect(split.getByRole("table")).toBeVisible();
  await expect(split.locator("pre")).toHaveCount(0);
  await expect(
    split.getByRole("columnheader", { name: /With fallback/ }),
  ).toBeVisible();
  await method
    .locator("summary")
    .filter({ hasText: "Group-call outputs" })
    .click();
  await expect(
    method.getByText(
      "Display names were finalized by the owner; the model's proposed names are shown here.",
      { exact: true },
    ),
  ).toBeVisible();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
  await page.screenshot({
    path: "test-results/dashboard-phone-methodology.png",
    fullPage: true,
  });
});
