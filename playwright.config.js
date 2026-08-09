const { defineConfig } = require("@playwright/test");

module.exports = defineConfig({
  testDir: "./e2e",
  timeout: 30_000,
  retries: 0,
  workers: 1,
  reporter: [["list"], ["html", { open: "never" }]],
  use: {
    baseURL: "http://127.0.0.1:8787/",
    locale: "fr-FR",
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
  },
  webServer: {
    command:
      "bash scripts/e2e_setup.sh && .venv/bin/python manage.py runserver 127.0.0.1:8787 --settings=config.settings_e2e --noreload",
    url: "http://127.0.0.1:8787/",
    reuseExistingServer: !process.env.CI,
    timeout: 120_000,
  },
});