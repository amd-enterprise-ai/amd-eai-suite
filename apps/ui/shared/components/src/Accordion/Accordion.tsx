// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import {
  Accordion as HeroAccordion,
  AccordionItem,
  type AccordionProps,
  type AccordionItemProps,
} from '@heroui/react';

type AccordionWithSubComponents = typeof HeroAccordion & {
  Item: typeof AccordionItem;
};

const Accordion = HeroAccordion as AccordionWithSubComponents;
Accordion.Item = AccordionItem;

export { Accordion, AccordionItem };
export type { AccordionProps, AccordionItemProps };
