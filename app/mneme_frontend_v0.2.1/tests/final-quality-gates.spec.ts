import { expect, test, type Locator, type Page, type Route } from "@playwright/test";
import { mkdir, readFile, readdir, rm } from "node:fs/promises";
import path from "node:path";
import { getDocumentAction, openView } from "./helpers/navigation";

const auditDirectory = path.resolve("../../.tmp/final-quality-matrix");
const envelope = (data: unknown) => ({ code: 0, message: "ok", data });

test.describe.configure({ mode: "serial" });

async function expectNoHorizontalOverflow(page: Page) {
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth + 1)).toBe(true);
}

async function expectKeySurfacesInViewport(page: Page) {
  const violations = await page.evaluate(() => {
    const selectors = [
      "main",
      '[role="main"]',
      '[role="dialog"]',
      '[data-testid$="-layout"]',
      ".graph-toolbar",
      ".zoom-controls",
      ".document-actions",
      ".memory-center",
    ];
    return [...document.querySelectorAll<HTMLElement>(selectors.join(","))]
      .filter((element) => {
        const style = getComputedStyle(element);
        const rect = element.getBoundingClientRect();
        return style.visibility !== "hidden" && style.display !== "none" && rect.width > 0 && rect.height > 0;
      })
      .map((element) => {
        const rect = element.getBoundingClientRect();
        return {
          selector: element.dataset.testid || element.className || element.tagName,
          left: Math.round(rect.left),
          right: Math.round(rect.right),
          ancestors: [...function* ancestors() {
            let current = element.parentElement;
            while (current && current !== document.body) {
              const currentRect = current.getBoundingClientRect();
              yield {
                selector: current.dataset.testid || current.className || current.tagName,
                left: Math.round(currentRect.left),
                right: Math.round(currentRect.right),
                transform: getComputedStyle(current).transform,
              };
              current = current.parentElement;
            }
          }()].slice(0, 6),
        };
      })
      .filter(({ left, right }) => left < -1 || right > window.innerWidth + 1);
  });
  expect(violations).toEqual([]);
}

type VisualRecord = {
  name: string;
  width: number;
  height: number;
  theme: "light" | "dark";
};

async function capture(page: Page, name: string, records: VisualRecord[], theme: "light" | "dark") {
  await expectNoHorizontalOverflow(page);
  await expectKeySurfacesInViewport(page);
  const viewport = page.viewportSize();
  expect(viewport).not.toBeNull();
  await page.screenshot({ path: path.join(auditDirectory, `${name}.png`), animations: "disabled" });
  records.push({ name, width: viewport!.width, height: viewport!.height, theme });
}

async function setWorkspaceValue(page: Page, pathSegments: string[], value: unknown) {
  return page.evaluate(({ pathSegments, value }) => {
    const host = document.querySelector("#root") as HTMLElement & {
      __vue_app__?: { _instance?: { setupState?: Record<string, unknown> } };
    };
    const setupState = host.__vue_app__?._instance?.setupState;
    let owner = setupState?.workspace as Record<string, unknown> | undefined;
    if (!owner) return false;
    for (const segment of pathSegments.slice(0, -1)) {
      owner = owner?.[segment] as Record<string, unknown> | undefined;
      if (!owner) return false;
    }
    const key = pathSegments.at(-1);
    if (!key) return false;
    const current = owner[key] as { value?: unknown } | undefined;
    if (current && typeof current === "object" && "value" in current) current.value = value;
    else owner[key] = value;
    return true;
  }, { pathSegments, value });
}

