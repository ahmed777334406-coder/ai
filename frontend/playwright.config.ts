import { defineConfig } from '@playwright/test';
const site=new URL(process.env.BASE_URL || 'http://localhost:3000');
if(!['localhost','127.0.0.1','[::1]'].includes(site.hostname)) throw new Error('E2E mutations require an isolated local test server.');
export default defineConfig({
  testDir:'./e2e', fullyParallel:false, workers:1, timeout:60000,
  reporter:[['list'],['json',{outputFile:'test-results/results.json'}]],
  use:{actionTimeout:15000,navigationTimeout:30000,baseURL:process.env.BASE_URL || 'http://localhost:3000', launchOptions:{executablePath:process.env.CHROMIUM_PATH || undefined, args:['--no-sandbox', ...(process.env.CLOUD_PROXY_SPKI ? [`--ignore-certificate-errors-spki-list=${process.env.CLOUD_PROXY_SPKI}`] : [])]}, screenshot:'only-on-failure'},
});
