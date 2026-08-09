const { chromium } = require("@playwright/test");

(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage();
  page.on("response", (r) => {
    if (r.request().method() !== "GET" && r.url().includes("/api/"))
      console.log("API", r.request().method(), r.url().split("?")[0], "->", r.status(), (r.statusText ? "(" + r.statusText() + ")" : ""));
  });
  page.on("pageerror", (e) => console.log("PAGEERROR:", e.message));
  const suffixe = Date.now();
  await page.goto("http://127.0.0.1:8787/");
  await page.getByRole("button", { name: "Connexion" }).click();
  const modale = page.locator(".modale-voile");
  await modale.locator('input[name="username"]').fill("demo");
  await modale.locator('input[name="password"]').fill("motdepasse123");
  await modale.locator('button[type="submit"]').click();
  await page.locator('[data-action="menu-utilisateur"]').waitFor();
  await page.goto("http://127.0.0.1:8787/");
  await page.getByRole("link", { name: /Lancement d'un incubateur/ }).click();
  await page.locator(".post-page").waitFor();
  const scoreAvant = await page.locator(".post-page [data-champ='score']").first().innerText();
  console.log("score avant:", scoreAvant);
  await page.locator('.post-page [data-action="vote"][data-type="post"]').first().click();
  await page.waitForTimeout(1500);
  const scoreApres = await page.locator(".post-page [data-champ='score']").first().innerText();
  console.log("score apres:", scoreApres);
  const actif = await page.locator(".post-page .bouton-vote.actif").count();
  console.log("boutons actifs:", actif);
  await browser.close();
})();