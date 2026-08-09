// Scénario 4 : modération — signalement d'un post, puis traitement par l'administrateur.
const { test, expect } = require("@playwright/test");
const { seConnecter, seDeconnecter } = require("./helpers");

test("modération : signaler un post puis le résoudre", async ({ page }) => {
  // zoe signale un post existant
  await seConnecter(page, "zoe");
  await page.goto("/");
  await page.getByRole("link", { name: /Lancement d'un incubateur/ }).click();

  await page.locator('[data-action="signaler"][data-type="post"]').click();
  const modale = page.locator(".modale-voile");
  await modale.locator('textarea[name="raison"]').fill("Signalement créé par le scénario e2e.");
  await modale.locator('button[type="submit"]').click();
  await expect(page.locator(".modale-voile")).toHaveCount(0);
  await expect(page.getByText("Signalement créé par le scénario e2e.")).toHaveCount(0);

  // demo, administrateur de la communauté, traite le signalement
  await seDeconnecter(page);
  await seConnecter(page, "demo");
  await page.goto("/#/c/tech-afrique");
  await page.locator('a:has-text("Modération")').click();
  await expect(page.getByRole("heading", { name: "Signalements" })).toBeVisible();

  const signalement = page.locator(".signalement").filter({
    hasText: "Signalement créé par le scénario e2e.",
  });
  await expect(signalement).toBeVisible();

  // Résoudre : le signalement sort de la liste "En attente"…
  await signalement.getByRole("button", { name: "Résoudre" }).click();
  await expect(signalement).toHaveCount(0);

  // …et apparaît "Résolu" dans le filtre dédié
  await page.getByRole("button", { name: "Résolus" }).click();
  await expect(
    page.locator(".signalement").filter({ hasText: "Signalement créé par le scénario e2e." })
  ).toHaveText(/Résolu/);
});