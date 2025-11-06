// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import react from '@vitejs/plugin-react';

import path from 'path';
import { defineConfig as defineViteConfig, mergeConfig } from 'vite';
import { defineConfig as defineVitestConfig } from 'vitest/config';

const viteConfig = defineViteConfig({
  plugins: [react()],
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
    alias: {
      '\\.(gif|ttf|eot|svg|png)$': '<rootDir>/__mocks__/fileMock.js',
    },
    coverage: {
      provider: 'istanbul',
      reporter: ['html'],
      enabled: true,
      exclude: [
        'app/api/**',
        '__tests__/**',
        '__mocks__/**',
        '.next/**',
        'node_modules/**',
        'dist/**',
        'coverage/**',
        'vite.config.ts',
        'vitest.config.ts',
        'components/shared/Metrics/**/{AreaChart,BarChart,LineChart,CategoryBar}.tsx', // trust tremor chart component to be tested
        'utils/app/tremor-charts/*.ts', // trust tremor charts have been tested
        '*.js',
      ],
      thresholds: {
        statements: 70.9,
        branches: 58.5,
        functions: 71.4,
        lines: 71.1,
        'components/shared/**/*.{ts,tsx}': {
          statements: 68.8,
          branches: 60.5,
          functions: 68.9,
          lines: 67.6,
        },
        'components/features/**/*.{ts,tsx}': {
          statements: 84,
          branches: 44,
          functions: 78,
          lines: 67,
        },
        'pages/**/*.{ts,tsx}': {
          statements: 66,
          branches: 42,
          functions: 63,
          lines: 67,
        },
        'hooks/**/*.{ts,tsx}': {
          statements: 65,
          branches: 71,
          functions: 57,
          lines: 67,
        },
        'utils/**/*.{ts,tsx}': {
          statements: 67.7,
          branches: 55,
          functions: 77.4,
          lines: 67.6,
        },
      },
    },
  },
});

export default mergeConfig(viteConfig, vitestConfig);
