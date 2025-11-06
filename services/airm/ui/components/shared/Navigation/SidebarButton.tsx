// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import React, { FC } from 'react';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useTranslation } from 'next-i18next';

import { isMenuItemActive } from '@/utils/app/navigation';

interface Props {
  text: string;
  textColor?: string;
  href: string;
  isSidebarMini: boolean;
  icon?: React.ReactNode;
  nested?: boolean;
}

export const SidebarButton: FC<Props> = ({
  href,
  text,
  icon,
  isSidebarMini,
  nested,
}) => {
  const { t } = useTranslation('common');

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
        {t(text)}
      </span>
    </div>
  );
  const pathname = usePathname();

  const isActive = isMenuItemActive(href, pathname);
  let classNames =
    'bg-transparent dark:hover:bg-default-100 hover:bg-default-200';
  if (isActive && nested) {
    classNames += ' font-extrabold';
  } else if (isActive) {
    classNames =
      'bg-primary-200/75 hover:bg-primary-300/50 text-primary dark:bg-primary-900/25 dark:hover:bg-primary-800/25 dark:text-primary-400';
  }

  return (
    <div
      className={`menu-item flex justify-center items-center max-h-12 text-sm rounded-md duration-10 w-full cursor-pointer
        ${classNames}
      `}
    >
      <Link className="w-full h-full py-3 text-nowrap" href={href} role="link">
        {content}
      </Link>
    </div>
  );
};