async function installPacedPreviewStream(page: Page, intervalMs: number) {
  await page.evaluate(async (pace) => {
    const importModule = (modulePath: string) => import(/* @vite-ignore */ modulePath);
    const { api } = await importModule("/src/lib/api.ts");
    api.streamChatSessionMessage = async (
      token: string,
      sessionId: string,
      payload: { question: string; answer_mode: string; execution_mode?: "single" | "multi"; top_k?: number },
      onEvent: (event: Record<string, unknown>) => void,
    ) => {
      onEvent({ type: "lifecycle", name: "run.started", phase: "started" });
      onEvent({ type: "lifecycle", name: "retrieval.started", phase: "retrieve" });
      const detail = await api.sendChatSessionMessage(token, sessionId, payload);
      const answer = detail.messages.find((item: { role: string }) => item.role === "assistant")?.content ?? "";
      onEvent({
        type: "lifecycle",
        name: "retrieval.source_completed",
        phase: "retrieve",
        metadata: { source_type: "document", result_count: 2 },
      });
      onEvent({
        type: "lifecycle",
        name: "evidence.selected",
        phase: "retrieve",
        metadata: { evidence_count: 2, source_counts: { document: 2 } },
      });
      onEvent({ type: "lifecycle", name: "answer.started", phase: "answer" });
      for (const character of answer) {
        onEvent({ type: "assistant", name: "answer.delta", content: character });
        await new Promise((resolve) => window.setTimeout(resolve, pace));
      }
      onEvent({ type: "lifecycle", name: "answer.completed", phase: "completed" });
    };
  }, intervalMs);
}

async function openVaultTree(page: Page) {
  await openView(page, "Research Vault");
  const tree = page.getByTestId("document-tree-pane");
  if (!(await tree.isVisible())) await page.getByRole("button", { name: "Files", exact: true }).click();
  await expect(tree).toBeVisible();
  return tree;
}

async function routeKeyboardLogin(route: Route) {
  const pathname = new URL(route.request().url()).pathname;
  if (pathname === "/auth/login") {
    await route.fulfill({ json: envelope({ access_token: "token-keyboard", token_type: "bearer" }) });
    return;
  }
  if (pathname === "/auth/me") {
    await route.fulfill({ json: envelope({ id: 31, username: "keyboard-user", display_name: "Keyboard User", avatar_url: "" }) });
    return;
  }
  if (pathname === "/health") {
    await route.fulfill({ json: envelope({ service: "mneme", status: "running" }) });
    return;
  }
  if (pathname === "/health/neo4j") {
    await route.fulfill({ json: envelope({ enabled: true, backend: "neo4j", database: "neo4j", uri: "bolt://neo4j:7687", ok: true, error: null }) });
    return;
  }
  if (pathname === "/health/readiness") {
    await route.fulfill({ json: envelope({ overall_status: "ready", checks: [], framework_decisions: [], default_stack: [], optional_stack: [], avoid_by_default: [], markdown: "" }) });
    return;
  }
  if (pathname === "/users/31/knowledge-bases") {
    await route.fulfill({ json: envelope({ items: [], total: 0 }) });
    return;
  }
  if (pathname === "/ai/model-configs") {
    await route.fulfill({ json: envelope({ provider_presets: [], items: [], default_config_id: null }) });
    return;
  }
  await route.fulfill({ status: 404, json: { detail: `Unexpected quality-gate request: ${pathname}` } });
}

async function tabTo(page: Page, target: Locator, maxTabs = 100) {
  for (let index = 0; index < maxTabs; index += 1) {
    if (await target.evaluate((element) => element === document.activeElement).catch(() => false)) return;
    await page.keyboard.press("Tab");
  }
  throw new Error(`Keyboard focus did not reach ${await target.evaluate((element) => element.outerHTML).catch(() => "target")}`);
}

async function expectVisibleKeyboardFocus(target: Locator) {
  const presentation = await target.evaluate((element) => {
    const style = getComputedStyle(element);
    const parentStyle = element.parentElement ? getComputedStyle(element.parentElement) : null;
    const focusGraphic = element.querySelector<HTMLElement>("circle, input + span");
    const graphicStyle = focusGraphic ? getComputedStyle(focusGraphic) : null;
    return {
      focusVisible: element.matches(":focus-visible"),
      outline: style.outlineStyle !== "none" && parseFloat(style.outlineWidth) > 0,
      shadow: style.boxShadow !== "none",
      parentFocus: Boolean(
        parentStyle
        && (parentStyle.boxShadow !== "none"
          || (parentStyle.outlineStyle !== "none" && parseFloat(parentStyle.outlineWidth) > 0)),
      ),
      graphic: Boolean(
        graphicStyle
        && ((graphicStyle.stroke !== "none" && parseFloat(graphicStyle.strokeWidth) > 0)
          || graphicStyle.boxShadow !== "none"),
      ),
    };
  });
  expect(presentation.focusVisible).toBe(true);
  expect(presentation.outline || presentation.shadow || presentation.parentFocus || presentation.graphic).toBe(true);
}

