import { test, expect } from "@playwright/test";

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
    "36.0% coverage",
  );
  await expect(page.getByLabel("Partial scope disclosure")).toContainText(
    "422,845",
  );
  const row = page
    .getByRole("row")
    .filter({
      has: page.getByRole("button", {
        name: "Free-tier playback controls locked behind Premium",
        exact: true,
      }),
    });
  await expect(row).toContainText("4,444");
  await page
    .getByRole("button", { name: "Random prefix only", exact: true })
    .click();
  await expect(row).toContainText("4,440");
  await expect(row).toContainText("13,865");
  await page
    .getByRole("button", { name: "Propagated baseline", exact: true })
    .click();
  await page.getByLabel("Search issues").fill("ads");
  await expect(page.getByText("1 of 35 issues")).toBeVisible();
  await page.getByLabel("Search issues").fill("zzzzzz");
  await expect(
    page.getByText("No issues match this search.", { exact: false }),
  ).toBeVisible();
  await page.getByLabel("Search issues").fill("");
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
    page.getByRole("heading", { name: "Issue ranking", exact: true }),
  ).toBeVisible();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBe(true);
  const button = page.getByRole("button", {
    name: "Random prefix only",
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
    page.getByRole("heading", { name: "Issue ranking", exact: true }),
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
