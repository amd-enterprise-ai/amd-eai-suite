// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { Button } from '@heroui/react';
import { IconChevronDown, IconChevronRight } from '@tabler/icons-react';
import React, { useRef, useEffect, useState } from 'react';
import { useTranslation } from 'next-i18next';

import { SidebarItem } from '@/types/navigation';

import { CollapsibleItem } from './CollapsibleItem';
import { SidebarButton } from './SidebarButton';

interface Props {
  title: string;
  icon: React.ComponentType<{ size?: number; className?: string }>;
  items: SidebarItem[];
  isSidebarMini: boolean;
  sectionId: string;
  isExpanded: boolean;
  onToggle: (sectionId: string) => void;
}

export const CollapsibleSection: React.FC<Props> = ({
  title,
  icon: IconComponent,
  items,
  isSidebarMini,
  sectionId,
  isExpanded,
  onToggle,
}) => {
  const { t } = useTranslation('common');
  const contentRef = useRef<HTMLDivElement>(null);
  const [contentHeight, setContentHeight] = useState<number>(0);

  const toggleExpansion = () => {
    onToggle(sectionId);
  };

  useEffect(() => {
    if (contentRef.current) {
      const height = contentRef.current.scrollHeight;
      setContentHeight(height);
    }
  }, [items, isExpanded]);

  return (
    <div>
      <div className="mb-4">
        <div
          className={`flex h-10 px-3 items-center text-default-500 dark:text-default-500 cursor-pointer hover:text-neutral-700 transition-colors
          ${isSidebarMini ? 'group-hover:hidden block' : 'hidden'}`}
          onClick={toggleExpansion}
        >
          <IconComponent size={20} />
          <div className="absolute left-[42px] text-default-400">
            {isExpanded ? (
              <IconChevronDown size={10} className="ml-0.25" />
            ) : (
              <IconChevronRight size={10} className="ml-0.25" />
            )}
          </div>
        </div>
        <Button
          onPress={toggleExpansion}
          variant="light"
          className={`w-full h-10 justify-start text-sm font-semibold text-nowrap bg-transparent hover:bg-default-100
          ${isSidebarMini ? 'group-hover:flex hidden' : 'flex'}`}
        >
          <div className="flex items-center w-full">
            <span className="flex-1 text-left">{t(title)}</span>
            {isExpanded ? (
              <IconChevronDown size={16} className="ml-2" />
            ) : (
              <IconChevronRight size={16} className="ml-2" />
            )}
          </div>
        </Button>
      </div>
      <div
        ref={contentRef}
        className="overflow-hidden transition-all duration-200 ease-out"
        style={{
          height: isExpanded ? `${contentHeight}px` : '0px',
          opacity: isExpanded ? 1 : 0,
        }}
      >
        <div className="pb-4">
          <ul className="flex flex-col gap-1">
            {items.map((item: SidebarItem) =>
              item.subItems && item.subItems.length > 0 ? (
                <CollapsibleItem
                  key={item.stringKey}
                  item={item}
                  isSidebarMini={isSidebarMini}
                  defaultExpanded={false}
                />
              ) : (
                <li key={item.stringKey}>
                  <SidebarButton
                    href={item.href}
                    text={item.stringKey}
                    icon={item.icon}
                    isSidebarMini={isSidebarMini}
                  />
                </li>
              ),
            )}
          </ul>
        </div>
      </div>
    </div>
  );
};
