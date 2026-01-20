// Test setup file for Vitest
import { config } from '@vue/test-utils'

// Mock fetch globally
global.fetch = vi.fn()

// Configure Vue Test Utils
config.global.mocks = {
  $route: {
    params: {},
    query: {}
  },
  $router: {
    push: vi.fn(),
    replace: vi.fn(),
    go: vi.fn(),
    back: vi.fn()
  }
}

// Reset mocks after each test
afterEach(() => {
  vi.clearAllMocks()
})
