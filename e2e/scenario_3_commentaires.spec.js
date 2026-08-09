// Scénario 3 : commentaires — publication, édition, suppression.
const { test, expect } = require("@playwright/test");
const { seConnecter } = require("./helpers");

test("commentaires : répondre, éditer et supprimer", async ({ page }) => {
  await seConnecter(page, "demo");

  // Ouvrir le post du seed
  await page.getByRole("link", { name: /Lancement d'un incubateur/ }).click();
  await expect(page.locator(".post-page").getByText("Lancement d'un incubateur pour fintechs à Dakar")).toBeVisible();

  // Répondre en commentaire racine
  await page
    .locator('form[data-action="form-commentaire"] textarea[name="contenu"]')
    .fill("Réponse e2e.");
  await page.locator('form[data-action="form-commentaire"] button[type="submit"]').click();
  const monCommentaire = page.locator(".commentaire").filter({ hasText: "Réponse e2e." });
  await expect(monCommentaire).toBeVisible();

  // Éditer son commentaire
  await monCommentaire.locator('[data-action="editer-commentaire"]').click();
  await page
    .locator('form[data-action="form-edition-commentaire"] textarea[name="contenu"]')
    .fill("Réponse e2e modifiée.");
  await page.locator('form[data-action="form-edition-commentaire"] button[type="submit"]').click();
  await expect(page.locator(".commentaire").filter({ hasText: "Réponse e2e modifiée." })).toBeVisible();

  // Supprimer le commentaire
  page.once("dialog", (dialog) => dialog.accept());
  await page
    .locator(".commentaire")
    .filter({ hasText: "Réponse e2e modifiée." })
    .locator('[data-action="supprimer-commentaire"]')
    .click();
  await expect(page.getByText("Réponse e2e modifiée.")).toHaveCount(0);
});