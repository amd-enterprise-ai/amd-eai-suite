// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { Link } from '@heroui/react';
import NextLink from 'next/link';
import { useTranslation } from 'next-i18next';

interface LinkToastProps {
  message: string;
  href: string;
}

export const LinkToast = ({ message, href }: LinkToastProps) => {
  const { t } = useTranslation('common');

  return (
    <div className="flex items-center gap-1 pr-3">
      {message} {'\u2008'}
      <Link as={NextLink} href={href} className="ml-1">
        {t('actions.showDetails.title')}
      </Link>
    </div>
  );
};

LinkToast.displayName = 'LinkToast';
