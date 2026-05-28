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
import { useSession } from 'next-auth/react';
import React, { Fragment } from 'react';

import { useTranslation } from 'next-i18next';
import { usePathname } from 'next/navigation';
import router, { useRouter } from 'next/router';

import {
  filterMenuItemsByRole,
  isMenuItemActive,
} from '@amdenterpriseai/utils/app';

import { SidebarItem } from '@amdenterpriseai/types';

import { buildProjectHref, stripProjectPrefix } from './project-utils';

interface MobileMenuProps {
  menuItems: SidebarItem[];
  projectPrefix?: string;
}

export const MobileMenu: React.FC<MobileMenuProps> = ({
  menuItems,
  projectPrefix,
}) => {
  const [isMenuOpen, setIsMenuOpen] = React.useState(false);
  const pathname = usePathname();
  const { locale, defaultLocale } = useRouter();
  const { t } = useTranslation('common');
  const { data: session } = useSession();

  const userRoles = session?.user?.roles ?? [];
  const filteredMenuItems = filterMenuItemsByRole(menuItems, userRoles);

  const pathWithoutProject = React.useMemo(
    () => stripProjectPrefix(pathname, projectPrefix, locale, defaultLocale),
    [projectPrefix, pathname, locale, defaultLocale],
  );

  const getFullHref = React.useCallback(
    (href: string): string => buildProjectHref(href, projectPrefix),
    [projectPrefix],
  );

  function handleNavigation(href: string) {
    setIsMenuOpen(false);
    router.push(getFullHref(href));
  }

  const isItemActive = (item: SidebarItem) =>
    isMenuItemActive(item.href, pathWithoutProject);

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
        {filteredMenuItems.map((item: SidebarItem) => (
          <Fragment key={item.stringKey}>
            {item.subItems ? nestedNavigationItem(item) : navigationItem(item)}
          </Fragment>
        ))}
      </NavbarMenu>
    </Navbar>
  );
};

export default MobileMenu;
