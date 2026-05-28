// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import react from '@vitejs/plugin-react';

import path from 'path';
import { defineConfig as defineViteConfig, mergeConfig } from 'vite';
import { defineConfig as defineVitestConfig } from 'vitest/config';

const rootDir = __dirname;

const viteConfig = defineViteConfig({
  plugins: [react()],
  define: {
    'process.env.NODE_ENV': '"development"',
  },
  esbuild: {
    define: {
      'process.env.NODE_ENV': '"development"',
    },
  },
});

const vitestConfig = defineVitestConfig({
  resolve: {
    alias: {
      '@': path.resolve(rootDir, './'),
      '@amdenterpriseai/components': path.resolve(rootDir, 'src/index.ts'),
      '@amdenterpriseai/types': path.resolve(rootDir, '../types/src/index.ts'),
      '@amdenterpriseai/utils/app': path.resolve(
        rootDir,
        '../utils/src/app/index.ts',
      ),
      '@amdenterpriseai/utils/data': path.resolve(
        rootDir,
        '../utils/src/data/index.ts',
      ),
      '@amdenterpriseai/utils/server': path.resolve(
        rootDir,
        '../utils/src/server/index.ts',
      ),
      '@amdenterpriseai/utils': path.resolve(rootDir, '../utils/src/index.ts'),
      '@amdenterpriseai/hooks': path.resolve(rootDir, '../hooks/src/index.ts'),
      '@amdenterpriseai/layouts': path.resolve(
        rootDir,
        '../layouts/src/index.ts',
      ),
      '@amdenterpriseai/assets/svg/logo': path.resolve(
        rootDir,
        '../assets/src/svg/logo/index.ts',
      ),
    },
  },
  define: process.env.VITEST ? {} : { global: 'window' },
  test: {
    setupFiles: ['__tests__/setup.ts'],
    mockReset: true,
    globals: true,
    environment: 'jsdom',
    ...(process.env.CI ? { testTimeout: 15_000, hookTimeout: 15_000 } : {}),
    pool: 'threads',
    coverage: {
      provider: 'v8',
      reporter: ['html'],
      // Avoid parallel coverage tmp races (ENOENT on coverage/.tmp) in CI
      enabled: process.env.VITEST_COVERAGE === 'true',
      include: ['src/**/*.{ts,tsx}'],
      exclude: [
        '__tests__/**',
        'node_modules/**',
        'dist/**',
        'coverage/**',
        'vitest.config.ts',
      ],
      thresholds: undefined,
    },
  },
});

export default mergeConfig(viteConfig, vitestConfig);
