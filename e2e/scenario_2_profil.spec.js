// Scénario 2 : profil — édition de la bio et affichage des publications de l'auteur.
const { test, expect } = require("@playwright/test");
const { seConnecter } = require("./helpers");

test("profil : éditer sa bio puis la voir sur sa page", async ({ page }) => {
  await seConnecter(page, "demo");

  // Aller sur son profil via le menu utilisateur
  await page.locator('[data-action="menu-utilisateur"]').click();
  await page.locator('[data-action="profil"]').click();
  await expect(page.locator(".communaute-nom")).toHaveText("u/demo");

  // Modifier la bio
  await page.locator('[data-action="modifier-profil"]').click();
  await page.locator('form[data-action="form-profil"] textarea[name="bio"]').fill("Bio mise à jour par e2e.");
  await page.locator('form[data-action="form-profil"] button[type="submit"]').click();

  // La bio modifiée est visible sur le profil
  await expect(page.getByText("Bio mise à jour par e2e.")).toBeVisible();
});