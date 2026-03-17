import '@testing-library/jest-dom/vitest'
import { cleanup } from '@testing-library/react'
import { afterEach, beforeEach } from 'vitest'
import { resetMocks } from '@/shared/lib/mock-data'

afterEach(() => {
  cleanup()
})

beforeEach(() => {
  resetMocks()
})
