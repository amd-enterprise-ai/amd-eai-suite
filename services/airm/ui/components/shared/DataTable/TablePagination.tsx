// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { Pagination, Select, SelectItem } from '@heroui/react';
import React from 'react';

import { TFunction } from 'next-i18next';

import { PageFrameSize } from '@/types/enums/page-frame-size';

interface Props {
  currentPage: number;
  frameSize: PageFrameSize;
  totalItems: number;
  translation: TFunction;
  translationKeyPrefix?: string;
  onFrameSizeChange: (frameSize: PageFrameSize) => void;
  onPageChange: (page: number) => void;
}

const ClientSidePagination: React.FC<Props> = ({
  currentPage,
  frameSize,
  totalItems,
  translation,
  translationKeyPrefix,
  onFrameSizeChange,
  onPageChange,
}) => {
  const t = translation;

  return (
    <div className="h-16 p-4 w-full flex justify-between items-center">
      {totalItems > 0 ? (
        <>
          <div className="flex items-center gap-4 text-sm w-1/3">
            <span>
              {t(
                `list.${translationKeyPrefix ? `${translationKeyPrefix}.` : ''}pagination.pageSize.label`,
              )}
            </span>
            <Select
              defaultSelectedKeys={[
                frameSize
                  ? frameSize.toString()
                  : PageFrameSize.SMALL.toString(),
              ]}
              aria-label={
                t(
                  `list.${translationKeyPrefix ? `${translationKeyPrefix}.` : ''}pagination.pageSize.label`,
                ) || ''
              }
              variant="bordered"
              size="sm"
              onChange={(e) => {
                onFrameSizeChange(e.target.value as unknown as PageFrameSize);
              }}
              className="w-24"
            >
              <SelectItem key={PageFrameSize.SMALL.toString()}>
                {PageFrameSize.SMALL.toString()}
              </SelectItem>
              <SelectItem key={PageFrameSize.MEDIUM.toString()}>
                {PageFrameSize.MEDIUM.toString()}
              </SelectItem>
              <SelectItem key={PageFrameSize.LARGE.toString()}>
                {PageFrameSize.LARGE.toString()}
              </SelectItem>
            </Select>
            <span>
              {t(
                `list.${translationKeyPrefix ? `${translationKeyPrefix}.` : ''}pagination.pageSize.entities`,
              )}
            </span>
          </div>
          <span className="text-sm mx-auto w-1/3 text-center">
            {t(
              `list.${translationKeyPrefix ? `${translationKeyPrefix}.` : ''}pagination.showing`,
              {
                from: Math.min((currentPage - 1) * frameSize + 1, totalItems),
                to: Math.min(
                  (currentPage - 1) * frameSize + frameSize,
                  totalItems,
                ),
                total: totalItems,
              },
            )}
          </span>
          <div className="w-1/3 flex justify-end">
            <Pagination
              size="sm"
              variant="bordered"
              showControls
              initialPage={1}
              page={currentPage}
              total={Math.ceil(totalItems / frameSize)}
              onChange={onPageChange}
            />
          </div>
        </>
      ) : null}
    </div>
  );
};

export default ClientSidePagination;
