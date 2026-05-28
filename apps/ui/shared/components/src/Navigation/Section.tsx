// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { useSession } from 'next-auth/react';
import React, { useRef, useEffect, useState } from 'react';
import { useTranslation } from 'next-i18next';

import { filterMenuItemsByRole } from '@amdenterpriseai/utils/app';

import { SidebarItem } from '@amdenterpriseai/types';

import { CollapsibleItem } from './CollapsibleItem';
import { SidebarButton } from './SidebarButton';
import { Button } from '@heroui/react';

interface Props {
  title: string;
  items: SidebarItem[];
  isSidebarMini: boolean;
  projectPrefix?: string;
}

export const Section: React.FC<Props> = ({
  title,
  items,
  isSidebarMini,
  projectPrefix,
}) => {
  const { t } = useTranslation('common');
  const contentRef = useRef<HTMLDivElement>(null);
  const [contentHeight, setContentHeight] = useState<number>(0);
  const { data: session } = useSession();

  const userRoles = session?.user?.roles ?? [];
  const filteredItems = filterMenuItemsByRole(items, userRoles);

  useEffect(() => {
    if (contentRef.current) {
      const height = contentRef.current.scrollHeight;
      setContentHeight(height);
    }
  }, [filteredItems]);

  return (
    <div>
      <div className="mb-4">
        <Button
          variant="light"
          className={`w-full h-10 justify-start text-sm font-semibold text-nowrap bg-transparent hover:bg-default-100
          ${isSidebarMini ? 'group-hover:flex hidden' : 'flex'}`}
        >
          <div className="flex items-center w-full">
            <span className="flex-1 text-left">{t(title)}</span>
          </div>
        </Button>
      </div>
      <div
        ref={contentRef}
        className=" transition-all duration-200 ease-out"
        style={{
          height: `${contentHeight}px`,
          opacity: 1,
        }}
      >
        <div className="pb-4">
          <ul className="flex flex-col gap-1">
            {filteredItems.map((item: SidebarItem) =>
              item.subItems && item.subItems.length > 0 ? (
                <CollapsibleItem
                  key={item.stringKey}
                  item={item}
                  isSidebarMini={isSidebarMini}
                  defaultExpanded={false}
                  projectPrefix={projectPrefix}
                />
              ) : (
                <li key={item.stringKey}>
                  <SidebarButton
                    href={item.href}
                    text={item.stringKey}
                    icon={item.icon}
                    isSidebarMini={isSidebarMini}
                    projectPrefix={projectPrefix}
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