test("light and dark visual matrix covers five target viewports and core states", async ({ page }, testInfo) => {
  test.skip(testInfo.project.name !== "Desktop Chrome", "The test sets all target viewports explicitly.");
  test.setTimeout(360_000);
  await rm(auditDirectory, { recursive: true, force: true });
  await mkdir(auditDirectory, { recursive: true });
  const visualRecords: VisualRecord[] = [];

  const viewports = [
    { name: "1440x900", width: 1440, height: 900 },
    { name: "1024x768", width: 1024, height: 768 },
    { name: "768x1024", width: 768, height: 1024 },
    { name: "390x844", width: 390, height: 844 },
    { name: "360x800", width: 360, height: 800 },
  ];

  for (const theme of ["light", "dark"] as const) {
    for (const viewport of viewports) {
      const prefix = `${theme}-${viewport.name}`;
      await page.setViewportSize(viewport);
      await page.goto("/");
      await page.evaluate((selectedTheme) => {
        localStorage.clear();
        localStorage.setItem("mneme.theme", selectedTheme);
      }, theme);
      await page.reload({ waitUntil: "domcontentloaded" });
      await expect(page.locator("html")).toHaveAttribute("data-theme", theme);
      await expect(page.getByRole("heading", { name: "Welcome to Mneme" })).toBeVisible();
      await capture(page, `${prefix}-login`, visualRecords, theme);

      await page.goto("/?preview=1", { waitUntil: "domcontentloaded" });
      await expect(page.locator("html")).toHaveAttribute("data-theme", theme);
      await expect(page.getByTestId("stitch-graph-layout")).toBeVisible();
      await capture(page, `${prefix}-graph-content`, visualRecords, theme);

      expect(await setWorkspaceValue(page, ["graphData"], { nodes: [], edges: [] })).toBe(true);
      await expect(page.getByText("No graph nodes yet", { exact: true })).toBeVisible();
      await capture(page, `${prefix}-graph-empty`, visualRecords, theme);

      await page.reload({ waitUntil: "domcontentloaded" });
      await openView(page, "Semantic Map");
      await expect(page.getByTestId("dashboard-overview")).toBeVisible();
      await capture(page, `${prefix}-dashboard`, visualRecords, theme);

      await openVaultTree(page);
      if (viewport.width <= 1100) await page.keyboard.press("Escape");
      await expect(page.getByText("Open a source", { exact: true })).toBeVisible();
      await capture(page, `${prefix}-vault-empty`, visualRecords, theme);
      const tree = await openVaultTree(page);
      await tree.getByRole("button", { name: "zettelkasten-principles.md", exact: true }).click();
      await expect(page.getByTestId("document-reader-title")).toContainText("zettelkasten-principles.md");
      await capture(page, `${prefix}-vault-content`, visualRecords, theme);

      await openView(page, "AI Laboratory");
      await installPacedPreviewStream(page, 35);
      const history = page.getByTestId("ai-history-rail");
      if (!(await history.isVisible())) await page.getByTestId("ai-history-rail-toggle").click();
      await history.getByRole("button", { name: "New chat" }).click();
      await expect(page.getByText("Begin with a question", { exact: true })).toBeVisible();
      await capture(page, `${prefix}-ai-empty`, visualRecords, theme);
      const composer = page.getByTestId("workspace-chat-command");
      await composer.locator("textarea").fill("Summarize the current evidence");
      await composer.getByRole("button", { name: "Send message" }).click();
      await expect(page.getByTestId("agent-run-trace")).toHaveAttribute("aria-live", "polite");
      const visualStreamState = page.getByTestId("agent-run-trace").locator("header > span");
      await expect(visualStreamState).toHaveAttribute("data-state", "streaming");
      await page.waitForTimeout(250);
      await capture(page, `${prefix}-ai-stream`, visualRecords, theme);
      await expect(visualStreamState).toHaveAttribute("data-state", "completed", { timeout: 10_000 });

      await openView(page, /Memory Center/);
      await expect(page.getByRole("heading", { name: /Pending review/ })).toBeVisible();
      await capture(page, `${prefix}-memory-candidate`, visualRecords, theme);
      await page.evaluate(async () => {
        const importModule = (modulePath: string) => import(/* @vite-ignore */ modulePath);
        const { api } = await importModule("/src/lib/api.ts");
        api.listMemories = async () => ({ items: [], total: 0 });
        api.listMemoryCandidates = async () => ({ items: [], total: 0, pending_count: 0 });
      });
      await page.locator(".memory-center__header").getByRole("button", { name: "Refresh" }).click();
      await expect(page.getByText("No active memories", { exact: true })).toBeVisible();
      await capture(page, `${prefix}-memory-empty`, visualRecords, theme);

      await openView(page, "System Settings");
      await expect(page.getByTestId("stitch-settings-layout")).toBeVisible();
      await capture(page, `${prefix}-settings`, visualRecords, theme);
    }
  }

  const expectedFiles = visualRecords.map(({ name }) => `${name}.png`).sort();
  const actualFiles = (await readdir(auditDirectory)).filter((file) => file.endsWith(".png")).sort();
  expect(visualRecords).toHaveLength(110);
  expect(actualFiles).toEqual(expectedFiles);
  await testInfo.attach("visual-matrix-manifest", {
    body: Buffer.from(JSON.stringify({ generatedAt: new Date().toISOString(), screenshots: visualRecords }, null, 2)),
    contentType: "application/json",
  });
  for (const representative of [
    "light-1440x900-dashboard.png",
    "dark-1024x768-settings.png",
    "light-768x1024-vault-content.png",
    "dark-390x844-memory-candidate.png",
    "light-360x800-graph-empty.png",
  ]) {
    await testInfo.attach(`visual-${representative}`, {
      path: path.join(auditDirectory, representative),
      contentType: "image/png",
    });
  }
});

