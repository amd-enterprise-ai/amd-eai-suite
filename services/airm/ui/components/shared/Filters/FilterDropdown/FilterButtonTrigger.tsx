// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { DropdownTrigger, PressEvent, Tooltip, cn } from '@heroui/react';
import { IconChevronDown } from '@tabler/icons-react';
import { ReactNode, useCallback, useMemo } from 'react';
import ClearSingleFilterButton from '../ClearSingleFilterButton';
import { InlineBadge } from '@/components/shared/InlineBadge';
import { ActionButton } from '@/components/shared/Buttons';

export interface FilterButtonTriggerProps {
  label: string;
  className?: string;
  numberOfSelectedKeys: number;
  startContent?: ReactNode;
  tooltipText?: string;
  isActive?: boolean;
  onReset?: () => void;
}

const FilterButtonTrigger: React.FC<FilterButtonTriggerProps> = ({
  label,
  className,
  startContent,
  numberOfSelectedKeys,
  tooltipText,
  isActive = false,
  onReset,
}) => {
  const handleResetClick = useCallback(
    (_e: PressEvent): void => {
      onReset?.();
    },
    [onReset],
  );

  // Memoize complex conditional components for performance
  const memoizedStartContent = useMemo(() => {
    if (!isActive) return null;

    return (
      <Tooltip content={tooltipText} delay={500} size="sm" className="max-w-40">
        <div className="cursor-help">
          <InlineBadge color="primary" size="sm" variant="solid">
            {numberOfSelectedKeys.toString()}
          </InlineBadge>
        </div>
      </Tooltip>
    );
  }, [isActive, tooltipText, numberOfSelectedKeys]);

  return (
    <div className={cn('relative sm:flex', className)}>
      <DropdownTrigger className="w-full">
        <ActionButton
          className="px-2"
          endContent={
            <div className="w-6 h-6 min-w-6 flex justify-center items-center">
              {isActive && onReset ? null : (
                <IconChevronDown size={16} stroke={2} />
              )}
            </div>
          }
          aria-label={label}
          startContent={memoizedStartContent}
        >
          <div className="flex flex-grow items-center gap-2 truncate">
            {startContent} {label}
          </div>
        </ActionButton>
      </DropdownTrigger>

      {isActive && onReset && (
        <ClearSingleFilterButton onPress={handleResetClick} />
      )}
    </div>
  );
};

export default FilterButtonTrigger;
