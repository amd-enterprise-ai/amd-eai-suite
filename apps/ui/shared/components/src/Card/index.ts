// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import {
  Card as CardBase,
  CardBody,
  CardHeader,
  CardFooter,
} from '@heroui/react';

type CardWithCompound = typeof CardBase & {
  Body: typeof CardBody;
  Header: typeof CardHeader;
  Footer: typeof CardFooter;
};

const Card = CardBase as CardWithCompound;
Card.Body = CardBody;
Card.Header = CardHeader;
Card.Footer = CardFooter;

export { Card, CardBody, CardHeader, CardFooter };
