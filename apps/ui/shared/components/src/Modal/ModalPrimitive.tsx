// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import {
  Modal as HeroUIModal,
  ModalBody as HeroUIModalBody,
  ModalContent as HeroUIModalContent,
  ModalFooter as HeroUIModalFooter,
  ModalHeader as HeroUIModalHeader,
} from '@heroui/react';

const ModalPrimitive = Object.assign(HeroUIModal, {
  Body: HeroUIModalBody,
  Content: HeroUIModalContent,
  Footer: HeroUIModalFooter,
  Header: HeroUIModalHeader,
});

export {
  ModalPrimitive,
  HeroUIModalBody as ModalPrimitiveBody,
  HeroUIModalContent as ModalPrimitiveContent,
  HeroUIModalFooter as ModalPrimitiveFooter,
  HeroUIModalHeader as ModalPrimitiveHeader,
};
