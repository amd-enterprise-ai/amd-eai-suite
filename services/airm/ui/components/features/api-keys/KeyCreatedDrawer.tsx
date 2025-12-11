// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import {
  Alert,
  Button,
  Drawer,
  DrawerBody,
  DrawerContent,
  DrawerFooter,
  DrawerHeader,
  Input,
} from '@heroui/react';
import { IconCopy } from '@tabler/icons-react';
import { useTranslation } from 'next-i18next';

import { ApiKeyWithFullKey } from '@/types/api-keys';

import useSystemToast from '@/hooks/useSystemToast';

interface KeyCreatedDrawerProps {
  isOpen: boolean;
  apiKey: ApiKeyWithFullKey | null;
  onClose: () => void;
}

export const KeyCreatedDrawer: React.FC<KeyCreatedDrawerProps> = ({
  isOpen,
  apiKey,
  onClose,
}) => {
  const { t } = useTranslation('api-keys');
  const { toast } = useSystemToast();

  const handleCopy = async () => {
    if (!apiKey) return;
    try {
      await navigator.clipboard.writeText(apiKey.fullKey);
      toast.success(t('form.keyCreated.notification.copySuccess'));
    } catch {
      toast.error(t('form.keyCreated.notification.copyError'));
    }
  };

  if (!apiKey) return null;

  return (
    <Drawer isOpen={isOpen} onClose={onClose} size="md" placement="right">
      <DrawerContent>
        <DrawerHeader className="flex flex-col gap-1">
          <h2 className="text-xl font-semibold">
            {t('form.keyCreated.title')}
          </h2>
        </DrawerHeader>

        <DrawerBody>
          <div className="flex flex-col gap-4">
            {/* Description */}
            <p className="text-sm text-foreground-600">
              {t('form.keyCreated.description')}
            </p>

            {/* Warning Section */}
            <Alert
              color="danger"
              variant="solid"
              className="text-sm"
              description={t('form.keyCreated.warning')}
            />

            {/* Name Field */}
            <div className="flex flex-col gap-2">
              <label className="text-sm font-medium text-foreground-600">
                {t('form.keyCreated.field.name.label')}
              </label>
              <Input
                value={apiKey.name}
                isReadOnly
                variant="bordered"
                classNames={{
                  input: 'font-mono text-sm',
                }}
              />
            </div>

            {/* API Key Field */}
            <div className="flex flex-col gap-2">
              <label className="text-sm font-medium text-foreground-600">
                {t('form.keyCreated.field.key.label')}
              </label>
              <Input
                value={apiKey.fullKey}
                isReadOnly
                variant="bordered"
                classNames={{
                  input: 'font-mono text-sm',
                }}
                endContent={
                  <Button
                    isIconOnly
                    size="sm"
                    variant="light"
                    onPress={handleCopy}
                    aria-label={t('form.keyCreated.aria.copyButton')}
                  >
                    <IconCopy size={16} />
                  </Button>
                }
              />
            </div>
          </div>
        </DrawerBody>

        <DrawerFooter>
          <Button color="primary" onPress={onClose} className="w-full">
            {t('form.keyCreated.action.done')}
          </Button>
        </DrawerFooter>
      </DrawerContent>
    </Drawer>
  );
};

export default KeyCreatedDrawer;
