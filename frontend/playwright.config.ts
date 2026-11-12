import { defineConfig } from '@playwright/test';
export default defineConfig({
  testDir:'./e2e', fullyParallel:false, workers:1, timeout:60000,
  reporter:[['list'],['json',{outputFile:'test-results/results.json'}]],
  use:{baseURL:process.env.BASE_URL || 'http://localhost:3000', launchOptions:{executablePath:process.env.CHROMIUM_PATH || '/usr/bin/chromium', args:['--no-sandbox', ...(process.env.CLOUD_PROXY_SPKI ? [`--ignore-certificate-errors-spki-list=${process.env.CLOUD_PROXY_SPKI}`] : [])]}, screenshot:'only-on-failure'},
});
