import { defineConfig, devices, type ReporterDescription } from '@playwright/test';

import { BASE_URL } from './e2e/env.js';

// Retries exist because the suite is globally serial with DB-restore retry
// hooks (see e2e/db-snapshot.ts) — a test that fails then passes on retry is
// "flaky" rather than a hard failure. By default that only shows up as a
// buried "N flaky" line in the run summary. In CI, add reporters that make
// flaky tests visible instead of silent:
// - `github`: emits GitHub Actions annotations — an `::error` annotation
//   with the failed attempt's stack trace for each flaky (or failed) test,
//   plus a `::notice` run-summary annotation with the flaky/failed counts.
// - `json`: writes a machine-readable report that the CI workflow parses
//   with jq to list flaky tests in the job summary.
const reporters: ReporterDescription[] = [
  ['html', { outputFolder: 'playwright-report', open: 'never' }],
  ['junit', { outputFile: 'junit/playwright-results.xml' }],
];
if (process.env.CI) {
  // `json` must stay listed after `html`: the html reporter's onEnd wipes
  // and rebuilds `outputFolder` ('playwright-report'), so a json report
  // written into that same folder before html runs would be deleted.
  reporters.push(['github'], ['json', { outputFile: 'playwright-report/results.json' }]);
}

export default defineConfig({
  testDir: './e2e/tests',
  fullyParallel: false,
  workers: 1,
  retries: 3,
  maxFailures: 1,
  reporter: reporters,
  use: {
    baseURL: BASE_URL,
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
  },
  globalSetup: './e2e/global-setup.ts',
  globalTeardown: './e2e/global-teardown.ts',
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
    {
      name: 'firefox',
      use: { ...devices['Desktop Firefox'] },
    },
  ],
});