test("keyboard-only workflow preserves focus and semantic state", async ({ page }, testInfo) => {
  test.skip(testInfo.project.name !== "Desktop Chrome", "One desktop keyboard pass covers the shared semantics.");
  test.setTimeout(120_000);
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.route("http://127.0.0.1:8000/**", routeKeyboardLogin);
  await page.goto("/");

  const username = page.getByLabel("Username");
  await tabTo(page, username);
  await expectVisibleKeyboardFocus(username);
  await page.keyboard.type("keyboard-user");
  await page.keyboard.press("Tab");
  const password = page.getByLabel("Password", { exact: true });
  await expect(password).toBeFocused();
  await expectVisibleKeyboardFocus(password);
  await page.keyboard.type("password123");
  await page.keyboard.press("Enter");
  await expect(page.getByTestId("obsidian-shell")).toBeVisible();

  await page.unroute("http://127.0.0.1:8000/**");
  await page.goto("/?preview=1", { waitUntil: "domcontentloaded" });
  const settingsButton = page.getByTestId("activity-bar").getByRole("button", { name: "System Settings" });
  await tabTo(page, settingsButton);
  await expectVisibleKeyboardFocus(settingsButton);
  await page.keyboard.press("Enter");
  await expect(settingsButton).toHaveAttribute("aria-pressed", "true");

  const resourceToggle = page.getByRole("button", { name: "Toggle resources" });
  const wasExpanded = await resourceToggle.getAttribute("aria-expanded");
  await tabTo(page, resourceToggle);
  await expectVisibleKeyboardFocus(resourceToggle);
  await page.keyboard.press("Enter");
  await expect(resourceToggle).not.toHaveAttribute("aria-expanded", wasExpanded ?? "");
  await page.keyboard.press("Enter");
  await expect(resourceToggle).toHaveAttribute("aria-expanded", wasExpanded ?? "");

  const graphButton = page.getByTestId("activity-bar").getByRole("button", { name: "Knowledge Graph" });
  await tabTo(page, graphButton);
  await expectVisibleKeyboardFocus(graphButton);
  await page.keyboard.press("Enter");
  const graphNode = page.locator('[data-node-id="node-doc-zettel"]');
  await tabTo(page, graphNode);
  await expectVisibleKeyboardFocus(graphNode);
  await page.keyboard.press("Space");
  await expect(graphNode).toHaveAttribute("data-focus-state", "selected");
  await page.keyboard.press("Enter");
  await expect(page.getByTestId("document-reader-title")).toContainText("zettelkasten-principles.md");

  const secondDocument = page.getByTestId("document-tree").getByRole("button", { name: "memory-graph-design.pdf", exact: true });
  await tabTo(page, secondDocument);
  await expectVisibleKeyboardFocus(secondDocument);
  await page.keyboard.press("Enter");
  await expect(page.getByTestId("document-reader-title")).toContainText("memory-graph-design.pdf");

  const aiButton = page.getByTestId("activity-bar").getByRole("button", { name: "AI Laboratory" });
  await tabTo(page, aiButton);
  await expectVisibleKeyboardFocus(aiButton);
  await page.keyboard.press("Enter");
  const composer = page.getByTestId("workspace-chat-command");
  const textarea = composer.locator("textarea");
  await tabTo(page, textarea);
  await expectVisibleKeyboardFocus(textarea);
  await page.keyboard.type("Trace keyboard evidence");
  const send = composer.getByRole("button", { name: "Send message" });
  await tabTo(page, send);
  await expectVisibleKeyboardFocus(send);
  await page.keyboard.press("Enter");
  const liveTrace = page.getByTestId("agent-run-trace");
  await expect(liveTrace).toHaveAttribute("aria-live", "polite");
  await expect(liveTrace.locator("header > span")).toHaveAttribute("data-state", "completed");

  const vaultButton = page.getByTestId("activity-bar").getByRole("button", { name: "Research Vault" });
  await tabTo(page, vaultButton);
  await expectVisibleKeyboardFocus(vaultButton);
  await page.keyboard.press("Enter");
  const deleteButton = page.locator(".document-actions__desktop").getByRole("button", { name: "Delete", exact: true });
  await tabTo(page, deleteButton);
  await expectVisibleKeyboardFocus(deleteButton);
  await page.keyboard.press("Enter");
  const dialog = page.getByRole("dialog", { name: "Delete this document?" });
  const cancel = dialog.getByRole("button", { name: "Cancel" });
  await expect(cancel).toBeFocused();
  await page.keyboard.press("Escape");
  await expect(deleteButton).toBeFocused();
  await page.keyboard.press("Enter");
  await expect(cancel).toBeFocused();
  await page.keyboard.press("Tab");
  const confirm = dialog.getByRole("button", { name: "Delete", exact: true });
  await expect(confirm).toBeFocused();
  await page.keyboard.press("Enter");
  await expect(page.getByTestId("document-reader-title")).not.toContainText("memory-graph-design.pdf");
});

