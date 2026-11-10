// EV02: run only against an isolated fixture database, never the presentation server.
import assert from "node:assert/strict";
import fs from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { createRequire } from "node:module";
import { randomUUID } from "node:crypto";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");
const require = createRequire(path.join(root, "test/browser/package.json"));
const { chromium, expect } = require("@playwright/test");
const AxeBuilder = require("@axe-core/playwright").default;
const base = new URL(process.env.BASE_URL || "http://127.0.0.1:8082");
assert(["127.0.0.1", "localhost", "[::1]"].includes(base.hostname), "Use a loopback fixture server");
assert(base.port && !["8080", "8081"].includes(base.port), "Do not run on the presentation or legacy server");
const phase = process.env.PHASE || `ev02-ui-${new Date().toISOString().replace(/[^0-9]/g, "")}`;
assert(/^[a-z0-9-]+$/.test(phase), "Use a unique lowercase measurement name");
const out = path.join(root, "artifacts/browser", phase);
await fs.mkdir(path.dirname(out), { recursive: true });
await fs.mkdir(out, { recursive: false });
const report = {
  checkedAt: new Date().toISOString(), base: base.origin, phase,
  checks: [], accessibility: [], errors: [], externalRequests: [], cleanup: [], passed: false,
  limits: ["Synthetic aoi/forest fixtures and one newly registered password-test account only", "Root font-size 200% is text scaling, not a browser-zoom certification", "Japanese typeahead uses an injected Unicode keydown; real IME interaction is not covered", "Browser checks are not measured user satisfaction or actual revisit effects"],
};
const sessions = new Map();
let currentStep = "setup";
let fixturePlan;
let forestProvider;
let originalResume;
let originalForestResume;
let releaseOldReference;
const passwords = ["aoi-local-2026", "forest-local-2026"];

