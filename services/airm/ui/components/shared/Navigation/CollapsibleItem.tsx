// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { Button } from '@heroui/react';
import { IconChevronDown, IconChevronRight } from '@tabler/icons-react';
import React, { useState, useRef, useEffect } from 'react';

import { useTranslation } from 'next-i18next';
import { usePathname } from 'next/navigation';

import { isMenuItemActive } from '@/utils/app/navigation';

import { SidebarItem } from '@/types/navigation';

import { SidebarButton } from './SidebarButton';

interface Props {
  item: SidebarItem;
  isSidebarMini: boolean;
  defaultExpanded?: boolean;
}

export const CollapsibleItem: React.FC<Props> = ({
  item,
  isSidebarMini,
  defaultExpanded,
}) => {
  const { t } = useTranslation('common');
  const pathName = usePathname();

  const isActive = isMenuItemActive(item.href, pathName);

  // Simple local state for expansion, with default based on active state
  const [isExpanded, setIsExpanded] = useState<boolean>(
    defaultExpanded || isActive || false,
  );
  const contentRef = useRef<HTMLDivElement>(null);
  const [contentHeight, setContentHeight] = useState<number>(0);

  useEffect(() => {
    if (contentRef.current) {
      setContentHeight(contentRef.current.scrollHeight);
    }
  }, [item.subItems, isExpanded]);

  return (
    <li>
      <div
        className={`menu-item flex justify-center items-center tracking-wide max-h-12 text-sm rounded-md duration-10 w-full cursor-pointer ${
          isActive
            ? 'bg-primary-200/75 hover:bg-primary-300/50 text-primary dark:bg-primary-900/25 dark:hover:bg-primary-800/25 dark:text-primary-500'
            : 'bg-transparent dark:hover:bg-default-100 hover:bg-default-200'
        }`}
      >
        <Button
          onPress={() => setIsExpanded(!isExpanded)}
          variant="light"
          className="w-full h-full py-3 px-0 justify-start bg-transparent hover:bg-transparent min-h-0"
        >
          <div className="flex w-full items-center">
            <span className="px-[14px]">{item.icon}</span>
            <span
              className={
                isSidebarMini
                  ? 'flex-1 text-left text-nowrap scale-0 group-hover:scale-100'
                  : 'flex-1 text-left text-nowrap scale-100'
              }
            >
              {t(item.stringKey)}
            </span>
            <span
              className={
                isSidebarMini
                  ? 'px-2 scale-0 group-hover:scale-100'
                  : 'px-2 scale-100'
              }
            >
              {isExpanded ? (
                <IconChevronDown size={14} />
              ) : (
                <IconChevronRight size={14} />
              )}
            </span>
          </div>
        </Button>
      </div>

      {item.subItems && (
        <div
          ref={contentRef}
          className="overflow-hidden transition-all duration-300 ease-out"
          style={{
            height: isExpanded ? `${contentHeight}px` : '0px',
            opacity: isExpanded ? 1 : 0,
          }}
        >
          <ul
            className={`ml-4 mt-1 ${isSidebarMini ? 'group-hover:block hidden' : 'block'}`}
          >
            {item.subItems.map((subItem: SidebarItem) => (
              <li key={subItem.stringKey} className="gap-1 my-1">
                <SidebarButton
                  href={subItem.href}
                  text={subItem.stringKey}
                  icon={subItem.icon}
                  isSidebarMini={isSidebarMini}
                  nested={true}
                />
              </li>
            ))}
          </ul>
        </div>
      )}
    </li>
  );
};
