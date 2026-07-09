// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { cn } from '@heroui/react';
import { Switch } from '@amdenterpriseai/components';
import {
  Dropdown,
  DropdownItem,
  DropdownMenu,
  DropdownSection,
  DropdownTrigger,
} from '../Dropdown/DropdownPrimitive';
import {
  IconFlag,
  IconLogout,
  IconMoon,
  IconSun,
  IconUser,
} from '@tabler/icons-react';
import { CollectionElement } from '@react-types/shared';
import { useSession } from 'next-auth/react';
import React from 'react';

import { useTranslation } from 'next-i18next';
import { useTheme } from 'next-themes';

import { useSystemInfo } from '@amdenterpriseai/hooks';
import { createMailtoLink, logout } from '@amdenterpriseai/utils/app';

interface UserMenuProps {
  additionalMenuItems?: CollectionElement<object>;
}

export const UserMenu: React.FC<UserMenuProps> = ({ additionalMenuItems }) => {
  const { data: session } = useSession();
  const { theme, setTheme } = useTheme();
  const { t } = useTranslation('common');
  const getSystemInfo = useSystemInfo();

  const handleLogout = async () => {
    await logout();
  };

  const reportIssueHref = createMailtoLink({
    subject: 'Issue report: [describe the problem shortly]',
    body: [
      'Issue:',
      '[Please describe the issue in detail, include steps to reproduce and what result was expected]',
      '',
      '--- System info ---',
      ...getSystemInfo(),
    ],
  });

  return (
    <div>
      <Dropdown>
        <DropdownTrigger>
          <div className="flex items-center cursor-pointer gap-3 capitalize outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2 focus-visible:ring-offset-background rounded-lg">
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
        <DropdownMenu aria-label={t('list.actions.label')}>
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
              {t('menu.actions.theme', {
                theme: t(`theme.${theme}` as any) as string,
              })}
            </DropdownItem>
          </DropdownSection>
          {additionalMenuItems ?? null}
          <DropdownItem
            as="a"
            href={reportIssueHref}
            endContent={<IconFlag size={16} stroke={2} />}
            key={'menu-report-issue'}
          >
            {t('menu.actions.reportIssue')}
          </DropdownItem>
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