async function api(user, route, method = "GET", body) {
  const session = sessions.get(user);
  const response = await fetch(new URL(`/api${route}`, base), {
    method,
    headers: {
      Origin: base.origin, "Content-Type": "application/json",
      ...(session ? { Authorization: `Bearer ${session.access_token}`, "X-CSRF-Token": session.csrf_token } : {}),
    },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  assert(response.ok, `Fixture API failed: ${method} ${route.split("?")[0]} ${response.status}`);
  return response.json();
}

async function step(name, action) {
  currentStep = name;
  const scansBefore = report.accessibility.length;
  await action();
  const status = report.accessibility.slice(scansBefore).some((scan) => scan.violations.length) ? "fail" : "pass";
  report.checks.push({ name, status });
  console.log(`${status.toUpperCase()} ${name}`);
}

const browser = await chromium.launch({ channel: process.env.BROWSER_CHANNEL || "msedge", headless: true });
const context = await browser.newContext({ viewport: { width: 1440, height: 900 }, locale: "ja-JP", timezoneId: "Asia/Tokyo" });
await context.route("**/*", async (route) => {
  const url = new URL(route.request().url());
  if (["data:", "blob:"].includes(url.protocol) || url.origin === base.origin) await route.continue();
  else {
    report.externalRequests.push({ origin: url.origin, type: route.request().resourceType() });
    await route.abort();
  }
});
context.on("page", (page) => page.on("pageerror", (error) => report.errors.push({ step: currentStep, name: error.name })));
const stage = await context.newPage();
const visitor = stage.frameLocator('iframe[title="利用者のスマートフォン画面"]');
const provider = stage.frameLocator('iframe[title="事業者のパソコン管理画面"]');

async function login(scope, user, password = `${user}-local-2026`) {
  await scope.getByLabel("アカウント名", { exact: true }).fill(user);
  await scope.getByLabel("パスワード", { exact: true }).fill(password);
  await scope.getByLabel("パスワード", { exact: true }).press("Enter");
  await expect(scope.locator(".app-shell")).toBeVisible();
}

async function noOverflow(scope) {
  const dimensions = await scope.locator("html").evaluate((element) => ({ width: innerWidth, content: element.scrollWidth }));
  assert(dimensions.content <= dimensions.width + 1, `Horizontal overflow: ${dimensions.content}/${dimensions.width}`);
}

async function scan(page, name) {
  const results = await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa", "wcag21aa", "wcag22aa"]).analyze();
  const violations = results.violations.map((item) => ({ id: item.id, impact: item.impact, targets: item.nodes.map((node) => node.target), checks: item.nodes.map((node) => node.any.map((check) => ({ id: check.id, data: check.data }))) }));
  report.accessibility.push({ name, violations });
}

function planBody(plan, patch = {}) {
  const fields = ["title", "summary", "area", "min_people", "max_people", "nights", "price_yen", "price_basis", "price_scope", "price_note", "tags", "itinerary", "status", "version", "schedule_type", "starts_at", "ends_at"];
  return { ...Object.fromEntries(fields.map((field) => [field, plan[field]])), ...patch };
}

async function openFixtureEditor() {
  await provider.locator(".provider-workspace-nav").getByRole("button", { name: "プラン", exact: true }).click();
  await provider.getByRole("group", { name: "プランの公開状態" }).getByRole("button", { name: /^下書き/ }).click();
  const card = provider.locator(".market-plan-card").filter({ hasText: fixturePlan.title });
  await card.getByRole("button", { name: "プランを編集する", exact: true }).click();
  const editor = provider.getByRole("dialog", { name: "プランを編集する", exact: true });
  await expect(editor).toBeVisible();
  return editor;
}

try {
  for (const user of ["aoi", "forest"]) sessions.set(user, await api(user, "/stage/login", "POST", { username: user, password: `${user}-local-2026` }));
  originalResume = await api("aoi", "/me/resume-state");
  await api("aoi", "/me/resume-state", "PUT", { ...originalResume, page: "market", community_id: "peers", circle_id: null, filters: { query: "", category: "", duration: "all", schedule: "all", area: "" } });
  originalForestResume = await api("forest", "/me/resume-state");
  await api("forest", "/me/resume-state", "PUT", { ...originalForestResume, page: "provider" });
  const capabilities = await api("forest", "/marketplace/capabilities");
  forestProvider = capabilities.providers[0];
  assert(forestProvider, "Isolated forest provider fixture is required");
  fixturePlan = await api("forest", `/providers/${forestProvider.id}/plans`, "POST", {
    title: `画面評価用 ${phase}`, summary: "隔離した画面試験用のプラン", area: "N西市", min_people: 2, max_people: 6,
    nights: 0, price_yen: 4500, price_basis: "per_person", price_scope: "plan_only", price_note: "体験料のみ。交通費は含みません。",
    tags: ["nature"], itinerary: [{ day: 1, period: "afternoon", place: "画面評価用の集合場所", description: "表示と入力を確認", travel_minutes: null }],
    status: "draft", version: 0, schedule_type: "on_request", starts_at: null, ends_at: null,
  });

  await step("stage-independent-login-and-desktop-layout", async () => {
    await stage.goto(new URL("/stage", base).href);
    await login(visitor, "aoi");
    await expect(provider.getByRole("button", { name: "ログイン", exact: true })).toBeVisible();
    await login(provider, "forest");
    await expect(provider.locator(".provider-workspace")).toBeVisible();
    await expect(visitor.getByRole("searchbox", { name: "取得した候補を場所・プラン名で絞り込む" })).toBeVisible();
    await noOverflow(stage); await noOverflow(visitor); await noOverflow(provider);
    const bounds = await stage.locator(".desktop-frame").boundingBox();
    assert(bounds && bounds.width > bounds.height, "Provider should use the wide PC frame");
    await scan(stage, "stage-1440x900");
    await stage.screenshot({ path: path.join(out, "stage.png") });
  });

  await step("choice-keyboard-label-and-focus", async () => {
    await visitor.getByRole("button", { name: /^絞り込み/ }).click();
    const modal = visitor.getByRole("dialog", { name: "候補を絞り込む" });
    const duration = modal.getByRole("button", { name: "所要日数", exact: true });
    const schedule = modal.getByRole("button", { name: "開催日程", exact: true });
    await duration.focus(); await duration.press("ArrowDown");
    const list = modal.getByRole("listbox", { name: "所要日数の選択肢" });
    await expect(list).toBeVisible();
    await expect(list.getByRole("option", { name: "すべて", exact: true })).toBeFocused();
    await list.getByRole("option", { name: "すべて", exact: true }).press("End");
    await expect(list.getByRole("option", { name: "宿泊を含む", exact: true })).toBeFocused();
    await list.getByRole("option", { name: "宿泊を含む", exact: true }).press("Home");
    await expect(list.getByRole("option", { name: "すべて", exact: true })).toBeFocused();
    await list.getByRole("option", { name: "すべて", exact: true }).evaluate((node) => {
      node.dispatchEvent(new KeyboardEvent("keydown", { key: "日", bubbles: true, cancelable: true }));
    });
    await expect(list.getByRole("option", { name: "日帰り", exact: true })).toBeFocused();
    await list.getByRole("option", { name: "日帰り", exact: true }).press("Escape");
    await expect(duration).toBeFocused(); await expect(list).toBeHidden();
    await duration.press("ArrowDown"); await list.getByRole("option", { name: "すべて", exact: true }).press("Tab");
    await expect(schedule).toBeFocused(); await expect(list).toBeHidden();
    await schedule.press("ArrowDown");
    await modal.getByRole("listbox", { name: "開催日程の選択肢" }).getByRole("option", { name: "すべて", exact: true }).press("Shift+Tab");
    await expect(duration).toBeFocused();
    const focusStyle = await duration.evaluate((node) => ({ style: getComputedStyle(node).outlineStyle, width: parseFloat(getComputedStyle(node).outlineWidth) }));
    assert(focusStyle.style !== "none" && focusStyle.width > 0, "Keyboard focus should remain visible");
    await modal.getByRole("button", { name: "閉じる", exact: true }).click();
  });

  await step("provider-unsaved-change-confirmation", async () => {
    let editor = await openFixtureEditor();
    const changedTitle = `${fixturePlan.title} 変更`;
    await editor.getByLabel("プランの名前", { exact: true }).fill(changedTitle);
    await editor.getByLabel("プランの名前", { exact: true }).press("Escape");
    const confirm = provider.getByRole("dialog", { name: "保存せずに閉じますか？", exact: true });
    await expect(confirm).toBeVisible();
    await confirm.getByRole("button", { name: "編集を続ける", exact: true }).press("Escape");
    await expect(confirm).toBeHidden();
    await expect(editor.getByLabel("プランの名前", { exact: true })).toHaveValue(changedTitle);
    await editor.getByRole("button", { name: "閉じる", exact: true }).click();
    await confirm.getByRole("button", { name: "編集を続ける", exact: true }).click();
    await expect(editor.getByLabel("プランの名前", { exact: true })).toHaveValue(changedTitle);
    await editor.getByRole("button", { name: "閉じる", exact: true }).click();
    await confirm.getByRole("button", { name: "変更を破棄して閉じる", exact: true }).click();
    await expect(editor).toBeHidden();
    editor = await openFixtureEditor();
    await expect(editor.getByLabel("プランの名前", { exact: true })).toHaveValue(fixturePlan.title);
    await editor.getByLabel("プランの名前", { exact: true }).fill(changedTitle);
    await editor.getByRole("button", { name: "下書きに保存", exact: true }).click();
    await expect(editor).toBeHidden(); await expect(confirm).toBeHidden();
    const saved = (await api("forest", `/provider-plans?provider_id=${encodeURIComponent(forestProvider.id)}&mine=true`)).items.find((item) => item.id === fixturePlan.id);
    assert.equal(saved.title, changedTitle); fixturePlan = saved;
  });

  await step("old-provider-reference-does-not-reappear", async () => {
    const cards = visitor.locator(".plan-discovery .market-plan-card");
    await expect(cards.first()).toBeVisible();
    const publicPlans = (await api("aoi", "/provider-plans")).items;
    const first = publicPlans[0];
    const second = publicPlans.find((plan) => plan.provider.id !== first?.provider.id);
    assert(first && second, "At least two providers are required in the fixture catalog");
    const summary = await api("aoi", `/providers/${first.provider.id}/experience-summary`);
    const marker = "EV02_OLD_PROVIDER_RESULT";
    let intercepted;
    const interceptedPromise = new Promise((resolve) => { intercepted = resolve; });
    const release = new Promise((resolve) => { releaseOldReference = resolve; });
    const routePath = `**/api/providers/${first.provider.id}/experience-summary`;
    await context.route(routePath, async (route) => {
      intercepted(); await release;
      await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ ...summary, note: marker }) }).catch(() => undefined);
    });
    const open = async (plan) => {
      await visitor.getByRole("searchbox", { name: "取得した候補を場所・プラン名で絞り込む" }).fill(plan.title);
      await cards.filter({ hasText: plan.title }).getByRole("button", { name: "日別の行程を見る", exact: true }).click();
      const detail = visitor.getByRole("dialog", { name: "プランの行程と費用" });
      await detail.locator(".plan-reference-details > summary").click();
      return detail;
    };
    const firstDetail = await open(first);
    await Promise.race([interceptedPromise, new Promise((_, reject) => setTimeout(() => reject(new Error("Reference request was not intercepted")), 10000))]);
    await firstDetail.getByRole("button", { name: "閉じる", exact: true }).click();
    const secondDetail = await open(second);
    releaseOldReference();
    await expect(secondDetail.locator(".experience-reference")).toBeVisible();
    await expect(secondDetail).not.toContainText(marker);
    await context.unroute(routePath);
    await secondDetail.getByRole("button", { name: "閉じる", exact: true }).click();
    await visitor.getByRole("searchbox", { name: "取得した候補を場所・プラン名で絞り込む" }).fill("");
  });

  const mobile = await context.newPage();
  await mobile.setViewportSize({ width: 390, height: 844 });
  await mobile.goto(new URL("/stage/visitor", base).href); await login(mobile, "aoi");
  await expect(mobile.locator(".discovery-results")).toBeVisible();
  for (const width of [390, 320]) {
    await step(`traveler-${width}px`, async () => {
      await mobile.setViewportSize({ width, height: 844 });
      const planButton = mobile.getByRole("button", { name: "旅を計画", exact: true });
      await planButton.click();
      const newTrip = mobile.getByRole("dialog", { name: "新しい旅を計画する", exact: true });
      await expect(newTrip).toBeVisible();
      await newTrip.getByRole("button", { name: "閉じる", exact: true }).click();
      await noOverflow(mobile); await scan(mobile, `traveler-${width}px`);
      await mobile.screenshot({ path: path.join(out, `traveler-${width}.png`), fullPage: true });
    });
  }
  await step("traveler-text-200-percent", async () => {
    await mobile.evaluate(() => { const html = document.documentElement; html.style.fontSize = `${parseFloat(getComputedStyle(html).fontSize) * 2}px`; });
    await noOverflow(mobile);
    await mobile.getByRole("button", { name: /^絞り込み/ }).click();
    await expect(mobile.getByRole("dialog", { name: "候補を絞り込む" })).toBeVisible();
    await noOverflow(mobile); await scan(mobile, "traveler-320px-root-font-200-percent");
    await mobile.screenshot({ path: path.join(out, "traveler-text-200.png"), fullPage: true });
    await mobile.getByRole("dialog").getByRole("button", { name: "閉じる", exact: true }).click();
    await mobile.evaluate(() => document.documentElement.style.removeProperty("font-size"));
  });
  await step("reduced-motion-and-runtime-boundaries", async () => {
    await mobile.emulateMedia({ reducedMotion: "reduce" });
    await mobile.getByRole("button", { name: "日帰りの講", exact: true }).last().click();
    await expect(mobile.getByRole("heading", { name: "日帰りを探す", exact: true })).toBeVisible();
    await expect(mobile.locator("#main")).toHaveAttribute("data-motion-state", "idle");
    assert.equal(await mobile.locator("select").count(), 0, "The required custom choices must remain in use");
    assert.equal(report.errors.length, 0, "Unexpected browser runtime error");
    assert.equal(report.externalRequests.length, 0, "Unexpected external request");
  });
  await step("password-change-validation-and-session-revocation", async () => {
    const username = `ev02_pw_${randomUUID().replaceAll("-", "").slice(0, 18)}`;
    const oldPassword = `Initial-${randomUUID()}${"😀".repeat(80)}`;
    const nextPassword = `Changed-${randomUUID()}${"🗺".repeat(80)}`;
    const wrongPassword = `Wrong-${randomUUID()}`;
    const tooShort = "😀".repeat(6);
    const tooLong = "a".repeat(129);
    passwords.push(oldPassword, nextPassword, wrongPassword, tooShort, tooLong);
    const registrationPage = await context.newPage();
    await registrationPage.goto(new URL("/stage/visitor", base).href);
    await registrationPage.getByRole("button", { name: "アカウントを作る", exact: true }).click();
    await registrationPage.getByLabel("表示名", { exact: true }).fill("画面評価用");
    await registrationPage.locator("#register-username").fill(username);
    await registrationPage.locator("#register-password").fill(tooShort);
    await registrationPage.locator("#register-confirmation").fill(tooShort);
    await registrationPage.getByRole("checkbox", { name: /一覧にないため、地域を登録せずに続ける/ }).check();
    await expect(registrationPage.getByRole("button", { name: "登録してはじめる", exact: true })).toBeDisabled();
    await registrationPage.locator("#register-password").fill(oldPassword);
    await registrationPage.locator("#register-confirmation").fill(oldPassword);
    await registrationPage.getByRole("button", { name: "登録してはじめる", exact: true }).click();
    await expect(registrationPage.locator(".app-shell")).toBeVisible();
    await registrationPage.close();
    const oldSession = await api(undefined, "/stage/login", "POST", { username, password: oldPassword });
    report.cleanup.push("new password-test account kept only in isolated disposable database");
    const accountPage = await context.newPage();
    await accountPage.setViewportSize({ width: 390, height: 844 });
    await accountPage.goto(new URL("/stage/visitor", base).href);
    await login(accountPage, username, oldPassword);
    await accountPage.getByRole("button", { name: "画面評価用 アカウントを切り替える", exact: true }).click();
    await accountPage.getByRole("dialog", { name: "アカウントを切り替える", exact: true }).getByRole("button", { name: "パスワードを変更する", exact: true }).click();
    const form = accountPage.getByRole("dialog", { name: "パスワードを変更する", exact: true });
    await form.getByRole("button", { name: "閉じる", exact: true }).press("Escape");
    await expect(form).toBeHidden();
    const accountDialog = accountPage.getByRole("dialog", { name: "アカウントを切り替える", exact: true });
    await expect(accountDialog).toBeVisible();
    await expect(accountDialog.getByRole("button", { name: "パスワードを変更する", exact: true })).toBeFocused();
    await accountDialog.getByRole("button", { name: "パスワードを変更する", exact: true }).click();
    const current = form.getByLabel("現在のパスワード", { exact: true });
    const next = form.getByLabel("新しいパスワード", { exact: true });
    const confirmation = form.getByLabel("新しいパスワードの確認", { exact: true });
    const save = form.getByRole("button", { name: "パスワードを変更する", exact: true });
    await current.fill(oldPassword); await next.fill(tooShort); await confirmation.fill(tooShort);
    await save.click();
    await expect(next).toBeFocused(); await expect(next).toHaveAttribute("aria-invalid", "true");
    await expect(form.getByRole("alert")).toContainText("12〜128文字");
    await next.fill(tooLong); await confirmation.fill(tooLong); await save.click();
    await expect(next).toHaveAttribute("aria-invalid", "true");
    await current.fill(oldPassword); await next.fill(nextPassword); await confirmation.fill(wrongPassword);
    await save.click();
    await expect(confirmation).toBeFocused(); await expect(confirmation).toHaveAttribute("aria-invalid", "true");
    await expect(form.getByRole("alert")).toContainText("一致しません");
    await current.fill(wrongPassword); await confirmation.fill(nextPassword);
    const rejected = accountPage.waitForResponse((response) => response.url().endsWith("/api/account/password") && response.request().method() === "POST");
    await save.click(); assert.equal((await rejected).status(), 422);
    await expect(form.getByRole("alert")).toBeVisible();
    await expect(form.getByRole("alert")).toBeFocused();
    await current.fill(oldPassword);
    await noOverflow(accountPage); await scan(accountPage, "password-change-390px");
    const accepted = accountPage.waitForResponse((response) => response.url().endsWith("/api/account/password") && response.request().method() === "POST");
    await save.click(); assert.equal((await accepted).status(), 200);
    await expect(accountPage.getByRole("button", { name: "ログイン", exact: true })).toBeVisible();
    await expect(accountPage.getByText("パスワードを変更しました。もう一度ログインしてください。", { exact: true })).toBeVisible();
    await expect(accountPage.getByLabel("パスワード", { exact: true })).toHaveValue("");
    const revoked = await fetch(new URL("/api/me", base), { headers: { Authorization: `Bearer ${oldSession.access_token}` } });
    assert.equal(revoked.status, 401, "The same user's previous Stage session should be revoked");
    await api("forest", "/me");
    await login(accountPage, username, nextPassword);
    const stored = await accountPage.evaluate(() => JSON.stringify({ local: { ...localStorage }, session: { ...sessionStorage } }));
    assert(!passwords.some((password) => stored.includes(password)), "Passwords must not be persisted in browser storage");
    await accountPage.close();
    assert.equal(report.errors.length, 0, "Unexpected browser runtime error");
    assert.equal(report.externalRequests.length, 0, "Unexpected external request");
  });
  assert(report.accessibility.every((scan) => scan.violations.length === 0), "Accessibility violations remain; see recorded scans");
  report.passed = true;
} catch (error) {
  report.checks.push({ name: currentStep, status: "fail" });
  const message = passwords.reduce((text, password) => text.replaceAll(password, "[redacted]"), String(error.message)).slice(0, 1200);
  report.failure = { name: error.name, message };
  process.exitCode = 1;
} finally {
  releaseOldReference?.();
  await context.close();
  await browser.close();
  if (fixturePlan && forestProvider) {
    try {
      const current = (await api("forest", `/provider-plans?provider_id=${encodeURIComponent(forestProvider.id)}&mine=true`)).items.find((item) => item.id === fixturePlan.id);
      await api("forest", `/provider-plans/${fixturePlan.id}`, "PATCH", planBody(current, { status: "archived" }));
      report.cleanup.push("isolated test plan archived");
    } catch { report.cleanup.push("test plan archival failed"); report.passed = false; process.exitCode = 1; }
  }
  if (originalResume) {
    try {
      const current = await api("aoi", "/me/resume-state");
      await api("aoi", "/me/resume-state", "PUT", { ...originalResume, version: current.version });
      report.cleanup.push("isolated traveler resume restored");
    } catch { report.cleanup.push("resume restore failed"); report.passed = false; process.exitCode = 1; }
  }
  if (originalForestResume) {
    try {
      const current = await api("forest", "/me/resume-state");
      await api("forest", "/me/resume-state", "PUT", { ...originalForestResume, version: current.version });
      report.cleanup.push("isolated provider resume restored");
    } catch { report.cleanup.push("provider resume restore failed"); report.passed = false; process.exitCode = 1; }
  }
  await fs.writeFile(path.join(out, "results.json"), JSON.stringify(report, null, 2) + "\n");
  console.log(JSON.stringify({ phase, passed: report.passed, checks: report.checks.length, failure: report.failure?.name }));
}
