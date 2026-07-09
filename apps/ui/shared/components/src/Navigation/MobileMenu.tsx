// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { IconMenu, IconX } from '@tabler/icons-react';
import { useSession } from 'next-auth/react';
import React, { Fragment } from 'react';

import { useTranslation } from 'next-i18next';
import { usePathname } from 'next/navigation';
import router, { useRouter } from 'next/router';

import { useOverlayState } from '@amdenterpriseai/hooks';

import {
  filterMenuItemsByRole,
  isMenuItemActive,
} from '@amdenterpriseai/utils/app';

import { SidebarItem } from '@amdenterpriseai/types';

import { Button } from '../Buttons/Button';
import { buildProjectHref, stripProjectPrefix } from './project-utils';

interface MobileMenuProps {
  menuItems: SidebarItem[];
  projectPrefix?: string;
}

export const MobileMenu: React.FC<MobileMenuProps> = ({
  menuItems,
  projectPrefix,
}) => {
  const { isOpen, onClose, onOpenChange } = useOverlayState();
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
    onClose();
    router.push(getFullHref(href));
  }

  const isItemActive = (item: SidebarItem) =>
    isMenuItemActive(item.href, pathWithoutProject);

  const navigationItem = (item: SidebarItem, nested: boolean = false) => (
    <li key={item.stringKey}>
      <button
        type="button"
        aria-current={isItemActive(item) ? 'page' : undefined}
        onClick={() => handleNavigation(item.href)}
        className={`active:text-primary w-full cursor-pointer py-0.5 text-left text-lg font-light
          ${isItemActive(item) ? 'font-bold text-default-800' : 'text-default-600 dark:text-default-500'}
          ${nested ? ' pl-4' : ''}`}
      >
        {t(item.stringKey as any) as string}
      </button>
    </li>
  );

  const nestedNavigationItem = (item: SidebarItem) => (
    <>
      {navigationItem(item)}
      {item.subItems?.map((subItem) => navigationItem(subItem, true))}
    </>
  );

  const toggleLabel = isOpen
    ? (t('menu.actions.close') as string)
    : (t('menu.actions.open') as string);

  return (
    <nav className="flex h-16 items-center md:hidden">
      <Button
        isIconOnly
        variant="light"
        radius="sm"
        aria-label={toggleLabel}
        aria-expanded={isOpen}
        onPress={onOpenChange}
        className="h-full w-6 min-w-6 bg-transparent px-0
          data-[hover=true]:bg-transparent data-[pressed=true]:bg-transparent"
      >
        {isOpen ? <IconX /> : <IconMenu />}
      </Button>

      {isOpen && (
        <div
          className="fixed inset-x-0 bottom-0 top-16 z-30 overflow-y-auto
            bg-background/70 px-6 pt-2 backdrop-blur-xl backdrop-saturate-150"
        >
          <ul className="flex flex-col gap-2">
            {filteredMenuItems.map((item: SidebarItem) => (
              <Fragment key={item.stringKey}>
                {item.subItems
                  ? nestedNavigationItem(item)
                  : navigationItem(item)}
              </Fragment>
            ))}
          </ul>
        </div>
      )}
    </nav>
  );
};

export default MobileMenu;
