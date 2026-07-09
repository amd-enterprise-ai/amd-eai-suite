// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import {
  ActionButton,
  CopySnippet,
  Modal,
  Switch,
  Tab,
  Tabs,
} from '@amdenterpriseai/components';
import { IconCopy } from '@tabler/icons-react';
import { useState } from 'react';

import { useTranslation } from 'next-i18next';

import { useProject } from '@/contexts/ProjectContext';

interface Props {
  onOpenChange: (isOpen: boolean) => void;
  onChatRequested: (serviceId: string) => void;
  isOpen: boolean;
  serviceId?: string;
  endpoints?: { internal?: string; external?: string };
  modelName?: string;
}

const getCodeExamples = (
  url: string,
  modelName?: string,
  backend?: string,
): Record<string, string> => {
  const model = modelName ?? '';
  // Precise backend routing through the unified gateway: send the deployment UUID
  // and the model name as the x-ai-eg-backend / x-ai-eg-model headers so the
  // gateway's 3-condition route (host + x-ai-eg-backend + x-ai-eg-model) matches
  // at routing time and wins over the model-name fallback — which otherwise routes
  // by model name alone and can hit a different deployment when the same model is
  // deployed in another project. Only emitted when routing through the gateway.
  const curlRoutingHeaders = backend
    ? `  -H "x-ai-eg-backend: ${backend}" \\\n  -H "x-ai-eg-model: ${model}" \\\n`
    : '';
  const pythonRoutingHeaders = backend
    ? `    "x-ai-eg-backend": "${backend}",\n    "x-ai-eg-model": "${model}",\n`
    : '';
  const jsRoutingHeaders = backend
    ? `  'x-ai-eg-backend': '${backend}',\n  'x-ai-eg-model': '${model}',\n`
    : '';
  return {
    curl: `curl -X POST "${url}" \\
  -H "Authorization: Bearer UPDATE_YOUR_API_KEY_HERE" \\
  -H "Content-Type: application/json" \\
${curlRoutingHeaders}  -d '{
    "model": "${model}",
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
${pythonRoutingHeaders}    "Content-Type": "application/json"
}
data = {
    "model": "${model}",
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
${jsRoutingHeaders}  'Content-Type': 'application/json'
};
const data = {
  model: '${model}',
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
  };
};

const AIMConnectModal = ({
  onOpenChange,
  onChatRequested,
  isOpen,
  serviceId,
  endpoints,
  modelName,
}: Props) => {
  const { t } = useTranslation('models', { keyPrefix: 'aimCatalog' });
  const { t: tc } = useTranslation('common');
  const { aiGatewayEnabled, aiGatewayUrl } = useProject();
  const [selectedLanguage, setSelectedLanguage] = useState<string>('curl');
  const [useInternalUrl, setUseInternalUrl] = useState<boolean>(false);

  // When the unified Envoy AI Gateway is enabled and configured, inference goes
  // through a single endpoint (the model is selected via the OpenAI `model`
  // field), replacing the per-service external URL.
  const gatewayUrl =
    aiGatewayEnabled && aiGatewayUrl
      ? `${aiGatewayUrl.replace(/\/$/, '')}/v1/chat/completions`
      : '';
  const useGateway = !!gatewayUrl;

  const handleClose = () => {
    if (onOpenChange) {
      onOpenChange(false);
    }
  };

  const handleConfirm = () => {
    if (serviceId) {
      onChatRequested(serviceId);
      onOpenChange(false);
    }
  };

  const externalUrl = useGateway
    ? gatewayUrl
    : endpoints?.external
      ? `${endpoints.external}/v1/chat/completions`
      : '';

  // Label the primary URL as the unified inference endpoint when routing
  // through the gateway, otherwise as the per-service external URL.
  const externalUrlLabel = useGateway
    ? t('actions.connect.modal.inferenceUrl')
    : t('actions.connect.modal.externalUrl');

  const internalUrl = endpoints?.internal
    ? `${endpoints.internal}/v1/chat/completions`
    : '';

  const urlToUse = useInternalUrl ? internalUrl : externalUrl || internalUrl;
  // Only the unified gateway routes by the x-ai-eg-backend / x-ai-eg-model
  // headers; the per-service internal URL targets the deployment directly, so
  // emit the routing headers only when the snippet points at the gateway.
  const routeViaGateway = useGateway && !useInternalUrl;
  // Empty model when unresolved — a display-name fallback silently 404s.
  const codeExamples = getCodeExamples(
    urlToUse,
    modelName,
    routeViaGateway ? serviceId : undefined,
  );
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
              <ActionButton
                primary
                onPress={handleConfirm}
                isDisabled={!serviceId}
              >
                {t('actions.connect.modal.openChat')}
              </ActionButton>
            </>
          }
        >
          <div className="space-y-4">
            {externalUrl ? (
              <div>
                <label className="block text-sm text-foreground-500 mb-2">
                  {externalUrlLabel}
                </label>
                <CopySnippet
                  symbol=""
                  classNames={{
                    base: 'w-full relative',
                    pre: 'whitespace-nowrap font-mono overflow-x-auto mr-6 my-1',
                    copyButton: 'absolute top-1 right-1',
                  }}
                  copyIcon={<IconCopy size={16} />}
                  aria-label={externalUrlLabel}
                >
                  {externalUrl}
                </CopySnippet>
              </div>
            ) : null}
            <div>
              <label className="block text-sm text-foreground-500 mb-2">
                {t('actions.connect.modal.internalUrl')}
              </label>
              <CopySnippet
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
              </CopySnippet>
            </div>

            <div>
              <h4 className="uppercase mb-2 mt-4 font-bold">
                {t('actions.connect.modal.codeTitle')}
              </h4>
              <label className="block text-sm font-medium text-foreground-500 mb-3">
                {t('actions.connect.modal.codeExample')}
              </label>
              {externalUrl && (
                <div className="flex items-center justify-between mb-3">
                  <Switch
                    isSelected={useInternalUrl}
                    onValueChange={setUseInternalUrl}
                    size="sm"
                  >
                    {t('actions.connect.modal.useInternalUrl')}
                  </Switch>
                </div>
              )}
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
              <CopySnippet
                classNames={{
                  base: 'w-full relative',
                  pre: 'whitespace-pre-wrap font-mono',
                  copyButton: 'absolute top-1 right-1',
                }}
                copyIcon={<IconCopy size={16} />}
                aria-label={t('actions.connect.modal.codeExample')}
                data-testid="connect-code-snippet"
                symbol=""
              >
                {codeBlock}
              </CopySnippet>
            </div>
          </div>
        </Modal>
      )}
    </>
  );
};

export default AIMConnectModal;
