// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

const { heroui } = require('@heroui/react');
const appColorPalette = require('./utils/app/colors').default;

module.exports = heroui({
  addCommonColors: true,
  themes: {
    light: {
      colors: {
        background: appColorPalette.default[100],
        foreground: appColorPalette.default[800],
        primary: appColorPalette.primary,
        secondary: appColorPalette.successSecondary,
        warning: appColorPalette.warning,
        danger: appColorPalette.danger,
        success: appColorPalette.successSecondary,
        focus: appColorPalette.primary,
      },
    },
    dark: {
      colors: {
        background: appColorPalette.default[900],
        foreground: appColorPalette.default[200],
        primary: appColorPalette.primary,
        secondary: appColorPalette.successSecondary,
        warning: appColorPalette.warning,
        danger: appColorPalette.danger,
        success: appColorPalette.successSecondary,
        focus: appColorPalette.primary,
      },
    },
  },
});
