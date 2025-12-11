// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { Spinner } from '@heroui/react';
import { FC } from 'react';

export const ChatLoader: FC = () => {
  return (
    <div>
      <Spinner size="sm" color="primary" />
    </div>
  );
};