test("25 percent playback audit keeps interface motion bounded and composited", async ({ page, context }, testInfo) => {
  test.skip(testInfo.project.name !== "Desktop Chrome", "The CDP audit is browser-level, not viewport-specific.");
  test.setTimeout(120_000);
  const sourceRoot = path.resolve("src");
  const sourceFiles = (await readdir(sourceRoot, { recursive: true }))
    .filter((file) => typeof file === "string" && (file.endsWith(".vue") || file.endsWith(".css")));
  const source = (await Promise.all(sourceFiles.map((file) => readFile(path.join(sourceRoot, file), "utf8")))).join("\n");
  expect(source).not.toMatch(/transition\s*:\s*all\b/);
  expect(source).not.toMatch(/\bease-in(?:\s|[;,)]|$)/);
  expect(source).not.toMatch(/scale\(0(?:\.0+)?\)/);

  await page.setViewportSize({ width: 390, height: 844 });
  const cdp = await context.newCDPSession(page);
  await cdp.send("Animation.enable");
  await cdp.send("Animation.setPlaybackRate", { playbackRate: 0.25 });
  await page.goto("/?preview=1", { waitUntil: "domcontentloaded" });

  type AnimationSample = { id: number; trigger: string; duration: number; properties: string[]; target: string };
  const samples: AnimationSample[] = [];
  const readAnimations = (selector = "") => page.evaluate((surfaceSelector) => {
    const auditWindow = window as Window & {
      __mnemeAnimationAudit?: { ids: WeakMap<Animation, number>; nextId: number };
    };
    auditWindow.__mnemeAnimationAudit ??= { ids: new WeakMap(), nextId: 1 };
    return document.getAnimations().flatMap((animation) => {
      const effect = animation.effect as KeyframeEffect | null;
      const target = effect?.target as HTMLElement | null;
      if (
        surfaceSelector
        && target
        && !target.matches(surfaceSelector)
      ) return [];
      let id = auditWindow.__mnemeAnimationAudit!.ids.get(animation);
      if (!id) {
        id = auditWindow.__mnemeAnimationAudit!.nextId;
        auditWindow.__mnemeAnimationAudit!.nextId += 1;
        auditWindow.__mnemeAnimationAudit!.ids.set(animation, id);
      }
      const timing = effect?.getTiming();
      const properties = new Set<string>();
      for (const frame of effect?.getKeyframes() ?? []) {
        for (const key of Object.keys(frame)) {
          if (!["offset", "easing", "composite", "computedOffset"].includes(key)) properties.add(key);
        }
      }
      return [{
        id,
        duration: typeof timing?.duration === "number" ? timing.duration : 0,
        properties: [...properties],
        target: target?.className?.toString() ?? target?.tagName ?? "unknown",
      }];
    });
  }, selector);
  const collectNewAnimations = async (
    trigger: string,
    selector: string,
    action: () => Promise<unknown>,
  ) => {
    const before = new Set((await readAnimations()).map(({ id }) => id));
    const actionPromise = action();
    let created: AnimationSample[] = [];
    for (let attempt = 0; attempt < 400 && !created.length; attempt += 1) {
      await page.waitForTimeout(5);
      created = (await readAnimations(selector))
        .filter(({ id, duration }) => !before.has(id) && duration > 0 && duration !== Infinity)
        .map((sample) => ({ trigger, ...sample }));
    }
    await actionPromise;
    expect(created, `${trigger} must create an animation on ${selector}`).not.toHaveLength(0);
    samples.push(...created);
    return created;
  };
  const waitForSurfaceAnimations = async (selector: string) => {
    await expect.poll(async () => (await readAnimations(selector)).length, { timeout: 5_000 }).toBe(0);
  };

  const moreTrigger = page.getByTestId("mobile-navigation").getByRole("button", { name: "Open more navigation" });
  await collectNewAnimations("drawer-enter", ".more-sheet, .more-sheet__panel", () => moreTrigger.click());
  await waitForSurfaceAnimations(".more-sheet, .more-sheet__panel");
  await collectNewAnimations(
    "drawer-exit",
    ".more-sheet, .more-sheet__panel",
    () => page.getByTestId("more-navigation-sheet").getByRole("button", { name: "Close" }).click(),
  );
  await waitForSurfaceAnimations(".more-sheet, .more-sheet__panel");
  await openView(page, "Knowledge Graph");
  const filterTrigger = page.getByRole("button", { name: "Graph filters" });
  await collectNewAnimations("popover-enter", ".ui-popover", () => filterTrigger.click());
  const popoverOrigin = await page.locator(".ui-popover").evaluate((element) => {
    const [x, y] = getComputedStyle(element).transformOrigin.split(" ").map(Number.parseFloat);
    return { x, y, width: (element as HTMLElement).offsetWidth };
  });
  expect(popoverOrigin.y).toBeLessThanOrEqual(1);
  expect(Math.abs(popoverOrigin.width - popoverOrigin.x)).toBeLessThanOrEqual(1.5);
  await waitForSurfaceAnimations(".ui-popover");
  await collectNewAnimations("popover-exit", ".ui-popover", () => page.keyboard.press("Escape"));
  await waitForSurfaceAnimations(".ui-popover");
  await openVaultTree(page);
  await page.getByRole("button", { name: "zettelkasten-principles.md", exact: true }).click();
  const deleteAction = await getDocumentAction(page, "Delete");
  await collectNewAnimations("dialog-enter", ".ui-dialog__backdrop, .ui-dialog", () => deleteAction.click());
  await waitForSurfaceAnimations(".ui-dialog__backdrop, .ui-dialog");
  await collectNewAnimations("dialog-exit", ".ui-dialog__backdrop, .ui-dialog", () => page.keyboard.press("Escape"));
  await waitForSurfaceAnimations(".ui-dialog__backdrop, .ui-dialog");

  const notificationTrigger = page.getByTestId("notification-center-toggle");
  const triggerBox = await notificationTrigger.boundingBox();
  expect(triggerBox).not.toBeNull();
  await page.mouse.move(triggerBox!.x + triggerBox!.width / 2, triggerBox!.y + triggerBox!.height / 2);
  await collectNewAnimations("button-active", ".ui-icon-button", () => page.mouse.down());
  await collectNewAnimations("notification-enter", ".ui-popover", () => page.mouse.up());
  await waitForSurfaceAnimations(".ui-popover");
  await collectNewAnimations("notification-exit", ".ui-popover", () => notificationTrigger.click());
  await waitForSurfaceAnimations(".ui-popover");

  await page.emulateMedia({ reducedMotion: "reduce" });
  const reducedSamples = await collectNewAnimations(
    "drawer-reduced-motion",
    ".more-sheet, .more-sheet__panel",
    () => moreTrigger.click(),
  );
  expect(reducedSamples.flatMap(({ properties }) => properties)).not.toContain("transform");
  await page.keyboard.press("Escape");

  expect(Math.max(...samples.map((sample) => sample.duration))).toBeLessThanOrEqual(300);
  const movementProperties = new Set(
    samples.flatMap((sample) => sample.properties).filter(
      (property) => !["opacity", "transform"].includes(property) && !property.toLowerCase().endsWith("color"),
    ),
  );
  console.log(`MOTION_AUDIT ${JSON.stringify({ playbackRate: 0.25, samples })}`);
  expect([...movementProperties]).toEqual([]);
});

