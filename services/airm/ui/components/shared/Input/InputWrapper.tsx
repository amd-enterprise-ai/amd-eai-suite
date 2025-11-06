// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

// FIXME: Refactor or remove?
import { Tooltip } from '@heroui/react';
import { PropsWithChildren } from 'react';
import React from 'react';

interface Props {
  label: string;
  value?: number | number[] | string | boolean | null;
  tooltip?: string;
  description?: string;
  horizontal?: boolean;
}
export const InputWrapper = ({
  label,
  description,
  tooltip,
  value,
  children,
  horizontal,
}: PropsWithChildren<Props>) => (
  <div
    className={`flex gap-3 first-of-type:pt-0 py-4 ${horizontal ? 'flex-row items-center' : 'flex-col'}`}
  >
    <div className="w-full flex justify-between">
      <div className="flex flex-row items-center">
        {tooltip || description ? (
          <Tooltip
            content={
              <div className="flex flex-col gap-3">
                <span className="font-bold">{description || ''}</span>{' '}
                {tooltip ? <span>{tooltip}</span> : null}
              </div>
            }
            placement="left"
            offset={32}
            containerPadding={24}
            className="max-w-60 p-4"
          >
            <div className="mr-1.5 text-sm font-bold border-b-1.5 cursor-help border-transparent hover:border-default-800 border-dotted">
              {label}
            </div>
          </Tooltip>
        ) : null}
      </div>
      <div className="text-default-700 text-sm font-semibold">{value}</div>
    </div>
    {children}
  </div>
);
