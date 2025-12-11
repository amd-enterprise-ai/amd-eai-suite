// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

export const MOTION_PROPS = {
  variants: {
    enter: {
      opacity: 1,
      x: 0,
    },
    exit: {
      x: 100,
      opacity: 0,
    },
  },
};
export const BACKDROP = 'blur';
export const CLASSES = {
  header: 'border-b-1 border-default-200 w-full pr-[64px]',
  body: 'py-6',
  closeButton: 'top-2.5 right-2.5',
};
