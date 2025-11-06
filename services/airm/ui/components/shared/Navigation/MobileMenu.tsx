// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import {
  Navbar,
  NavbarContent,
  NavbarMenu,
  NavbarMenuItem,
  NavbarMenuToggle,
} from '@heroui/react';
import { IconMenu, IconX } from '@tabler/icons-react';
import React, { Fragment } from 'react';

import { useTranslation } from 'next-i18next';
import { usePathname } from 'next/navigation';
import router from 'next/router';

import {
  airmMenuItems,
  aiWorkbenchMenuItems,
  isMenuItemActive,
} from '@/utils/app/navigation';
import { useAccessControl } from '@/hooks/useAccessControl';

import { SidebarItem } from '@/types/navigation';

export const MobileMenu: React.FC = () => {
  const [isMenuOpen, setIsMenuOpen] = React.useState(false);
  const pathname = usePathname();
  const { t } = useTranslation('common');
  const { isAdministrator } = useAccessControl();

  function handleNavigation(href: string) {
    setIsMenuOpen(false);
    router.push(href);
  }

  const isItemActive = (item: SidebarItem) =>
    isMenuItemActive(item.href, pathname);

  const navigationItem = (item: SidebarItem, nested: boolean = false) => (
    <NavbarMenuItem
      isActive={isItemActive(item)}
      key={item.stringKey}
      onClick={() => handleNavigation(item.href)}
      className={`active:text-primary font-light w-full cursor-pointer py-0.5
        ${isItemActive(item) ? 'font-bold text-default-800' : 'text-default-600 dark:text-default-500'}
        ${nested && ' pl-4'}`}
    >
      {t(item.stringKey)}
    </NavbarMenuItem>
  );

  const nestedNavigationItem = (item: SidebarItem) => (
    <>
      {navigationItem(item)}
      {item.subItems?.map((subItem) => navigationItem(subItem, true))}
    </>
  );

  return (
    <Navbar
      className="md:hidden block"
      classNames={{
        wrapper: 'px-0',
      }}
      isMenuOpen={isMenuOpen}
      onMenuOpenChange={setIsMenuOpen}
    >
      <NavbarContent className="px-0">
        <NavbarMenuToggle
          icon={isMenuOpen ? <IconX /> : <IconMenu />}
          aria-label={
            isMenuOpen
              ? (t('menu.actions.close') as string)
              : (t('menu.actions.open') as string)
          }
        />
      </NavbarContent>

      <NavbarMenu>
        {isAdministrator && (
          <>
            <div className="mb-2 mt-2 text-sm text-neutral-500 font-semibold">
              {t('sections.resourceManagement.title')}
            </div>
            {airmMenuItems.map((item: SidebarItem) => (
              <Fragment key={item.stringKey}>
                {item.subItems
                  ? nestedNavigationItem(item)
                  : navigationItem(item)}
              </Fragment>
            ))}
          </>
        )}

        <div className="mb-2 mt-2 text-sm text-neutral-500 font-semibold">
          {t('sections.aiWorkbench.title')}
        </div>
        {aiWorkbenchMenuItems.map((item: SidebarItem) => (
          <Fragment key={item.stringKey}>
            {item.subItems ? nestedNavigationItem(item) : navigationItem(item)}
          </Fragment>
        ))}
      </NavbarMenu>
    </Navbar>
  );
};

export default MobileMenu;
