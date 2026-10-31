import { defineConfig, devices } from '@playwright/test'
import { isolatedBaseURL } from './e2e/target'

export default defineConfig({
  testDir: './e2e',
  fullyParallel: false,
  workers: 1,
  retries: 0,
  use: { baseURL: isolatedBaseURL(), ...devices['Desktop Chrome'], trace: 'off', screenshot: 'off', video: 'off' },
})
