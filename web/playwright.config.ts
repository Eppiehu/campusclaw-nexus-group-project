import { defineConfig, devices } from '@playwright/test'
import { isolatedBaseURL } from './e2e/target'

const channel = process.env.PLAYWRIGHT_CHANNEL?.trim()

export default defineConfig({
  testDir: './e2e',
  fullyParallel: false,
  workers: 1,
  retries: 0,
  use: {
    ...devices['Desktop Chrome'],
    baseURL: isolatedBaseURL(),
    ...(channel ? { channel } : {}),
    trace: 'off',
    screenshot: 'off',
    video: 'off',
  },
})
