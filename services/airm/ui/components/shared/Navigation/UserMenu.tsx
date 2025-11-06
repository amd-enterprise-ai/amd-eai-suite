// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import {
  Dropdown,
  DropdownItem,
  DropdownMenu,
  DropdownSection,
  DropdownTrigger,
  Switch,
  cn,
} from '@heroui/react';
import { IconLogout, IconMoon, IconSun, IconUser } from '@tabler/icons-react';
import { useSession } from 'next-auth/react';
import React from 'react';

import { useTranslation } from 'next-i18next';
import { useTheme } from 'next-themes';

import { logout } from '@/utils/app/auth';

interface Props {
  // Add any props you need for the usermenu here
}

export const UserMenu: React.FC<Props> = () => {
  const { data: session } = useSession();
  const { theme, setTheme } = useTheme();
  const { t } = useTranslation('common');

  const handleLogout = async () => {
    await logout();
  };

  return (
    <div>
      <Dropdown>
        <DropdownTrigger>
          <div className="flex items-center cursor-pointer gap-3 capitalize">
            <div className="hidden md:flex flex-col justify-start text-right">
              <span className="font-semibold text-sm text-default-800">
                {session?.user?.name}
              </span>
              <span className="text-nowrap text-xs lowercase text-default-500 font-normal">
                {session?.user?.email}
              </span>
            </div>
            <div className="border border-default-300 text-default-900 rounded-full min-w-8 h-8 flex justify-center items-center">
              <IconUser stroke="2" size={14} />
            </div>
          </div>
        </DropdownTrigger>
        <DropdownMenu aria-label="Static Actions">
          <DropdownSection
            aria-label={t('menu.actions.themeToggle') as string}
            showDivider
          >
            <DropdownItem
              isReadOnly
              className="cursor-default w-full"
              endContent={
                <Switch
                  defaultSelected
                  size="md"
                  color="primary"
                  isSelected={theme === 'light'}
                  startContent={<IconSun />}
                  endContent={<IconMoon />}
                  onValueChange={() =>
                    setTheme(theme === 'light' ? 'dark' : 'light')
                  }
                  classNames={{
                    base: cn(
                      'inline-flex m-0 justify-between flex-row-reverse w-full items-center',
                    ),
                    wrapper: 'm-0',
                  }}
                ></Switch>
              }
              key={''}
            >
              {t('menu.actions.theme', { theme: t(`theme.${theme}`) })}
            </DropdownItem>
          </DropdownSection>
          <DropdownItem
            onPress={handleLogout}
            endContent={<IconLogout size={16} stroke={2} />}
            key={'menu-logout'}
          >
            {t('menu.actions.logout')}
          </DropdownItem>
        </DropdownMenu>
      </Dropdown>
    </div>
  );
};
