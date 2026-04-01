// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

const { i18n } = require('./next-i18next.config');

/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  i18n,
  // Enable standalone output for optimized Docker builds
  output: 'standalone',
  // Transpile @heroui packages to bundle them into standalone output
  transpilePackages: [
    '@heroui/react',
    '@amdenterpriseai/components',
    '@amdenterpriseai/layouts',
    '@amdenterpriseai/hooks',
    '@amdenterpriseai/utils',
  ],
  // Disable source maps in production for faster builds
  productionBrowserSourceMaps: false,
  // Skip type checking during build (already done in CI)
  typescript: {
    ignoreBuildErrors: true,
  },
  turbopack: {
    rules: {
      '*.svg': {
        loaders: [
          {
            loader: '@svgr/webpack',
            options: {
              svgoConfig: {
                plugins: [
                  {
                    name: 'removeAttrs',
                    params: {
                      attrs: ['width', 'height'],
                    },
                  },
                  {
                    name: 'prefixIds',
                    params: {
                      prefixIds: false,
                      prefixClassNames: false,
                    },
                  },
                ],
              },
            },
          },
        ],
        as: '*.js',
      },
    },
    resolveAlias: {
      '@': '.',
      // Map workspace packages to handle circular dependencies in pnpm strict mode
      '@amdenterpriseai/components': '../shared/components/src',
      '@amdenterpriseai/layouts': '../shared/layouts/src',
      '@amdenterpriseai/hooks': '../shared/hooks/src',
      '@amdenterpriseai/utils/app': '../shared/utils/src/app',
      '@amdenterpriseai/utils/data': '../shared/utils/src/data',
      '@amdenterpriseai/utils/server': '../shared/utils/src/server',
      '@amdenterpriseai/utils': '../shared/utils/src',
      '@amdenterpriseai/types': '../shared/types/src',
      '@amdenterpriseai/assets': '../shared/assets',
    },
  },
  experimental: {
    proxyClientMaxBodySize: '100mb',
  },
  webpack(config, { isServer, dev }) {
    const fileLoaderRule = config.module.rules.find((rule) =>
      rule.test?.test?.('.svg'),
    );

    config.experiments = {
      asyncWebAssembly: true,
      layers: true,
    };

    config.module.rules.push(
      {
        ...fileLoaderRule,
        test: /\.svg$/i,
        resourceQuery: /url/,
      },
      {
        test: /\.svg$/i,
        issuer: fileLoaderRule.issuer,
        resourceQuery: { not: [...fileLoaderRule.resourceQuery.not, /url/] },
        use: [
          {
            loader: '@svgr/webpack',
            options: {
              svgoConfig: {
                plugins: [
                  {
                    name: 'removeAttrs',
                    params: {
                      attrs: ['width', 'height'],
                    },
                  },
                  {
                    name: 'prefixIds',
                    params: {
                      prefixIds: false,
                      prefixClassNames: false,
                    },
                  },
                ],
              },
              svgProps: {
                width: '{props.width}',
                height: '{props.height}',
              },
            },
          },
        ],
      },
    );

    return config;
  },
};

module.exports = nextConfig;
