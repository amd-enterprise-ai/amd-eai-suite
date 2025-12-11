// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import react from '@vitejs/plugin-react';
import { resolve } from 'path';
import { defineConfig } from 'vite';
import { createRequire } from 'module';

const require = createRequire(import.meta.url);
const ladleReactPath = require.resolve('@ladle/react');

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': resolve(__dirname, '../'),
      // Allow the shim to import from the actual package (must be first)
      '@ladle/react-original': ladleReactPath,
      // Redirect @ladle/react imports to our shim that wraps Story with context
      '@ladle/react': resolve(__dirname, './ladle-shim.tsx'),
    },
  },
});
