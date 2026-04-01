// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { Accordion, AccordionItem } from '@heroui/react';
import type { Selection } from '@heroui/react';
import { useTranslation } from 'next-i18next';
import { useLocalStorage } from '@amdenterpriseai/hooks';

import { RelevantDocsCard } from './RelevantDocsCard';
import { documentationMapping } from './documentation-mapping';

const STORAGE_KEY = 'relevantDocsAccordion';

/**
 * The component uses HeroUI's Accordion component to implement an expand/collapse block.
 * For controlling the state selected keys are used. Empty selection — closed, non-empty selection with AccordionItem in the array — open.
 */
const DEFAULT_VALUE = [STORAGE_KEY];

export interface RelevantDocsProps {
  page: string;
}

export const RelevantDocs = ({ page }: RelevantDocsProps) => {
  const { t } = useTranslation('sharedComponents', {
    keyPrefix: 'RelevantDocs',
  });
  const entries = documentationMapping[page];
  if (!entries || entries.length === 0) {
    return null;
  }
  const displayEntries = entries.slice(0, 3);
  const [storedKeys, setStoredKeys] = useLocalStorage<string[]>(
    STORAGE_KEY,
    DEFAULT_VALUE,
  );
  const selectedKeys = new Set(
    Array.isArray(storedKeys) ? storedKeys : DEFAULT_VALUE,
  );

  const handleToggle = (keys: Selection) =>
    setStoredKeys(
      keys instanceof Set ? Array.from(keys).map(String) : DEFAULT_VALUE,
    );

  return (
    <section className="mt-auto pt-4 pb-4 flex flex-col">
      <Accordion
        selectedKeys={selectedKeys}
        onSelectionChange={handleToggle}
        selectionMode="single"
        isCompact
      >
        <AccordionItem key={STORAGE_KEY} title={t('title')}>
          <div className="grid grid-cols-1 min-[1100px]:grid-cols-3 gap-4 w-full">
            {displayEntries.map((entry) => (
              <RelevantDocsCard key={entry.url} {...entry} />
            ))}
          </div>
        </AccordionItem>
      </Accordion>
    </section>
  );
};

RelevantDocs.displayName = 'RelevantDocs';
