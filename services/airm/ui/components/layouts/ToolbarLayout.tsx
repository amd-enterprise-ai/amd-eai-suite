// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { PropsWithChildren } from 'react';

export const Toolbar = ({ children }: PropsWithChildren) => {
  return (
    <div className="flex flex-wrap items-center justify-between w-full max-w-full rounded-md z-20 my-8 gap-3">
      {children}
    </div>
  );
};
