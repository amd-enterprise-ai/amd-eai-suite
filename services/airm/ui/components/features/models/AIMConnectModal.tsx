// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { Snippet, Tab, Tabs, Switch } from '@heroui/react';
import { IconCopy } from '@tabler/icons-react';
import React, { useState } from 'react';

import { useTranslation } from 'next-i18next';

import { Aim } from '@/types/aims';

import { Modal } from '@/components/shared/Modal/Modal';
import { ActionButton } from '@/components/shared/Buttons';

interface Props {
  onOpenChange: (isOpen: boolean) => void;
  onConfirmAction: (aim: Aim) => void;
  isOpen: boolean;
  aim: Aim | undefined;
}

const getCodeExamples = (
  url: string,
  canonicalName: string,
): Record<string, string> => ({
  curl: `curl -X POST "${url}" \\
  -H "Authorization: Bearer UPDATE_YOUR_API_KEY_HERE" \\
  -H "Content-Type: application/json" \\
  -d '{
    "model": "${canonicalName}",
    "messages": [
      {
        "content": "Hello",
        "role": "user"
      }
    ],
    "stream": false
  }'`,
  python: `import requests

url = "${url}"
headers = {
    "Authorization": "Bearer UPDATE_YOUR_API_KEY_HERE",
    "Content-Type": "application/json"
}
data = {
    "model": "${canonicalName}",
    "messages": [
        {"role": "user", "content": "Hello"}
    ],
    "stream": False
}

response = requests.post(url, headers=headers, json=data)
result = response.json()
print(result["choices"][0]["message"]["content"])`,
  javascript: `const url = '${url}';
const headers = {
  'Authorization': 'Bearer UPDATE_YOUR_API_KEY_HERE',
  'Content-Type': 'application/json'
};
const data = {
  model: '${canonicalName}',
  messages: [
    { role: 'user', content: 'Hello' }
  ],
  stream: false
};

fetch(url, {
  method: 'POST',
  headers: headers,
  body: JSON.stringify(data)
})
  .then(response => response.json())
  .then(result => console.log(result.choices[0].message.content))
  .catch(error => console.error('Error:', error));`,
});

const AIMConnectModal = ({
  onOpenChange,
  onConfirmAction,
  isOpen,
  aim,
}: Props) => {
  const { t } = useTranslation('models', { keyPrefix: 'aimCatalog' });
  const { t: tc } = useTranslation('common');
  const [selectedLanguage, setSelectedLanguage] = useState<string>('curl');
  const [useInternalUrl, setUseInternalUrl] = useState<boolean>(false);

  const handleClose = () => {
    if (onOpenChange) {
      onOpenChange(false);
    }
  };

  const handleConfirm = () => {
    if (aim && onConfirmAction) {
      onConfirmAction(aim);
      onOpenChange(false);
    }
  };

  const workload = aim?.workload;

  const externalUrl = workload?.output?.externalHost
    ? `${workload.output.externalHost}/v1/chat/completions`
    : '';

  const internalUrl = workload?.output?.internalHost
    ? `http://${workload.output.internalHost}/v1/chat/completions`
    : '';

  const urlToUse = useInternalUrl ? internalUrl : externalUrl;
  const codeExamples = getCodeExamples(urlToUse, aim?.canonicalName || '');
  const codeBlock = codeExamples[selectedLanguage] || codeExamples.curl;

  return (
    <>
      {isOpen && (
        <Modal
          size="xl"
          title={t('actions.connect.modal.title') as string}
          onClose={handleClose}
          footer={
            <>
              <ActionButton secondary onPress={handleClose}>
                {tc('actions.close.title')}
              </ActionButton>
              <ActionButton primary onPress={handleConfirm}>
                {t('actions.connect.modal.openChat')}
              </ActionButton>
            </>
          }
        >
          <div className="space-y-4">
            {externalUrl ? (
              <div>
                <label className="block text-sm text-foreground-500 mb-2">
                  {t('actions.connect.modal.externalUrl')}
                </label>
                <Snippet
                  symbol=""
                  classNames={{
                    base: 'w-full relative',
                    pre: 'whitespace-nowrap font-mono overflow-x-auto mr-6 my-1',
                    copyButton: 'absolute top-1 right-1',
                  }}
                  copyIcon={<IconCopy size={16} />}
                  aria-label={t('actions.connect.modal.externalUrl')}
                >
                  {externalUrl}
                </Snippet>
              </div>
            ) : null}

            <div>
              <label className="block text-sm text-foreground-500 mb-2">
                {t('actions.connect.modal.internalUrl')}
              </label>
              <Snippet
                symbol=""
                classNames={{
                  base: 'w-full relative',
                  pre: 'whitespace-nowrap font-mono overflow-x-auto mr-6 my-1',
                  copyButton: 'absolute top-1 right-1',
                }}
                copyIcon={<IconCopy size={16} />}
                aria-label={t('actions.connect.modal.internalUrl')}
              >
                {internalUrl}
              </Snippet>
            </div>

            <div>
              <h4 className="uppercase mb-2 mt-4 font-bold">
                {t('actions.connect.modal.codeTitle')}
              </h4>
              <label className="block text-sm font-medium text-foreground-500 mb-3">
                {t('actions.connect.modal.codeExample')}
              </label>
              <div className="flex items-center justify-between mb-3">
                <Switch
                  isSelected={useInternalUrl}
                  onValueChange={setUseInternalUrl}
                  size="sm"
                >
                  {t('actions.connect.modal.useInternalUrl')}
                </Switch>
              </div>
              <Tabs
                selectedKey={selectedLanguage}
                onSelectionChange={(key) => setSelectedLanguage(key as string)}
                aria-label={t('actions.connect.modal.codeExample')}
                className="mb-3"
              >
                <Tab
                  key="curl"
                  title={t('actions.connect.modal.languages.curl')}
                />
                <Tab
                  key="python"
                  title={t('actions.connect.modal.languages.python')}
                />
                <Tab
                  key="javascript"
                  title={t('actions.connect.modal.languages.javascript')}
                />
              </Tabs>
              <Snippet
                classNames={{
                  base: 'w-full relative',
                  pre: 'whitespace-pre-wrap font-mono',
                  copyButton: 'absolute top-1 right-1',
                }}
                copyIcon={<IconCopy size={16} />}
                aria-label={t('actions.connect.modal.codeExample')}
                symbol=""
              >
                {codeBlock}
              </Snippet>
            </div>
          </div>
        </Modal>
      )}
    </>
  );
};

export default AIMConnectModal;
