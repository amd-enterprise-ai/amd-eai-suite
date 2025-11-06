// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { Card, CardBody, Skeleton, cn } from '@heroui/react';
import { ReactNode, useMemo } from 'react';

import {
  AvailableChartColors,
  getColorClassName,
} from '@/utils/app/tremor-charts/utils';

import { CategoryData, CategoryValue } from '@/types/metrics/category-bar';

import { CategoryBar } from '../CategoryBar';

interface Props {
  title: string | ReactNode;
  total: string | ReactNode;
  data: CategoryData | null;
  isLoading?: boolean;
}

const skeletonData: CategoryValue[] = [
  { label: 'skeleton-0', value: 0 },
  { label: 'skeleton-1', value: 0 },
  { label: 'skeleton-2', value: 0 },
  { label: 'skeleton-3', value: 0 },
];

export const CategorySplitStatsCard = ({
  title,
  total,
  data,
  isLoading,
}: Props) => {
  const calculatedColors = useMemo(() => {
    return (data ? data.values : skeletonData).map(
      (entry, idx) => entry.color ?? AvailableChartColors[idx],
    );
  }, [data]);

  return (
    <Card
      className="h-full grow"
      classNames={{
        base: 'shadow-sm border-1 border-default-200 rounded-sm	dark:bg-default-100',
      }}
    >
      <CardBody>
        <div>{title}</div>
        <div className="my-4">
          {isLoading ? (
            <div className="flex gap-2 items-end">
              <Skeleton className="h-8 w-8 rounded-[3px]" />
              <Skeleton className="h-4 w-28 rounded-[3px]" />
            </div>
          ) : (
            total
          )}
        </div>
        <div>
          <div className="text-sm mb-4">
            {isLoading ? (
              <Skeleton className="h-3 w-32 rounded-[3px]" />
            ) : (
              data?.title
            )}
          </div>
          <div>
            <CategoryBar
              showLabels={false}
              values={data ? data.values.map((entry) => entry.value) : []}
              colors={calculatedColors}
              isLoading={isLoading}
            />
          </div>
          <div className="grid grid-cols-2 gap-2 mt-4">
            {(isLoading || !data ? skeletonData : data.values).map(
              (entry, idx) => {
                return (
                  <div key={entry.label} className="flex items-center text-sm">
                    <div
                      className={cn(
                        'w-3 h-3 bg-primary rounded-[3px]',
                        getColorClassName(
                          isLoading ? 'gray' : calculatedColors[idx],
                          'bg',
                        ),
                        { 'animate-pulse': isLoading },
                      )}
                    ></div>
                    <span className="mx-2">
                      {isLoading ? (
                        <Skeleton className="h-3 w-16 rounded-[3px]" />
                      ) : (
                        entry.label
                      )}
                    </span>
                    <span className="text-sm text-content4 flex gap-1 items-center">
                      (
                      {isLoading ? (
                        <Skeleton className="h-3 w-4 rounded-[3px]" />
                      ) : (
                        entry.value
                      )}
                      <span>/</span>
                      {isLoading ? (
                        <Skeleton className="h-3 w-4 rounded-[3px]" />
                      ) : (
                        data?.total
                      )}
                      )
                    </span>
                  </div>
                );
              },
            )}
          </div>
        </div>
      </CardBody>
    </Card>
  );
};

export default CategorySplitStatsCard;
