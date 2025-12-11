// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT
import { Button } from '@heroui/react';
import {
  IconCode,
  IconLock,
  IconLockOff,
  IconServer,
} from '@tabler/icons-react';
import { useSession } from 'next-auth/react';
import React, { useEffect, useState } from 'react';

import router from 'next/router';

import { useAccessControl } from '@/hooks/useAccessControl';
import { useNavigationState } from '@/hooks/useNavigationState';

import { aiWorkbenchMenuItems, airmMenuItems } from '@/utils/app/navigation';

import { CollapsibleSection } from './CollapsibleSection';

import AMDLogo from '@/assets/svg/logo/amd-logo.svg';
import AMDLogoSymbol from '@/assets/svg/logo/amd-symbol.svg';

export const Sidebar: React.FC = () => {
  const { data: session } = useSession({
    required: true,
  });
  const [isSidebarMini, setSidebarMini] = useState(false);
  const [mounted, setMounted] = useState(false);
  const [isHovered, setIsHovered] = useState(false);
  const { expandedSections, currentSection, toggleSection } =
    useNavigationState();
  const { isAdministrator } = useAccessControl();

  const toggleSidebar = () => {
    setSidebarMini(!isSidebarMini);
  };

  const handleSectionToggle = (sectionId: string) => toggleSection(sectionId);

  const getSectionExpanded = (sectionId: string) => {
    return isSidebarMini && !isHovered
      ? currentSection === sectionId
      : expandedSections?.includes(sectionId) || false;
  };

  useEffect(() => {
    setMounted(true);
  }, []);

  if (!mounted) {
    return null;
  }

  return (
    <div
      className={`hidden
        group overflow-x-hidden md:flex justify-between py-4 flex-col bg-default-200/20 bg-gradient-to-b dark:bg-default-100/20 border-r border-default-200 dark:border-default-100 relative z-40 transition-all transition-timing-function:ease duration-100 h-screen
        ${isSidebarMini ? 'w-16 hover:w-80 px-2 hover:px-4' : 'w-80 px-4'}`}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
    >
      <div>
        <div className="mb-6 px-4 flex flex-row w-full justify-between items-center text-default-800">
          <div
            className="flex items-center cursor-pointer"
            onClick={() => router.push('/')}
          >
            <AMDLogo
              className={`mr-1 text-default-800 h-3.5 transition-all opacity-100 translate-x-[-200%] ease-in-out overflow-hidden duration-100 ${!isSidebarMini ? 'translate-x-[0%] ' : 'hidden group-hover:translate-x-[0%] group-hover:block'}`}
            />
            <AMDLogoSymbol
              className={`text-default-800 h-3.5 group-hover:translate-x-[0%] group-hover:hidden ease-in-out duration-100 ${!isSidebarMini && 'hidden'}`}
            />
          </div>

          <Button
            onPress={toggleSidebar}
            isIconOnly
            variant="bordered"
            size="sm"
            data-testid="sidebar-lock-button"
            className={`border-1
            ${
              isSidebarMini
                ? 'flex items-center justify-center invisible scale-0 group-hover:block group-hover:visible group-hover:scale-100'
                : ''
            }`}
          >
            <div className="flex justify-center items-center">
              {isSidebarMini ? (
                <IconLock size={14} />
              ) : (
                <IconLockOff size={14} />
              )}
            </div>
          </Button>
        </div>
        {session ? (
          <div>
            {isAdministrator && (
              <CollapsibleSection
                title="sections.resourceManagement.title"
                icon={IconServer}
                items={airmMenuItems}
                isSidebarMini={isSidebarMini}
                sectionId="resource-management"
                isExpanded={getSectionExpanded('resource-management')}
                onToggle={handleSectionToggle}
              />
            )}
            <CollapsibleSection
              title="sections.aiWorkbench.title"
              icon={IconCode}
              items={aiWorkbenchMenuItems}
              isSidebarMini={isSidebarMini}
              sectionId="ai-workbench"
              isExpanded={getSectionExpanded('ai-workbench')}
              onToggle={handleSectionToggle}
            />
          </div>
        ) : null}
      </div>

      <div
        className={`w-full px-4 justify-between items-center text-sm mb-2 ${isSidebarMini ? 'hidden group-hover:flex' : 'flex'}`}
      >
        {process.env.NEXT_PUBLIC_BUILD_VERSION && (
          <span className="flex whitespace-nowrap text-default-600 dark:text-default-400">{`v${process.env.NEXT_PUBLIC_BUILD_VERSION}`}</span>
        )}
      </div>
    </div>
  );
};
