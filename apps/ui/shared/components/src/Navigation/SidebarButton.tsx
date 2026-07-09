// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import React, { FC, useMemo } from 'react';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useRouter } from 'next/router';
import { useTranslation } from 'next-i18next';

import { isMenuItemActive } from '@amdenterpriseai/utils/app';

import { buildProjectHref, stripProjectPrefix } from './project-utils';

interface Props {
  text: string;
  textColor?: string;
  href: string;
  isSidebarMini: boolean;
  icon?: React.ReactNode;
  nested?: boolean;
  projectPrefix?: string;
}

export const SidebarButton: FC<Props> = ({
  href,
  text,
  icon,
  isSidebarMini,
  nested,
  projectPrefix,
}) => {
  const { t } = useTranslation('common');
  const pathname = usePathname();
  const router = useRouter();

  const fullHref = useMemo(
    () => buildProjectHref(href, projectPrefix),
    [projectPrefix, href],
  );

  const pathWithoutProject = useMemo(
    () =>
      stripProjectPrefix(
        pathname,
        projectPrefix,
        router.locale,
        router.defaultLocale,
      ),
    [projectPrefix, pathname, router.locale, router.defaultLocale],
  );

  const content = (
    <div
      className={`flex w-full items-center tracking-tight ${
        isSidebarMini ? 'px-0 group-hover:px-2' : 'px-2'
      }`}
    >
      <span className="px-[14px]">{icon}</span>
      <span
        className={`${
          isSidebarMini
            ? 'scale-0 group-hover:scale-100'
            : 'block text-nowrap scale-100'
        }`}
      >
        {t(text as any) as string}
      </span>
    </div>
  );

  const isActive = isMenuItemActive(href, pathWithoutProject);
  let classNames =
    'bg-transparent dark:hover:bg-default-100 hover:bg-default-200';
  if (isActive && nested) {
    classNames += ' font-extrabold';
  } else if (isActive) {
    classNames =
      'bg-primary/15 hover:bg-primary/25 text-primary dark:text-primary-500';
  }

  return (
    <div
      className={`menu-item flex justify-center items-center max-h-12 text-sm rounded-md duration-10 w-full cursor-pointer
        ${classNames}
      `}
    >
      <Link
        className="w-full h-full py-3 text-nowrap outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2 focus-visible:ring-offset-background rounded-md"
        href={fullHref}
        role="link"
      >
        {content}
      </Link>
    </div>
  );
};
