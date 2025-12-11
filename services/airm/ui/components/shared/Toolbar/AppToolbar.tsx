// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import {
  BreadcrumbItem,
  Breadcrumbs,
  Button,
  Link as HeroLink,
} from '@heroui/react';
import { IconExternalLink } from '@tabler/icons-react';

import { useTranslation } from 'next-i18next';
import { usePathname } from 'next/navigation';
import { useRouter } from 'next/router';

import { getDocumentationLink } from '@/utils/app/docs';
import { toCamelCase } from '@/utils/app/strings';

import { PageBreadcrumbs } from '@/types/navigation';

import { UserMenu } from '@/components/shared//Navigation/UserMenu';
import { MobileMenu } from '@/components/shared/Navigation/MobileMenu';

import { ProjectSelect } from '../Select/ProjectSelect';

interface AppBarProps {
  pageBreadcrumb?: PageBreadcrumbs;
}

export const AppBar: React.FC<AppBarProps> = ({ pageBreadcrumb }) => {
  const router = useRouter();
  const { pathname } = router;
  const { t } = useTranslation();
  const path = pathname.split('/').pop()?.replace(/^_/, '');
  const title = path
    ? t(`pages.${toCamelCase(path)}.title`)
    : t('pages.dashboard.title');
  const isAIWorkbench = pathname.match(
    /^(\/api-keys|\/chat|\/collections|\/datasets|\/workloads|\/models|\/workspaces|\/workbench-secrets)/,
  );
  let documentationHref = getDocumentationLink(usePathname());

  return (
    <div className="md:py-4 px-4 md:px-8 flex items-center justify-between w-full border-b border-default-200 dark:border-default-100">
      <div className="flex items-center">
        <MobileMenu />
        {pageBreadcrumb ? (
          <Breadcrumbs size="lg">
            {pageBreadcrumb.map((breadcrumb, idx) => (
              <BreadcrumbItem
                href={breadcrumb.href}
                key={`page-breadcrumb-${idx}`}
              >
                {breadcrumb.title}
              </BreadcrumbItem>
            ))}
          </Breadcrumbs>
        ) : (
          <div className="text-md font-semibold text-default-800 capitalize ml-6 sm:ml-3">
            {title}
          </div>
        )}
      </div>
      <div className="flex gap-3 md:gap-6 items-center">
        {isAIWorkbench && (
          <div>
            <ProjectSelect></ProjectSelect>
          </div>
        )}

        <Button
          as={HeroLink}
          isExternal
          variant="bordered"
          className="w-max border-1 border-default-200"
          size="sm"
          href={documentationHref}
        >
          {t('links.documentation')}
          <IconExternalLink size="14" stroke="2" />
        </Button>
        <UserMenu />
      </div>
    </div>
  );
};
