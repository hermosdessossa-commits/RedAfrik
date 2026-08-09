// Scénario 1 : parcours complet d'un nouveau membre.
// Inscription, création d'une communauté, publication, vote.
const { test, expect } = require("@playwright/test");

test("parcours complet : inscription, communauté, post, vote", async ({ page }) => {
  // Noms uniques pour être rejouable sans reset de base (serveur réutilisé)
  const suffixe = Date.now();
  const nomUtilisateur = `e2e_${suffixe}`;
  const nomCommunaute = `e2e-diaspora-${suffixe}`;

  await page.goto("/");

  // Inscription
  await page.getByRole("button", { name: "Inscription" }).click();
  const modale = page.locator(".modale-voile");
  await modale.locator('input[name="username"]').fill(nomUtilisateur);
  await modale.locator('input[name="email"]').fill(`${nomUtilisateur}@redafrik.demo`);
  await modale.locator('input[name="mot_de_passe"]').fill("motdepasse123");
  await modale.locator('input[name="mot_de_passe_confirmation"]').fill("motdepasse123");
  await modale.locator('button[type="submit"]').click();

  // Connecté automatiquement : le menu utilisateur apparaît
  await expect(page.locator('[data-action="menu-utilisateur"]')).toBeVisible();

  // Créer une communauté
  await page.locator("#btn-nouvelle-communaute").click();
  await page.locator('form[data-action="form-communaute"] input[name="nom"]').fill(nomCommunaute);
  await page
    .locator('form[data-action="form-communaute"] textarea[name="description"]')
    .fill("Communauté de test e2e.");
  await page.locator('form[data-action="form-communaute"] button[type="submit"]').click();
  await expect(page.locator(".communaute-nom")).toHaveText(`r/${nomCommunaute}`);

  // Publier dedans : la page post s'ouvre
  await page.locator('[data-action="publier-ici"]').click();
  await page.locator('input[name="titre"]').fill("Mon premier post e2e");
  await page.locator('textarea[name="contenu"]').fill("Contenu du post e2e.");
  await page.locator('button[type="submit"]').click();
  const post = page.locator(".post-page");
  await expect(post).toBeVisible();
  await expect(post.getByText("Mon premier post e2e")).toBeVisible();

  // Voter positif sur un post d'un autre membre (le sien est exclu par la règle)
  await page.goto("/");
  await page.getByRole("link", { name: /Lancement d'un incubateur/ }).first().click();
  const postDemo = page.locator(".post-page");
  await expect(postDemo.getByText("Lancement d'un incubateur pour fintechs à Dakar")).toBeVisible();
  const scoreAvant = Number(await postDemo.locator('[data-champ="score"]').first().innerText());
  await postDemo.locator('[data-action="vote"][data-type="post"]').first().click();
  await expect(postDemo.locator('[data-champ="score"]').first()).toHaveText(String(scoreAvant + 1));
});