test("Graph simulation and AI streaming stay below the long-task budget", async ({ page, context }, testInfo) => {
  test.skip(testInfo.project.name !== "Desktop Chrome", "One Chromium process provides the shared main-thread sample.");
  test.skip(testInfo.config.workers !== 1, "Performance profiling runs through npm run test:quality in an uncontended worker.");
  test.setTimeout(120_000);
  const aiPage = await context.newPage();
  const pages = [page, aiPage];
  for (const currentPage of pages) {
    await currentPage.addInitScript(() => {
      const target = window as Window & { __mnemeLongTasks?: number[] };
      target.__mnemeLongTasks = [];
      new PerformanceObserver((list) => {
        target.__mnemeLongTasks?.push(...list.getEntries().map((entry) => entry.duration));
      }).observe({ type: "longtask", buffered: true });
    });
    await currentPage.goto("/?preview=1", { waitUntil: "domcontentloaded" });
  }

  await installPacedPreviewStream(aiPage, 55);

  const graphSession = await context.newCDPSession(page);
  const aiSession = await context.newCDPSession(aiPage);
  await Promise.all([graphSession.send("Performance.enable"), aiSession.send("Performance.enable")]);
  await openView(aiPage, "AI Laboratory");
  const composer = aiPage.getByTestId("workspace-chat-command");
  const streamState = aiPage.getByTestId("agent-run-trace").locator("header > span");
  const graphStage = page.getByTestId("graph-output-workspace");
  const metric = (metrics: { metrics: Array<{ name: string; value: number }> }, name: string) =>
    metrics.metrics.find((item) => item.name === name)?.value ?? 0;
  const samples: Array<{
    graphTaskDurationMs: number;
    aiTaskDurationMs: number;
    graphLayoutDurationMs: number;
    aiLayoutDurationMs: number;
    graphLongTaskCount: number;
    aiLongTaskCount: number;
    graphMaxLongTaskMs: number;
    aiMaxLongTaskMs: number;
  }> = [];

  await page.waitForTimeout(500);
  for (let iteration = 1; iteration <= 3; iteration += 1) {
    await page.getByRole("button", { name: "Restart graph layout" }).click();
    await expect(graphStage).toHaveAttribute("data-simulation-phase", "running");
    await composer.locator("textarea").fill(`Measure streaming performance ${iteration}`);
    await composer.getByRole("button", { name: "Send message" }).click();
    await expect(streamState).toHaveAttribute("data-state", "streaming");
    await expect(graphStage).toHaveAttribute("data-simulation-phase", "running");
    await expect(streamState).toHaveAttribute("data-state", "streaming");

    await Promise.all(pages.map((currentPage) => currentPage.evaluate(() => {
      (window as Window & { __mnemeLongTasks?: number[] }).__mnemeLongTasks = [];
    })));
    const before = await Promise.all([graphSession.send("Performance.getMetrics"), aiSession.send("Performance.getMetrics")]);
    await expect(streamState).toHaveAttribute("data-state", "completed", { timeout: 10_000 });
    await page.waitForTimeout(50);
    const after = await Promise.all([graphSession.send("Performance.getMetrics"), aiSession.send("Performance.getMetrics")]);
    const [graphLongTasks, aiLongTasks] = await Promise.all(pages.map((currentPage) => currentPage.evaluate(
      () => (window as Window & { __mnemeLongTasks?: number[] }).__mnemeLongTasks ?? [],
    )));
    samples.push({
      graphTaskDurationMs: Math.round((metric(after[0], "TaskDuration") - metric(before[0], "TaskDuration")) * 1_000),
      aiTaskDurationMs: Math.round((metric(after[1], "TaskDuration") - metric(before[1], "TaskDuration")) * 1_000),
      graphLayoutDurationMs: Math.round((metric(after[0], "LayoutDuration") - metric(before[0], "LayoutDuration")) * 1_000),
      aiLayoutDurationMs: Math.round((metric(after[1], "LayoutDuration") - metric(before[1], "LayoutDuration")) * 1_000),
      graphLongTaskCount: graphLongTasks.length,
      aiLongTaskCount: aiLongTasks.length,
      graphMaxLongTaskMs: Math.round(Math.max(0, ...graphLongTasks)),
      aiMaxLongTaskMs: Math.round(Math.max(0, ...aiLongTasks)),
    });
  }

  const median = (values: number[]) => [...values].sort((left, right) => left - right)[Math.floor(values.length / 2)];
  const report = {
    sampleCount: samples.length,
    graphTaskDurationMs: median(samples.map(({ graphTaskDurationMs }) => graphTaskDurationMs)),
    aiTaskDurationMs: median(samples.map(({ aiTaskDurationMs }) => aiTaskDurationMs)),
    graphLayoutDurationMs: median(samples.map(({ graphLayoutDurationMs }) => graphLayoutDurationMs)),
    aiLayoutDurationMs: median(samples.map(({ aiLayoutDurationMs }) => aiLayoutDurationMs)),
    graphLongTaskCount: median(samples.map(({ graphLongTaskCount }) => graphLongTaskCount)),
    aiLongTaskCount: median(samples.map(({ aiLongTaskCount }) => aiLongTaskCount)),
    graphMaxLongTaskMs: Math.max(...samples.map(({ graphMaxLongTaskMs }) => graphMaxLongTaskMs)),
    aiMaxLongTaskMs: Math.max(...samples.map(({ aiMaxLongTaskMs }) => aiMaxLongTaskMs)),
    samples,
  };

  console.log(`PERFORMANCE_AUDIT ${JSON.stringify(report)}`);
  expect(report.sampleCount).toBe(3);
  expect(report.graphTaskDurationMs).toBeLessThanOrEqual(500);
  expect(report.aiTaskDurationMs).toBeLessThanOrEqual(500);
  expect(report.graphLayoutDurationMs).toBeLessThanOrEqual(150);
  expect(report.aiLayoutDurationMs).toBeLessThanOrEqual(150);
  expect(report.graphMaxLongTaskMs).toBeLessThanOrEqual(120);
  expect(report.aiMaxLongTaskMs).toBeLessThanOrEqual(120);
  expect(report.graphLongTaskCount).toBeLessThanOrEqual(2);
  expect(report.aiLongTaskCount).toBeLessThanOrEqual(2);
  await aiPage.close();
});
