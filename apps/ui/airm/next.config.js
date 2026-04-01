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
        loaders: ['@svgr/webpack'],
        as: '*.js',
      },
    },
    resolveAlias: {
      '@': '.',
    },
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
