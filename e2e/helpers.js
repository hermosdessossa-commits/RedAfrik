const { test, expect } = require("@playwright/test");

/** Connexion : renseigne le formulaire de la modale et le soumet. */
async function seConnecter(page, username, motDePasse = "motdepasse123") {
  await page.goto("/");
  await page.getByRole("button", { name: "Connexion" }).first().click();
  const modale = page.locator(".modale-voile");
  await modale.locator('input[name="username"]').fill(username);
  await modale.locator('input[name="password"]').fill(motDePasse);
  await modale.locator('button[type="submit"]').click();
  await expect(page.locator('[data-action="menu-utilisateur"]')).toBeVisible();
}

/** Déconnexion via le menu utilisateur. */
async function seDeconnecter(page) {
  await page.locator('[data-action="menu-utilisateur"]').click();
  await page.locator('[data-action="deconnexion"]').click();
}

module.exports = { seConnecter, seDeconnecter };