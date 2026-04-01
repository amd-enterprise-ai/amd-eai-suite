// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import react from '@vitejs/plugin-react';

import path from 'path';
import { defineConfig as defineViteConfig, mergeConfig } from 'vite';
import { defineConfig as defineVitestConfig } from 'vitest/config';

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
      '@': path.resolve(__dirname, './'),
    },
  },
  define: process.env.VITEST ? {} : { global: 'window' },
  test: {
    setupFiles: ['__tests__/setup.ts'],
    mockReset: true,
    globals: true,
    environment: 'jsdom',
    pool: 'threads',
    coverage: {
      provider: 'v8',
      reporter: ['html'],
      enabled: true,
      include: ['**/*.{ts,tsx}'],
      exclude: [
        '__tests__/**',
        '__mocks__/**',
        '.next/**',
        'node_modules/**',
        'dist/**',
        'coverage/**',
        'vite.config.ts',
        'vitest.config.ts',
        'src/app/tremor-charts/*.ts', // trust tremor charts have been tested
        '*.js',
      ],
      thresholds: process.env.CI
        ? undefined
        : {
            statements: 68.8,
            branches: 60.5,
            functions: 68.9,
            lines: 67.6,
          },
    },
  },
});

export default mergeConfig(viteConfig, vitestConfig);
