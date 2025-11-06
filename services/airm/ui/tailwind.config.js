// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import appColorPalette from './utils/app/colors';

const { heroui, colors } = require('@heroui/react');

const config = {
  content: [
    './app/**/*.{js,ts,jsx,tsx}',
    './pages/**/*.{js,ts,jsx,tsx}',
    './components/**/*.{js,ts,jsx,tsx}',
    './utils/app/**/*.{js,ts,jsx,tsx}',
    './node_modules/@heroui/theme/dist/**/*.{js,ts,jsx,tsx}',
  ],
  darkMode: 'class',
  theme: {
    fontFamily: {
      sans: [
        '-apple-system',
        'BlinkMacSystemFont',
        '"Segoe UI"',
        'Roboto',
        'Helvetica',
        'Arial',
        'sans-serif',
        '"Apple Color Emoji"',
        '"Segoe UI Emoji"',
        '"Segoe UI Symbol"',
      ],
    },
    extend: {
      maxHeight: {
        custom: 'calc(100vh - 300px)',
      },
      minHeight: {
        custom: 'calc(100vh - 300px)',
      },
      borderRadius: {
        sm: '8px',
        md: '10px',
        lg: '12px',
        xl: '14px',
      },
      fontSize: {
        xs: '0.64rem',
        sm: '0.8rem',
        base: '1rem',
        xl: '1.25rem',
        '2xl': '1.563rem',
        '3xl': '1.953rem',
        '4xl': '2.441rem',
        '5xl': '3.052rem',
      },
      keyframes: {
        hide: {
          from: { opacity: '1' },
          to: { opacity: '0' },
        },
        slideDownAndFade: {
          from: { opacity: '0', transform: 'translateY(-6px)' },
          to: { opacity: '1', transform: 'translateY(0)' },
        },
        slideLeftAndFade: {
          from: { opacity: '0', transform: 'translateX(6px)' },
          to: { opacity: '1', transform: 'translateX(0)' },
        },
        slideUpAndFade: {
          from: { opacity: '0', transform: 'translateY(6px)' },
          to: { opacity: '1', transform: 'translateY(0)' },
        },
        slideRightAndFade: {
          from: { opacity: '0', transform: 'translateX(-6px)' },
          to: { opacity: '1', transform: 'translateX(0)' },
        },
        accordionOpen: {
          from: { height: '0px' },
          to: { height: 'var(--radix-accordion-content-height)' },
        },
        accordionClose: {
          from: {
            height: 'var(--radix-accordion-content-height)',
          },
          to: { height: '0px' },
        },
        dialogOverlayShow: {
          from: { opacity: '0' },
          to: { opacity: '1' },
        },
        dialogContentShow: {
          from: {
            opacity: '0',
            transform: 'translate(-50%, -45%) scale(0.95)',
          },
          to: { opacity: '1', transform: 'translate(-50%, -50%) scale(1)' },
        },
        drawerSlideLeftAndFade: {
          from: { opacity: '0', transform: 'translateX(100%)' },
          to: { opacity: '1', transform: 'translateX(0)' },
        },
        drawerSlideRightAndFade: {
          from: { opacity: '1', transform: 'translateX(0)' },
          to: { opacity: '0', transform: 'translateX(100%)' },
        },
        pulse: {
          '0%, 100%': { opacity: '1' },
          '50%': { opacity: '0.5' },
        },
        spin: {
          from: { transform: 'rotate(0deg)' },
          to: { transform: 'rotate(360deg)' },
        },
      },
    },
    animation: {
      hide: 'hide 150ms cubic-bezier(0.16, 1, 0.3, 1)',
      slideDownAndFade: 'slideDownAndFade 150ms cubic-bezier(0.16, 1, 0.3, 1)',
      slideLeftAndFade: 'slideLeftAndFade 150ms cubic-bezier(0.16, 1, 0.3, 1)',
      slideUpAndFade: 'slideUpAndFade 150ms cubic-bezier(0.16, 1, 0.3, 1)',
      slideRightAndFade:
        'slideRightAndFade 150ms cubic-bezier(0.16, 1, 0.3, 1)',
      // Accordion
      accordionOpen: 'accordionOpen 150ms cubic-bezier(0.87, 0, 0.13, 1)',
      accordionClose: 'accordionClose 150ms cubic-bezier(0.87, 0, 0.13, 1)',
      // Dialog
      dialogOverlayShow:
        'dialogOverlayShow 150ms cubic-bezier(0.16, 1, 0.3, 1)',
      dialogContentShow:
        'dialogContentShow 150ms cubic-bezier(0.16, 1, 0.3, 1)',
      // Drawer
      drawerSlideLeftAndFade:
        'drawerSlideLeftAndFade 150ms cubic-bezier(0.16, 1, 0.3, 1)',
      drawerSlideRightAndFade: 'drawerSlideRightAndFade 150ms ease-in',
      pulse: 'pulse 2s infinite',
      spin: 'spin 1s linear infinite',
    },
  },
  variants: {
    extend: {
      visibility: ['group-hover'],
    },
  },
  plugins: [
    require('@tailwindcss/typography'),
    heroui({
      themes: {
        light: {
          colors: {
            background: appColorPalette.default[100],
            foreground: appColorPalette.default[800],
            primary: appColorPalette.primary,
            white: appColorPalette.white,
            secondary: appColorPalette.successSecondary,
            warning: appColorPalette.warning,
            danger: appColorPalette.danger,
            success: appColorPalette.successSecondary,
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
          },
        },
      },
    }),
  ],
};

export default config;
