// Scénario 5 : recherche, thème clair/sombre et page introuvable.
const { test, expect } = require("@playwright/test");

test("recherche : trouve les posts correspondants", async ({ page }) => {
  await page.goto("/");
  await page.locator("#champ-recherche").fill("incubateur");
  await page.locator("#form-recherche").press("Enter");
  await expect(page.getByText("Lancement d'un incubateur pour fintechs à Dakar")).toBeVisible();
  await expect(page.getByText("Comment la diaspora finance les start-ups locales ?")).toHaveCount(0);
});

test("thème : basculer entre sombre et clair", async ({ page }) => {
  await page.goto("/");
  await expect(page.locator("html")).toHaveAttribute("data-theme", "sombre");
  await page.locator("#btn-theme").click();
  await expect(page.locator("html")).toHaveAttribute("data-theme", "clair");
  await page.locator("#btn-theme").click();
  await expect(page.locator("html")).toHaveAttribute("data-theme", "sombre");
});

test("404 : une route inconnue affiche la page introuvable", async ({ page }) => {
  await page.goto("/#/route-inexistante");
  await expect(page.getByText("Page introuvable")).toBeVisible();
});