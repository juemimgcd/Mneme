import { expect, type Locator, type Page } from "@playwright/test";

export async function openView(page: Page, name: string | RegExp) {
  const activityButton = page.getByTestId("activity-bar").getByRole("button", { name });
  const mobileButton = page.getByTestId("mobile-navigation").getByRole("button", { name });
  const moreTrigger = page.getByTestId("mobile-navigation").getByRole("button", { name: /Open more navigation|打开更多导航/ });
  await expect.poll(async () =>
    await activityButton.isVisible() || await mobileButton.isVisible() || await moreTrigger.isVisible(),
  ).toBe(true);
  if (await activityButton.isVisible()) {
    await activityButton.click();
    return;
  }

  if (await mobileButton.isVisible()) {
    await mobileButton.click();
    return;
  }

  await moreTrigger.click();
  await page.getByTestId("more-navigation-sheet").getByRole("button", { name }).click();
}

export async function openMoreAction(page: Page, name: string | RegExp) {
  const activityButton = page.getByTestId("activity-bar").getByRole("button", { name });
  const toolbarButton = page.getByTestId("sanctuary-topbar").getByRole("button", { name });
  const moreTrigger = page.getByTestId("mobile-navigation").getByRole("button", { name: /Open more navigation|打开更多导航/ });
  await expect.poll(async () =>
    await activityButton.isVisible() || await toolbarButton.isVisible() || await moreTrigger.isVisible(),
  ).toBe(true);
  if (await activityButton.isVisible()) {
    await activityButton.click();
    return;
  }

  if (await toolbarButton.isVisible()) {
    await toolbarButton.click();
    return;
  }

  await moreTrigger.click();
  await page.getByTestId("more-navigation-sheet").getByRole("button", { name }).click();
}

export async function getDocumentAction(page: Page, name: string | RegExp): Promise<Locator> {
  const desktopAction = page.locator(".document-actions__desktop").getByRole("button", { name });
  const mobileTrigger = page.getByRole("button", { name: /Document actions|文档操作/ });
  await expect.poll(async () => await desktopAction.isVisible() || await mobileTrigger.isVisible()).toBe(true);
  if (await desktopAction.isVisible()) return desktopAction;

  await mobileTrigger.click();
  const mobileAction = page.getByRole("menuitem", { name });
  await expect(mobileAction).toBeVisible();
  return mobileAction;
}
