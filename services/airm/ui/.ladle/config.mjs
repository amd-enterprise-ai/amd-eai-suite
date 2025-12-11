// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { resolve } from 'path';

/** @type {import('@ladle/react').UserConfig} */
export default {
  stories: '__stories__/**/*.stories.{tsx,mdx}',
  port: 61000,
  viteConfig: process.cwd() + '/.ladle/vite.config.ts',
  defaultStory: '',
  addons: {
    theme: {
      enabled: true,
      defaultState: 'dark',
    },
  },
};
