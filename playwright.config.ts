import {defineConfig} from '@playwright/test';
export default defineConfig({testDir:'tests/browser',workers:1,timeout:300000,expect:{timeout:15000},use:{baseURL:process.env.PBI_FRONTEND_URL??'http://localhost:5173',headless:true,screenshot:'only-on-failure'},reporter:[['list']],outputDir:'test-results'});
