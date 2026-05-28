// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT
//
// This file is auto-generated. Do not edit manually.
// Run 'pnpm i18n:types' to regenerate.

// ============================================================================
// i18next Key Type Enforcement — Flat Key Unions + Module Augmentation
// ============================================================================
// Flat key union types document all valid translation key paths per namespace.
// Use them for IDE autocomplete or typed wrapper functions (opt-in).
//
// The i18next module augmentation enables compile-time key validation via
// nested object types for each namespace. Passing an unknown key to t() is a
// TypeScript error. Nested types (not Record<flat, string>) are required so
// i18next's ParseKeys<Ns, TOpt> can resolve Keys[Ns] to the concrete structure
// rather than unknown when TOpt is a generic type variable in TFunctionStrict.
//
// Shared components that accept TFunction as a prop use a plain callable type
// to avoid $TFunctionBrand incompatibility across namespaces:
//   translation: (key: string, options?: Record<string, unknown>) => string
//
// WHY export {}:
// TypeScript distinguishes between script files (no imports/exports) and module
// files. In a script file, 'declare module "i18next"' is an ambient module
// declaration (declares a new module), NOT a module augmentation (adds to an
// existing module). Only module files produce proper augmentations. Adding
// 'export {}' makes this file a module, so the 'declare module "i18next"' block
// correctly augments the i18next package's CustomTypeOptions interface.
// ============================================================================

// Required to make this a module file so 'declare module "i18next"' below is
// a module augmentation (not an ambient module declaration).
export {};

// Flat key unions — one per namespace (for documentation and wrapper functions)
export type api_keysKeys =
  | 'list.title'
  | 'list.clusterAuthDisabled'
  | 'list.filters.search.placeholder'
  | 'list.actions.create.title'
  | 'list.actions.edit.title'
  | 'list.actions.delete.title'
  | 'list.actions.delete.confirmation.title'
  | 'list.actions.delete.confirmation.description'
  | 'list.actions.delete.notification.success'
  | 'list.actions.delete.notification.error'
  | 'list.apiKeys.headers.name.title'
  | 'list.apiKeys.headers.secretKey.title'
  | 'list.apiKeys.headers.createdAt.title'
  | 'list.apiKeys.headers.createdBy.title'
  | 'list.apiKeys.headers.actions.title'
  | 'list.apiKeys.empty.description'
  | 'list.apiKeys.pagination.showing'
  | 'list.apiKeys.pagination.pageSize.label'
  | 'list.apiKeys.pagination.pageSize.entities'
  | 'form.create.title'
  | 'form.create.action.create'
  | 'form.create.action.cancel'
  | 'form.create.field.name.label'
  | 'form.create.field.name.placeholder'
  | 'form.create.field.name.error.minLength'
  | 'form.create.field.name.error.maxLength'
  | 'form.create.field.expiresAt.label'
  | 'form.create.field.validityPeriod.label'
  | 'form.create.field.validityPeriod.placeholder'
  | 'form.create.field.validityPeriod.description'
  | 'form.create.field.validityPeriod.options.1day'
  | 'form.create.field.validityPeriod.options.1week'
  | 'form.create.field.validityPeriod.options.2weeks'
  | 'form.create.field.validityPeriod.options.30days'
  | 'form.create.field.validityPeriod.options.60days'
  | 'form.create.field.validityPeriod.options.90days'
  | 'form.create.field.validityPeriod.options.never'
  | 'form.create.field.modelDeployment.label'
  | 'form.create.field.modelDeployment.placeholder'
  | 'form.create.field.modelDeployment.description'
  | 'form.create.section.endpointAccess'
  | 'form.create.notification.success'
  | 'form.create.notification.error'
  | 'form.edit.title'
  | 'form.edit.action.save'
  | 'form.edit.action.cancel'
  | 'form.edit.section.linkedDeployments'
  | 'form.edit.section.noLinkedDeployments'
  | 'form.edit.notification.success'
  | 'form.edit.notification.error'
  | 'form.edit.warning.linkedDeploymentsWarning'
  | 'form.keyCreated.title'
  | 'form.keyCreated.description'
  | 'form.keyCreated.warning'
  | 'form.keyCreated.field.name.label'
  | 'form.keyCreated.field.key.label'
  | 'form.keyCreated.action.done'
  | 'form.keyCreated.notification.copySuccess'
  | 'form.keyCreated.notification.copyError'
  | 'form.keyCreated.aria.copyButton';

export type autoscalingKeys =
  | 'title'
  | 'settingsTitle'
  | 'enable'
  | 'helper'
  | 'description'
  | 'replicaRange'
  | 'replicasMinimum'
  | 'scalingMetric.label'
  | 'scalingMetric.placeholder'
  | 'scalingMetric.defaultDescription'
  | 'scalingMetric.options.runningRequests'
  | 'scalingMetric.options.waitingRequests'
  | 'scalingMetric.descriptions.runningRequests'
  | 'scalingMetric.descriptions.waitingRequests'
  | 'aggregation.label'
  | 'aggregation.placeholder'
  | 'aggregation.description'
  | 'aggregation.options.avg'
  | 'aggregation.options.max'
  | 'aggregation.options.min'
  | 'aggregation.tooltips.avg'
  | 'aggregation.tooltips.max'
  | 'aggregation.tooltips.min'
  | 'targetType.label'
  | 'targetType.placeholder'
  | 'targetType.description'
  | 'targetType.options.value'
  | 'targetType.options.averageValue'
  | 'targetType.tooltips.value'
  | 'targetType.tooltips.averageValue'
  | 'targetValue.label'
  | 'targetValue.descriptions.value'
  | 'targetValue.descriptions.averageValue'
  | 'podPhase.running'
  | 'podPhase.pending'
  | 'podPhase.succeeded'
  | 'podPhase.failed'
  | 'podPhase.unknown'
  | 'replicas.toggle'
  | 'list.replicas.headers.name.title'
  | 'list.replicas.headers.status.title'
  | 'list.replicas.headers.gpuCount.title'
  | 'list.replicas.headers.createdAt.title'
  | 'list.replicas.empty.description'
  | 'actions.cancel'
  | 'actions.save'
  | 'actions.settings'
  | 'notifications.noWorkloadId'
  | 'notifications.updateSuccess'
  | 'notifications.updateError'
  | 'notifications.convergenceTimeout';

export type catalogKeys =
  | 'actions.search.placeholder'
  | 'actions.search.label'
  | 'actions.categoryFilter.label'
  | 'actions.refresh'
  | 'categories.development'
  | 'categories.mlops'
  | 'categories.genai'
  | 'card.tagsMoreCount'
  | 'card.moreInformation'
  | 'list.actions.deploy'
  | 'list.actions.pending'
  | 'list.actions.launch'
  | 'list.actions.view'
  | 'list.actions.details'
  | 'list.actions.undeploy'
  | 'list.actions.deleteFailedWorkload'
  | 'list.errors.undeployError'
  | 'list.errors.noRunningWorkload'
  | 'list.notifications.undeploySuccess'
  | 'status.Complete'
  | 'status.Degraded'
  | 'status.Failed'
  | 'status.Deleting'
  | 'status.Deleted'
  | 'status.Pending'
  | 'status.Running'
  | 'status.Starting'
  | 'status.Unknown'
  | 'deployModal.title'
  | 'deployModal.settings.title'
  | 'deployModal.settings.displayName.label'
  | 'deployModal.settings.displayName.placeholder'
  | 'deployModal.settings.displayName.emptyNameError'
  | 'deployModal.settings.containerImage.label'
  | 'deployModal.settings.containerImage.tooltip'
  | 'deployModal.settings.containerImage.emptyNameError'
  | 'deployModal.settings.containerImage.formatError'
  | 'deployModal.settings.imagePullSecrets.label'
  | 'deployModal.settings.imagePullSecrets.tooltip'
  | 'deployModal.settings.imagePullSecrets.placeholder'
  | 'deployModal.settings.imagePullSecrets.noSecrets'
  | 'deployModal.settings.resourceAllocation.req'
  | 'deployModal.settings.resourceAllocation.belowRequiredWarning'
  | 'deployModal.settings.resourceAllocation.exceedsQuotaWarning'
  | 'deployModal.settings.resourceAllocation.belowRequiredExceedsQuotaWarning'
  | 'deployModal.settings.resourceAllocation.belowRequiredTooltip'
  | 'deployModal.settings.resourceAllocation.exceedsQuotaTooltip'
  | 'deployModal.settings.resourceAllocation.belowRequiredExceedsQuotaTooltip'
  | 'deployModal.settings.resourceAllocation.perGPU'
  | 'deployModal.settings.resourceAllocation.quotaFormatted'
  | 'deployModal.settings.resourceAllocation.cpuFormattedValue_one'
  | 'deployModal.settings.resourceAllocation.cpuFormattedValue_other'
  | 'deployModal.settings.resourceAllocation.ramFormattedValue'
  | 'deployModal.settings.resourceAllocation.ramLabel'
  | 'deployModal.settings.resourceAllocation.gpuLabel'
  | 'deployModal.settings.resourceAllocation.cpuLabel'
  | 'deployModal.settings.resourceAllocation.label'
  | 'deployModal.settings.resourceAllocation.totalResourceAllocation'
  | 'deployModal.settings.resourceAllocation.gpuCount'
  | 'deployModal.settings.resourceAllocation.gpuCountValue'
  | 'deployModal.settings.resourceAllocation.systemMemory'
  | 'deployModal.settings.resourceAllocation.systemMemoryValue'
  | 'deployModal.settings.resourceAllocation.cpuCoreCount'
  | 'deployModal.settings.resourceAllocation.cpuCoreCountValue'
  | 'deployModal.deploymentStatus.deployingMessage'
  | 'deployModal.deploymentStatus.readyMessage'
  | 'deployModal.deploymentStatus.launchButtonReady'
  | 'deployModal.deploymentStatus.launchButtonPending'
  | 'deployModal.actions.deploy'
  | 'deployModal.actions.cancel'
  | 'undeployModal.title'
  | 'undeployModal.description'
  | 'notifications.deployWorkload.success'
  | 'notifications.deployWorkload.error';

export type chatKeys =
  | 'title'
  | 'edit.saveAndSubmit'
  | 'edit.cancel'
  | 'modes.chat'
  | 'modes.compare'
  | 'chat.title'
  | 'chat.description'
  | 'chat.tips.tip1'
  | 'chat.tips.tip2'
  | 'chat.tips.tip3'
  | 'compare.title'
  | 'compare.description'
  | 'compare.tips.tip1'
  | 'compare.tips.tip2'
  | 'compare.tips.tip3'
  | 'roles.user'
  | 'roles.assistant'
  | 'roles.system'
  | 'modelSettings.title'
  | 'modelSettings.selectModel'
  | 'modelSettings.syncSettings.label'
  | 'modelSettings.syncSettings.description'
  | 'modelSettings.enableRag.label'
  | 'modelSettings.enableRag.description'
  | 'modelSettings.collection.label'
  | 'modelSettings.collection.description'
  | 'modelSettings.collection.tooltip'
  | 'modelSettings.documentCount.label'
  | 'modelSettings.documentCount.description'
  | 'modelSettings.documentCount.tooltip'
  | 'modelSettings.hybridSearch.label'
  | 'modelSettings.hybridSearch.description'
  | 'modelSettings.hybridSearch.tooltip'
  | 'modelSettings.alpha.label'
  | 'modelSettings.alpha.description'
  | 'modelSettings.alpha.tooltip'
  | 'modelSettings.certainty.label'
  | 'modelSettings.certainty.description'
  | 'modelSettings.certainty.tooltip'
  | 'modelSettings.userPromptTemplate.label'
  | 'modelSettings.userPromptTemplate.description'
  | 'modelSettings.userPromptTemplate.placeholder'
  | 'modelSettings.userPromptTemplate.tooltip'
  | 'modelSettings.userPromptTemplate.validationErrorMessage'
  | 'modelSettings.temperature.label'
  | 'modelSettings.temperature.description'
  | 'modelSettings.temperature.tooltip'
  | 'modelSettings.frequencyPenalty.label'
  | 'modelSettings.frequencyPenalty.description'
  | 'modelSettings.frequencyPenalty.tooltip'
  | 'modelSettings.presencePenalty.label'
  | 'modelSettings.presencePenalty.description'
  | 'modelSettings.presencePenalty.tooltip'
  | 'modelSettings.systemPrompt.label'
  | 'modelSettings.systemPrompt.placeholder'
  | 'modelSettings.systemPrompt.description'
  | 'modelSettings.systemPrompt.tooltip'
  | 'chatInput.placeholder'
  | 'chatInput.placeholderDisabled'
  | 'chatInput.regenerateResponse'
  | 'chatInput.attachImages'
  | 'chatInput.attachImage'
  | 'chatInput.removeImage'
  | 'chatInput.attachedImageAlt'
  | 'chatInput.dropImages'
  | 'actions.selectModel'
  | 'actions.clearAll'
  | 'errors.modelLoadingFailed'
  | 'errors.workloadLoadingFailed'
  | 'errors.chatResponseFailed'
  | 'errors.invalidImageFile'
  | 'errors.imageTooLarge'
  | 'errors.totalAttachmentTooLarge'
  | 'errors.failedToReadImage'
  | 'errors.failedToSendMessage'
  | 'notifications.delayedResponse'
  | 'debugInfoModal.title'
  | 'debugInfoModal.subTitle'
  | 'debugInfoModal.ragDocumentsTitle'
  | 'debugInfoModal.ragDocumentsDescription'
  | 'debugInfoModal.noSources'
  | 'debugInfoModal.promptsTitle'
  | 'debugInfoModal.promptsDescription'
  | 'debugInfoModal.noPromptMessages'
  | 'debugInfoModal.tokenUsageTitle'
  | 'debugInfoModal.promptTokens'
  | 'debugInfoModal.completionTokens'
  | 'debugInfoModal.totalTokens'
  | 'debugInfoModal.noTokenUsage';

export type clustersKeys =
  | 'title'
  | 'connectCluster.title'
  | 'connectCluster.start.title'
  | 'connectCluster.start.content.description'
  | 'connectCluster.start.content.confirmation'
  | 'connectCluster.start.actions.cancel'
  | 'connectCluster.start.actions.next'
  | 'connectCluster.script.title'
  | 'connectCluster.script.content.description'
  | 'connectCluster.script.content.note'
  | 'connectCluster.script.content.confirmation'
  | 'connectCluster.script.actions.next'
  | 'connectCluster.final.title'
  | 'connectCluster.final.content.description'
  | 'connectCluster.final.content.instruction'
  | 'connectCluster.final.content.helppage'
  | 'connectCluster.final.actions.complete'
  | 'connectCluster.notifications.failure'
  | 'form.edit.title'
  | 'form.edit.field.workbenchBaseUrl.label'
  | 'form.edit.field.workbenchBaseUrl.placeholder'
  | 'form.edit.field.workbenchBaseUrl.emptyError'
  | 'form.edit.field.workbenchBaseUrl.error.invalid'
  | 'form.edit.field.kubeApiUrl.label'
  | 'form.edit.field.kubeApiUrl.placeholder'
  | 'form.edit.field.kubeApiUrl.emptyError'
  | 'form.edit.field.kubeApiUrl.error.invalid'
  | 'form.edit.action.cancel'
  | 'form.edit.action.save'
  | 'form.edit.notification.success'
  | 'form.edit.notification.error'
  | 'config.button'
  | 'config.title'
  | 'config.description'
  | 'config.disabled'
  | 'list.pending.title'
  | 'list.pending.headers.requestedAt.title'
  | 'list.pending.headers.requestExpiry.title'
  | 'list.pending.headers.status.title'
  | 'list.pending.headers.actions.title'
  | 'list.pending.empty.description'
  | 'list.pending.pagination.showing'
  | 'list.pending.pagination.pageSize.label'
  | 'list.pending.pagination.pageSize.entities'
  | 'list.pending.actions.cancel'
  | 'list.active.title'
  | 'list.headers.name.title'
  | 'list.headers.status.title'
  | 'list.headers.nodes.title'
  | 'list.headers.nodes.description'
  | 'list.headers.gpuAllocation.title'
  | 'list.headers.cpuAllocation.title'
  | 'list.headers.memoryAllocation.title'
  | 'list.headers.actions.title'
  | 'list.filter.search.placeholder'
  | 'list.filter.status.placeholder'
  | 'list.pagination.showing'
  | 'list.pagination.pageSize.label'
  | 'list.pagination.pageSize.entities'
  | 'list.sort.name.asc'
  | 'list.sort.name.desc'
  | 'list.sort.status.asc'
  | 'list.sort.status.desc'
  | 'list.empty.description'
  | 'list.actions.delete.label'
  | 'list.actions.delete.confirmation.title'
  | 'list.actions.delete.confirmation.description'
  | 'list.actions.delete.notification.success'
  | 'list.actions.delete.notification.error'
  | 'list.actions.edit.label'
  | 'list.actions.cancel.label'
  | 'list.actions.cancel.confirmation.title'
  | 'list.actions.cancel.confirmation.description'
  | 'list.actions.cancel.notification.success'
  | 'list.actions.cancel.notification.error'
  | 'list.workloads.title'
  | 'list.workloads.empty.description'
  | 'list.workloads.headers.displayName.title'
  | 'list.workloads.headers.projectId.title'
  | 'list.workloads.headers.type.title'
  | 'list.workloads.headers.status.title'
  | 'list.workloads.headers.gpuCount.title'
  | 'list.workloads.headers.vram.title'
  | 'list.workloads.headers.createdAt.title'
  | 'list.workloads.headers.createdBy.title'
  | 'list.workloads.headers.actions.title'
  | 'list.workloads.actions.delete.title'
  | 'list.workloads.actions.delete.notification.success'
  | 'list.workloads.actions.delete.notification.error'
  | 'list.workloads.pagination.showing'
  | 'list.workloads.pagination.pageSize.label'
  | 'list.workloads.pagination.pageSize.entities'
  | 'nodes.title'
  | 'nodes.list.headers.name.title'
  | 'nodes.list.headers.status.title'
  | 'nodes.list.headers.cpuMilliCores.title'
  | 'nodes.list.headers.memoryBytes.title'
  | 'nodes.list.headers.gpuName.title'
  | 'nodes.list.headers.gpuCount.title'
  | 'nodes.list.headers.gpuMemory.title'
  | 'nodes.list.filter.placeholder'
  | 'nodes.list.pagination.showing'
  | 'nodes.list.pagination.pageSize.label'
  | 'nodes.list.pagination.pageSize.entities'
  | 'nodes.list.empty.description'
  | 'projects.title'
  | 'statistics.cluster.nodes.title'
  | 'statistics.cluster.nodes.tooltip'
  | 'statistics.cluster.projects.title'
  | 'statistics.cluster.projects.tooltip'
  | 'statistics.cluster.gpus.title'
  | 'statistics.cluster.gpus.tooltip'
  | 'statistics.cluster.workloads.title'
  | 'statistics.cluster.workloads.tooltip'
  | 'statistics.clusters.clusters.title'
  | 'statistics.clusters.clusters.tooltip'
  | 'statistics.clusters.nodes.title'
  | 'statistics.clusters.nodes.tooltip'
  | 'statistics.clusters.gpus.title'
  | 'statistics.clusters.gpus.tooltip'
  | 'statistics.clusters.workloads.title'
  | 'statistics.clusters.workloads.tooltip'
  | 'allocationAndWorkloads.charts.gpuDeviceUtilization.title'
  | 'dashboard.overview.workloadStates.title'
  | 'dashboard.overview.workloadStates.total'
  | 'dashboard.overview.workloadStates.subtitle'
  | 'dashboard.workloads.title'
  | 'workloads.title'
  | 'workloads.actions.view'
  | 'workloads.actions.back'
  | 'actions.connect'
  | 'status.healthy'
  | 'status.unhealthy'
  | 'status.verifying';

export type collectionsKeys =
  | 'title'
  | 'collections.select.label'
  | 'collections.select.placeholder'
  | 'collections.infoPanel.title'
  | 'collections.infoPanel.fields.name'
  | 'collections.infoPanel.fields.organization'
  | 'collections.infoPanel.fields.createdOn'
  | 'collections.infoPanel.fields.embeddings'
  | 'collections.infoPanel.fields.chunkSize'
  | 'collections.infoPanel.fields.chunkOverlap'
  | 'collections.infoPanel.fields.contentAwareness'
  | 'collections.infoPanel.enabled'
  | 'collections.infoPanel.disabled'
  | 'collections.messages.failed'
  | 'collections.actions.title'
  | 'collections.actions.label'
  | 'collections.actions.description'
  | 'collections.actions.scrape'
  | 'collections.actions.upload'
  | 'collections.actions.deleteSelected'
  | 'collections.actions.refresh.label'
  | 'collections.delete.title'
  | 'collections.delete.description'
  | 'collections.delete.messages.success'
  | 'collections.delete.messages.delete'
  | 'collections.errors.noCollection.title'
  | 'collections.errors.noCollection.description'
  | 'documents.title'
  | 'documents.list.headers.author.title'
  | 'documents.list.headers.documentId.title'
  | 'documents.list.headers.createdAt.title'
  | 'documents.list.headers.updatedAt.title'
  | 'documents.list.empty.title'
  | 'documents.list.empty.description'
  | 'documents.messages.failed'
  | 'documents.search.label'
  | 'documents.search.placeholder'
  | 'documents.search.clear'
  | 'jobs.title'
  | 'jobs.list.headers.jobType.title'
  | 'jobs.list.headers.status.title'
  | 'jobs.list.headers.createdAt.title'
  | 'jobs.list.headers.totalIndexedFailed.title'
  | 'jobs.list.empty.title'
  | 'jobs.list.empty.description'
  | 'jobs.messages.failed'
  | 'modals.fileUpload.action'
  | 'modals.fileUpload.dragAndDrop'
  | 'modals.newCollection.title'
  | 'modals.newCollection.description'
  | 'modals.newCollection.form.name.label'
  | 'modals.newCollection.form.name.placeholder'
  | 'modals.newCollection.form.name.error'
  | 'modals.newCollection.form.embeddingServer.label'
  | 'modals.newCollection.form.embeddingServer.placeholder'
  | 'modals.newCollection.form.chunkSize.label'
  | 'modals.newCollection.form.chunkSize.subLabel'
  | 'modals.newCollection.form.chunkSize.description'
  | 'modals.newCollection.form.chunkSize.placeholder'
  | 'modals.newCollection.form.chunkSize.error'
  | 'modals.newCollection.form.overlap.label'
  | 'modals.newCollection.form.overlap.subLabel'
  | 'modals.newCollection.form.overlap.description'
  | 'modals.newCollection.form.overlap.error'
  | 'modals.newCollection.form.contentAware.label'
  | 'modals.newCollection.form.contentAware.subLabel'
  | 'modals.newCollection.form.contentAware.description'
  | 'modals.newCollection.form.seeAdvanced.title'
  | 'modals.newCollection.messages.success'
  | 'modals.newCollection.messages.errors.embeddingServers'
  | 'modals.newCollection.messages.errors.uniqueName'
  | 'modals.newCollection.messages.errors.collection'
  | 'modals.deleteDocuments.title'
  | 'modals.deleteDocuments.description'
  | 'modals.deleteDocuments.messages.success'
  | 'modals.deleteDocuments.messages.delete'
  | 'modals.scrapeWebsite.title'
  | 'modals.scrapeWebsite.subTitle'
  | 'modals.scrapeWebsite.description'
  | 'modals.scrapeWebsite.form.url.label'
  | 'modals.scrapeWebsite.form.pages.label'
  | 'modals.scrapeWebsite.messages.success'
  | 'modals.scrapeWebsite.messages.failed'
  | 'modals.uploadZip.title'
  | 'modals.uploadZip.subTitle'
  | 'modals.uploadZip.helpText'
  | 'modals.uploadZip.form.host.label'
  | 'modals.uploadZip.form.host.placeholder'
  | 'modals.uploadZip.messages.success'
  | 'modals.uploadZip.messages.saveFailed'
  | 'modals.uploadZip.messages.uploadFailed'
  | 'modals.uploadZip.errors.activeJob'
  | 'modals.uploadZip.errors.oneZipFile'
  | 'modals.uploadZip.errors.maxFiles'
  | 'modals.uploadZip.errors.validation';

export type commonKeys =
  | 'app.title'
  | 'sections.aiWorkbench.title'
  | 'sections.resourceManagement.title'
  | 'sharedComponents.filterDropdown.selectAll.label'
  | 'sharedComponents.FormFileUpload.remove'
  | 'sharedComponents.FormFileUpload.add_one'
  | 'sharedComponents.FormFileUpload.add_other'
  | 'sharedComponents.FormFileUpload.drop_one'
  | 'sharedComponents.FormFileUpload.drop_other'
  | 'sharedComponents.FormFileUpload.dropFail_one'
  | 'sharedComponents.FormFileUpload.dropFail_other'
  | 'sharedComponents.FormFileUpload.footerFiles_one'
  | 'sharedComponents.FormFileUpload.footerFiles_other'
  | 'pages.collections.title'
  | 'pages.dashboard.title'
  | 'pages.clusters.title'
  | 'pages.projects.title'
  | 'pages.secrets.title'
  | 'pages.storages.title'
  | 'pages.chat.title'
  | 'pages.models.title'
  | 'pages.aimCatalog.title'
  | 'pages.customModels.title'
  | 'pages.deployedModels.title'
  | 'pages.datasets.title'
  | 'pages.workloads.title'
  | 'pages.workspaces.title'
  | 'pages.workbenchSecrets.title'
  | 'pages.accessControl.title'
  | 'pages.users.title'
  | 'pages.apiKeys.title'
  | 'pages.error.title'
  | 'menu.actions.open'
  | 'menu.actions.close'
  | 'menu.actions.themeToggle'
  | 'menu.actions.theme'
  | 'menu.actions.logout'
  | 'menu.actions.reportIssue'
  | 'actions.add'
  | 'actions.back.title'
  | 'actions.confirm.title'
  | 'actions.confirm.message'
  | 'actions.close.title'
  | 'actions.cancel.title'
  | 'actions.clear.title'
  | 'actions.copy.title'
  | 'actions.clearFilters.title'
  | 'actions.create.title'
  | 'actions.delete.title'
  | 'actions.download.title'
  | 'actions.next'
  | 'actions.previous'
  | 'actions.refresh.title'
  | 'actions.remove.title'
  | 'actions.save.title'
  | 'actions.showDetails.title'
  | 'actions.start.title'
  | 'actions.upload.title'
  | 'list.actions.label'
  | 'list.actions.assign.label'
  | 'list.actions.delete.label'
  | 'theme.light'
  | 'theme.dark'
  | 'links.home'
  | 'links.documentation'
  | 'links.support'
  | 'links.about'
  | 'error.label'
  | 'error.noSubmittableProjects.title'
  | 'error.noSubmittableProjects.description'
  | 'error.fetchFailed.title'
  | 'error.fetchFailed.description'
  | 'error.service.title'
  | 'error.service.description'
  | 'error.projectNotFound.title'
  | 'error.projectNotFound.description'
  | 'error.unknown.title'
  | 'error.unknown.description'
  | 'error.refreshActionLabel'
  | 'error.misc.unknownEntity'
  | 'error.misc.unknownError'
  | 'error.api.requestFailed'
  | 'error.api.noProjectSelected'
  | 'error.api.projectIdRequired'
  | 'statistics.upperLimitPrefix'
  | 'statistics.noData'
  | 'projectSelection.placeholder'
  | 'projectSelection.label'
  | 'projectSelection.tooltip'
  | 'projectSelectPrompt.title'
  | 'projectSelectPrompt.description'
  | 'timeRange.description'
  | 'timeRange.range.15m'
  | 'timeRange.range.30m'
  | 'timeRange.range.1h'
  | 'timeRange.range.24h'
  | 'timeRange.range.7d'
  | 'timeRange.lastUpdated'
  | 'charts.category.others'
  | 'charts.loading'
  | 'charts.nodata'
  | 'charts.refresh'
  | 'charts.refreshing'
  | 'data.lastUpdated'
  | 'data.refresh'
  | 'data.refreshing'
  | 'status.description'
  | 'status.errorDetail.title'
  | 'status.errorDetail.action.next'
  | 'status.errorDetail.action.prev'
  | 'password.showPassword'
  | 'password.hidePassword'
  | 'userMenu.airmAppLabel'
  | 'requestSoftware.model.title'
  | 'requestSoftware.model.description'
  | 'requestSoftware.model.button'
  | 'requestSoftware.workspace.title'
  | 'requestSoftware.workspace.description'
  | 'requestSoftware.workspace.button';

export type dashboardKeys =
  | 'title'
  | 'clusterAndNodes.title'
  | 'clusterAndNodes.cards.clusters.title'
  | 'clusterAndNodes.cards.clusters.tooltip'
  | 'clusterAndNodes.cards.gpuNodes.title'
  | 'clusterAndNodes.cards.gpuNodes.tooltip'
  | 'clusterAndNodes.cards.availableGPUs.title'
  | 'clusterAndNodes.cards.availableGPUs.tooltip'
  | 'clusterAndNodes.cards.allocatedGPUs.title'
  | 'clusterAndNodes.cards.allocatedGPUs.tooltip'
  | 'list.headers.name.title'
  | 'list.headers.gpuAllocation.title'
  | 'list.headers.gpuUtilization.title'
  | 'list.headers.running.title'
  | 'list.headers.pending.title'
  | 'list.headers.actions.title'
  | 'list.actions.open.label'
  | 'list.empty.description'
  | 'list.pagination.showing'
  | 'list.pagination.pageSize.label'
  | 'list.pagination.pageSize.entities'
  | 'allocationAndWorkloads.title'
  | 'allocationAndWorkloads.consumptionByProject.title'
  | 'allocationAndWorkloads.cards.gpuUtilization.title'
  | 'allocationAndWorkloads.cards.gpuUtilization.tooltip'
  | 'allocationAndWorkloads.cards.runningWorkloads.title'
  | 'allocationAndWorkloads.cards.runningWorkloads.tooltip'
  | 'allocationAndWorkloads.cards.pendingWorkloads.title'
  | 'allocationAndWorkloads.cards.pendingWorkloads.tooltip'
  | 'allocationAndWorkloads.charts.gpuMemoryUtilization.title'
  | 'allocationAndWorkloads.charts.gpuDeviceUtilization.title';

export type datasetsKeys =
  | 'title'
  | 'list.headers.type.title'
  | 'list.headers.name.title'
  | 'list.headers.description.title'
  | 'list.headers.organization.title'
  | 'list.headers.createdBy.title'
  | 'list.headers.createdAt.title'
  | 'list.headers.actions.title'
  | 'list.pagination.showing'
  | 'list.pagination.pageSize.label'
  | 'list.pagination.pageSize.entities'
  | 'list.sort.name.asc'
  | 'list.sort.name.desc'
  | 'list.sort.dataType.asc'
  | 'list.sort.dataType.desc'
  | 'list.empty.description'
  | 'list.actions.download.label'
  | 'list.actions.delete.label'
  | 'download.error'
  | 'download.indicator.preparing.title'
  | 'download.indicator.preparing.subtitle'
  | 'download.indicator.done.title'
  | 'download.indicator.done.subtitle'
  | 'download.indicator.dismiss'
  | 'actions.upload'
  | 'actions.refresh'
  | 'actions.datasetTypeFilter'
  | 'actions.actionsDropdown'
  | 'actions.delete.label'
  | 'actions.delete.success'
  | 'actions.delete.error'
  | 'actions.delete.confirm.title'
  | 'actions.delete.confirm.description'
  | 'modals.upload.title'
  | 'modals.upload.body'
  | 'modals.upload.docs'
  | 'modals.upload.actions.confirm'
  | 'modals.upload.actions.cancel'
  | 'modals.upload.messages.success'
  | 'modals.upload.messages.error'
  | 'modals.upload.form.datasetName.label'
  | 'modals.upload.form.datasetName.placeholder'
  | 'modals.upload.form.datasetName.emptyNameError'
  | 'modals.upload.form.datasetName.nonUniqueNameError'
  | 'modals.upload.form.datasetName.invalidCharactersError'
  | 'modals.upload.form.datasetType.label'
  | 'modals.upload.form.datasetType.placeholder'
  | 'modals.upload.form.description.label'
  | 'modals.upload.form.description.placeholder'
  | 'modals.upload.form.fileUpload.label'
  | 'modals.upload.form.fileUpload.placeholder'
  | 'modals.upload.form.fileUpload.emptyError'
  | 'modals.upload.form.fileUpload.filesizeError'
  | 'modals.upload.form.fileUpload.formatError'
  | 'selector.label'
  | 'types.Evaluation'
  | 'types.Fine-tuning'
  | 'types.unknown';

export type modelsKeys =
  | 'title'
  | 'performanceMetrics.values.latency'
  | 'performanceMetrics.values.throughput'
  | 'performanceMetrics.values.default'
  | 'status.ready'
  | 'status.pending'
  | 'status.starting'
  | 'status.running'
  | 'status.complete'
  | 'status.failed'
  | 'status.degraded'
  | 'status.deleting'
  | 'status.deleted'
  | 'status.unknown'
  | 'capabilities.chat'
  | 'capabilities.vision'
  | 'capabilities.browser'
  | 'capabilities.image'
  | 'capabilities.video'
  | 'capabilities.fine-tune'
  | 'notifications.refresh.error'
  | 'customModels.list.headers.name.title'
  | 'customModels.list.headers.canonicalName.title'
  | 'customModels.list.headers.createdBy.title'
  | 'customModels.list.headers.createdAt.title'
  | 'customModels.list.headers.type.title'
  | 'customModels.list.headers.onboardingStatus.title'
  | 'customModels.list.headers.status.title'
  | 'customModels.list.headers.workloads.title'
  | 'customModels.list.headers.actions.title'
  | 'customModels.list.filters.type.label'
  | 'customModels.list.filters.status.label'
  | 'customModels.list.filters.status.placeholder'
  | 'customModels.list.filters.search.placeholder'
  | 'customModels.list.pagination.showing'
  | 'customModels.list.pagination.pageSize.label'
  | 'customModels.list.pagination.pageSize.entities'
  | 'customModels.list.sort.name.asc'
  | 'customModels.list.sort.name.desc'
  | 'customModels.list.sort.status.asc'
  | 'customModels.list.sort.status.desc'
  | 'customModels.list.empty.description'
  | 'customModels.list.actions.delete.label'
  | 'customModels.list.actions.delete.confirmation.title'
  | 'customModels.list.actions.delete.confirmation.description'
  | 'customModels.list.actions.delete.confirmation.conflictDescription'
  | 'customModels.list.actions.delete.notification.success'
  | 'customModels.list.actions.delete.notification.error'
  | 'customModels.list.actions.delete.workloadNotification.success'
  | 'customModels.list.actions.delete.workloadNotification.error'
  | 'customModels.list.actions.deploy.label'
  | 'customModels.list.actions.deploy.confirmation.title'
  | 'customModels.list.actions.deploy.confirmation.description'
  | 'customModels.list.actions.undeploy.label'
  | 'customModels.list.actions.undeploy.confirmation.title'
  | 'customModels.list.actions.undeploy.confirmation.description'
  | 'customModels.list.actions.details.label'
  | 'customModels.list.actions.details.modal.title'
  | 'customModels.list.actions.details.modal.close'
  | 'customModels.list.actions.details.modal.modelNotFound'
  | 'customModels.list.actions.details.modal.fields.name'
  | 'customModels.list.actions.details.modal.fields.baseModel'
  | 'customModels.list.actions.details.modal.fields.resourceName'
  | 'customModels.list.actions.details.modal.fields.status'
  | 'customModels.list.actions.details.modal.fields.conditions'
  | 'customModels.list.actions.finetune.title'
  | 'customModels.list.actions.finetune.label'
  | 'customModels.list.actions.finetune.modal.title'
  | 'customModels.list.actions.finetune.modal.body'
  | 'customModels.list.actions.finetune.modal.cancel'
  | 'customModels.list.actions.finetune.modal.confirm'
  | 'customModels.list.actions.finetune.modal.baseModel.label'
  | 'customModels.list.actions.finetune.modal.baseModel.placeholder'
  | 'customModels.list.actions.finetune.modal.baseModel.noCompatibleRecipes'
  | 'customModels.list.actions.finetune.modal.dataset.label'
  | 'customModels.list.actions.finetune.modal.dataset.placeholder'
  | 'customModels.list.actions.finetune.modal.modelName.label'
  | 'customModels.list.actions.finetune.modal.modelName.placeholder'
  | 'customModels.list.actions.finetune.modal.modelName.description'
  | 'customModels.list.actions.finetune.modal.modelName.emptyNameError'
  | 'customModels.list.actions.finetune.modal.modelName.nonUniqueNameError'
  | 'customModels.list.actions.finetune.modal.modelName.invalidCharactersError'
  | 'customModels.list.actions.finetune.modal.modelDescription.label'
  | 'customModels.list.actions.finetune.modal.modelDescription.placeholder'
  | 'customModels.list.actions.finetune.modal.advancedSettingsAccordion.title'
  | 'customModels.list.actions.finetune.modal.batchSize.label'
  | 'customModels.list.actions.finetune.modal.batchSize.description'
  | 'customModels.list.actions.finetune.modal.batchSize.placeholder'
  | 'customModels.list.actions.finetune.modal.learningRateMultiplier.label'
  | 'customModels.list.actions.finetune.modal.learningRateMultiplier.description'
  | 'customModels.list.actions.finetune.modal.learningRateMultiplier.placeholder'
  | 'customModels.list.actions.finetune.modal.epochs.label'
  | 'customModels.list.actions.finetune.modal.epochs.description'
  | 'customModels.list.actions.finetune.modal.epochs.placeholder'
  | 'customModels.list.actions.finetune.notification.success'
  | 'customModels.list.actions.finetune.notification.error'
  | 'aimCatalog.list.title'
  | 'aimCatalog.list.description'
  | 'aimCatalog.list.filter.search.placeholder'
  | 'aimCatalog.list.filter.deploymentStatus.placeholder'
  | 'aimCatalog.list.filter.deploymentStatus.deployed'
  | 'aimCatalog.list.filter.deploymentStatus.notDeployed'
  | 'aimCatalog.list.filter.deploymentStatus.pending'
  | 'aimCatalog.list.filter.deploymentStatus.starting'
  | 'aimCatalog.list.filter.deploymentStatus.failed'
  | 'aimCatalog.list.filter.type.placeholder'
  | 'aimCatalog.list.filter.type.baseModel'
  | 'aimCatalog.list.filter.type.mergedModel'
  | 'aimCatalog.list.filter.type.adapter'
  | 'aimCatalog.list.filter.tag.placeholder'
  | 'aimCatalog.list.empty.description'
  | 'aimCatalog.list.sections.llm'
  | 'aimCatalog.list.sections.image'
  | 'aimCatalog.list.sections.vision'
  | 'aimCatalog.list.capabilities.text-generation'
  | 'aimCatalog.list.capabilities.chat'
  | 'aimCatalog.list.capabilities.instruction'
  | 'aimCatalog.list.capabilities.reasoning'
  | 'aimCatalog.list.capabilities.vision'
  | 'aimCatalog.card.versionCount_one'
  | 'aimCatalog.card.versionCount_other'
  | 'aimCatalog.card.gated'
  | 'aimCatalog.card.deploymentsCount_one'
  | 'aimCatalog.card.deploymentsCount_other'
  | 'aimCatalog.card.actionsMenu'
  | 'aimCatalog.card.tagsMoreCount'
  | 'aimCatalog.card.descriptionDisclaimer'
  | 'aimCatalog.actions.deploy.label'
  | 'aimCatalog.actions.retry.label'
  | 'aimCatalog.actions.undeploy.label'
  | 'aimCatalog.actions.undeploy.confirmation.title'
  | 'aimCatalog.actions.undeploy.confirmation.description'
  | 'aimCatalog.actions.workloadDetails.label'
  | 'aimCatalog.actions.chatWithModel.label'
  | 'aimCatalog.actions.connect.label'
  | 'aimCatalog.actions.connect.modal.title'
  | 'aimCatalog.actions.connect.modal.externalUrl'
  | 'aimCatalog.actions.connect.modal.internalUrl'
  | 'aimCatalog.actions.connect.modal.codeTitle'
  | 'aimCatalog.actions.connect.modal.codeExample'
  | 'aimCatalog.actions.connect.modal.inferenceUrl'
  | 'aimCatalog.actions.connect.modal.openChat'
  | 'aimCatalog.actions.connect.modal.useInternalUrl'
  | 'aimCatalog.actions.connect.modal.languages.curl'
  | 'aimCatalog.actions.connect.modal.languages.python'
  | 'aimCatalog.actions.connect.modal.languages.javascript'
  | 'aimCatalog.actions.notifications.downloadError'
  | 'aimCatalog.actions.notifications.downloadSuccess'
  | 'aimCatalog.actions.notifications.fetchError'
  | 'aimCatalog.actions.notifications.fetchSecretsError'
  | 'aimCatalog.actions.notifications.noActiveProject'
  | 'aimCatalog.actions.notifications.deleteSuccess'
  | 'aimCatalog.actions.notifications.deleteError'
  | 'aimCatalog.status.running'
  | 'aimCatalog.status.deploying'
  | 'aimCatalog.status.undeploying'
  | 'aimCatalog.status.deploymentFailed'
  | 'aimCatalog.status.unsupported'
  | 'aimCatalog.unsupported.message'
  | 'aimCatalog.unsupported.linkText'
  | 'aimCatalog.unsupported.linkUrl'
  | 'aimCatalog.tooltips.hfTokenRequired'
  | 'aimCatalog.versionSelector.label'
  | 'huggingFaceTokenDrawer.title'
  | 'huggingFaceTokenDrawer.actions.cancel'
  | 'huggingFaceTokenDrawer.actions.apply'
  | 'huggingFaceTokenDrawer.fields.selectMode'
  | 'huggingFaceTokenDrawer.fields.selectExisting'
  | 'huggingFaceTokenDrawer.fields.addNew'
  | 'huggingFaceTokenDrawer.fields.selectToken.label'
  | 'huggingFaceTokenDrawer.fields.selectToken.placeholder'
  | 'huggingFaceTokenDrawer.fields.name.label'
  | 'huggingFaceTokenDrawer.fields.name.placeholder'
  | 'huggingFaceTokenDrawer.fields.token.label'
  | 'huggingFaceTokenDrawer.fields.token.placeholder'
  | 'huggingFaceTokenDrawer.validation.selectTokenOrProvideNameAndToken'
  | 'huggingFaceTokenDrawer.validation.nameRequired'
  | 'huggingFaceTokenDrawer.validation.invalidSecretName'
  | 'huggingFaceTokenDrawer.validation.tokenRequired'
  | 'huggingFaceTokenDrawer.validation.invalidTokenFormat'
  | 'huggingFaceTokenDrawer.validation.nameTooLong'
  | 'huggingFaceTokenDrawer.notifications.secretCreated'
  | 'huggingFaceTokenDrawer.notifications.secretCreateError'
  | 'huggingFaceTokenDrawer.notifications.downloadStarted'
  | 'huggingFaceTokenDrawer.notifications.invalidSecretResponse'
  | 'huggingFaceTokenDrawer.notifications.noTokenSelected'
  | 'deployAIMDrawer.title'
  | 'deployAIMDrawer.actions.cancel'
  | 'deployAIMDrawer.actions.deploy'
  | 'deployAIMDrawer.fields.title'
  | 'deployAIMDrawer.fields.version.title'
  | 'deployAIMDrawer.fields.version.label'
  | 'deployAIMDrawer.fields.version.placeholder'
  | 'deployAIMDrawer.fields.version.latest'
  | 'deployAIMDrawer.fields.version.unsupported'
  | 'deployAIMDrawer.fields.huggingFaceToken.title'
  | 'deployAIMDrawer.fields.huggingFaceToken.description'
  | 'deployAIMDrawer.fields.huggingFaceToken.label'
  | 'deployAIMDrawer.fields.huggingFaceToken.placeholder'
  | 'deployAIMDrawer.fields.imagePullSecrets.title'
  | 'deployAIMDrawer.fields.imagePullSecrets.description'
  | 'deployAIMDrawer.fields.imagePullSecrets.label'
  | 'deployAIMDrawer.fields.imagePullSecrets.placeholder'
  | 'deployAIMDrawer.fields.metric.title'
  | 'deployAIMDrawer.fields.metric.label'
  | 'deployAIMDrawer.fields.metric.placeholder'
  | 'deployAIMDrawer.fields.metric.description'
  | 'deployAIMDrawer.fields.metric.notOptimized'
  | 'deployAIMDrawer.fields.metric.unoptimizedLabel'
  | 'deployAIMDrawer.fields.advancedProfileParams.show'
  | 'deployAIMDrawer.fields.advancedProfileParams.hide'
  | 'deployAIMDrawer.fields.advancedProfileParams.optimizationClass'
  | 'deployAIMDrawer.fields.advancedProfileParams.gpu'
  | 'deployAIMDrawer.fields.advancedProfileParams.precision'
  | 'deployAIMDrawer.fields.advancedProfileParams.gpuCount'
  | 'deployAIMDrawer.fields.advancedProfileParams.profile'
  | 'deployAIMDrawer.fields.advancedProfileParams.automatic'
  | 'deployAIMDrawer.fields.advancedProfileParams.automaticSelection'
  | 'deployAIMDrawer.fields.advancedProfileParams.automaticSelectionFromProfiles'
  | 'deployAIMDrawer.fields.advancedProfileParams.noMatchingProfiles'
  | 'deployAIMDrawer.fields.advancedProfileParams.placeholder'
  | 'deployAIMDrawer.fields.advancedProfileParams.resetParameters'
  | 'deployAIMDrawer.fields.autoscaling.title'
  | 'deployAIMDrawer.fields.autoscaling.enable'
  | 'deployAIMDrawer.notifications.success'
  | 'deployAIMDrawer.notifications.error'
  | 'deployAIMDrawer.notifications.noTemplatesDescription'
  | 'tabs.aimCatalog'
  | 'tabs.customModels'
  | 'tabs.deployedModels'
  | 'deployFinetuneAIMDrawer.title'
  | 'deployFinetuneAIMDrawer.actions.cancel'
  | 'deployFinetuneAIMDrawer.actions.deploy'
  | 'deployFinetuneAIMDrawer.fields.name.label'
  | 'deployFinetuneAIMDrawer.fields.name.description'
  | 'deployFinetuneAIMDrawer.notifications.success'
  | 'deployFinetuneAIMDrawer.notifications.error'
  | 'deployFinetuneAIMDrawer.notifications.fetchError';

export type projectsKeys =
  | 'title'
  | 'tab.title'
  | 'tab.users.title'
  | 'tab.overview.title'
  | 'tab.secrets.title'
  | 'tab.storages.title'
  | 'tab.quota.title'
  | 'tab.general.title'
  | 'actions.createProject'
  | 'list.headers.name.title'
  | 'list.headers.description.title'
  | 'list.headers.status.title'
  | 'list.headers.project.title'
  | 'list.headers.actions.title'
  | 'list.filter.search.placeholder'
  | 'list.filter.cluster.placeholder'
  | 'list.filter.status.placeholder'
  | 'list.pagination.showing'
  | 'list.pagination.pageSize.label'
  | 'list.pagination.pageSize.entities'
  | 'list.sort.name.asc'
  | 'list.sort.name.desc'
  | 'list.sort.description.asc'
  | 'list.sort.description.desc'
  | 'list.sort.users.asc'
  | 'list.sort.users.desc'
  | 'list.empty.description'
  | 'list.empty.title'
  | 'list.workloads.title'
  | 'list.workloads.empty.description'
  | 'list.workloads.headers.displayName.title'
  | 'list.workloads.headers.type.title'
  | 'list.workloads.headers.status.title'
  | 'list.workloads.headers.gpuCount.title'
  | 'list.workloads.headers.vram.title'
  | 'list.workloads.headers.runTime.title'
  | 'list.workloads.headers.createdAt.title'
  | 'list.workloads.headers.createdBy.title'
  | 'list.workloads.headers.actions.title'
  | 'list.workloads.actions.delete.title'
  | 'list.workloads.actions.delete.notification.success'
  | 'list.workloads.actions.delete.notification.error'
  | 'list.workloads.pagination.showing'
  | 'list.workloads.pagination.pageSize.label'
  | 'list.workloads.pagination.pageSize.entities'
  | 'list.users.title'
  | 'list.users.empty.description'
  | 'list.users.headers.name.title'
  | 'list.users.headers.email.title'
  | 'list.users.headers.role.title'
  | 'list.users.headers.lastActive.title'
  | 'list.users.headers.actions.title'
  | 'list.users.pagination.showing'
  | 'list.users.pagination.pageSize.label'
  | 'list.users.pagination.pageSize.entities'
  | 'list.projects.headers.name.title'
  | 'list.projects.headers.status.title'
  | 'list.projects.headers.project.title'
  | 'list.projects.headers.cpu.title'
  | 'list.projects.headers.gpu.title'
  | 'list.projects.headers.memory.title'
  | 'list.projects.headers.actions.title'
  | 'list.projects.filter.name.placeholder'
  | 'list.projects.filter.cluster.placeholder'
  | 'list.projects.filter.project.placeholder'
  | 'list.projects.clusters.unavailable'
  | 'list.projects.empty.title'
  | 'list.projects.empty.description'
  | 'list.projects.warnings.gpuWarning'
  | 'list.projects.warnings.cpuWarning'
  | 'list.projects.warnings.memoryWarning'
  | 'list.projects.pagination.showing'
  | 'list.projects.pagination.pageSize.label'
  | 'list.projects.pagination.pageSize.entities'
  | 'list.projects.actions.delete.label'
  | 'list.projects.actions.edit.label'
  | 'list.clusterUnavailable'
  | 'status.Ready'
  | 'status.Failed'
  | 'status.Deleting'
  | 'status.Pending'
  | 'status.PartiallyReady'
  | 'modal.create.title'
  | 'modal.create.actions.confirm'
  | 'modal.create.actions.cancel'
  | 'modal.create.form.name.label'
  | 'modal.create.form.name.placeholder'
  | 'modal.create.form.name.description'
  | 'modal.create.form.name.validation.unique'
  | 'modal.create.form.name.validation.format'
  | 'modal.create.form.name.validation.length'
  | 'modal.create.form.cluster.label'
  | 'modal.create.form.cluster.placeholder'
  | 'modal.create.form.cluster.validation.required'
  | 'modal.create.form.cluster.validation.exceedProjectsCount'
  | 'modal.create.form.description.label'
  | 'modal.create.form.description.placeholder'
  | 'modal.create.form.description.validation.required'
  | 'modal.create.form.description.validation.length'
  | 'modal.create.notification.success'
  | 'modal.create.notification.error'
  | 'settings.navigation'
  | 'settings.title'
  | 'settings.delete.title'
  | 'settings.delete.message'
  | 'settings.delete.action'
  | 'settings.delete.confirmation.title'
  | 'settings.delete.confirmation.description'
  | 'settings.delete.notification.success'
  | 'settings.delete.notification.error'
  | 'settings.form.basicInfo.name.label'
  | 'settings.form.basicInfo.cluster.label'
  | 'settings.form.basicInfo.description.label'
  | 'settings.form.basicInfo.description.placeholder'
  | 'settings.form.basicInfo.description.validation.required'
  | 'settings.form.basicInfo.description.validation.length'
  | 'settings.form.guaranteedQuota.info'
  | 'settings.form.guaranteedQuota.groups.resource'
  | 'settings.form.guaranteedQuota.groups.allocation'
  | 'settings.form.guaranteedQuota.groups.available'
  | 'settings.form.guaranteedQuota.fields.cpu'
  | 'settings.form.guaranteedQuota.fields.ram'
  | 'settings.form.guaranteedQuota.fields.gpu'
  | 'settings.form.guaranteedQuota.fields.disk'
  | 'settings.form.deleteProject.title'
  | 'settings.form.actions.confirm'
  | 'settings.form.actions.reset'
  | 'settings.form.notification.success'
  | 'settings.form.notification.error'
  | 'settings.membersAndInvitedUsers.title'
  | 'settings.membersAndInvitedUsers.members.title'
  | 'settings.membersAndInvitedUsers.members.empty'
  | 'settings.membersAndInvitedUsers.members.actions.add.title'
  | 'settings.membersAndInvitedUsers.members.actions.add.modal.intro'
  | 'settings.membersAndInvitedUsers.members.actions.add.modal.title'
  | 'settings.membersAndInvitedUsers.members.actions.add.modal.confirm'
  | 'settings.membersAndInvitedUsers.members.actions.add.modal.cancel'
  | 'settings.membersAndInvitedUsers.members.actions.add.form.users.label'
  | 'settings.membersAndInvitedUsers.members.actions.add.form.users.placeholder'
  | 'settings.membersAndInvitedUsers.members.actions.add.form.users.searchPlaceholder'
  | 'settings.membersAndInvitedUsers.members.actions.add.form.users.selectedUsers'
  | 'settings.membersAndInvitedUsers.members.actions.add.form.users.removeUser'
  | 'settings.membersAndInvitedUsers.members.actions.add.form.users.noUsersFound'
  | 'settings.membersAndInvitedUsers.members.actions.add.form.users.teamMember'
  | 'settings.membersAndInvitedUsers.members.actions.add.form.users.section.users'
  | 'settings.membersAndInvitedUsers.members.actions.add.form.users.section.invitedUsers'
  | 'settings.membersAndInvitedUsers.members.actions.add.validation.users.selected'
  | 'settings.membersAndInvitedUsers.members.actions.add.notification.success'
  | 'settings.membersAndInvitedUsers.members.actions.add.notification.error'
  | 'settings.membersAndInvitedUsers.members.actions.remove.label'
  | 'settings.membersAndInvitedUsers.members.actions.remove.description'
  | 'settings.membersAndInvitedUsers.members.actions.remove.confirm'
  | 'settings.membersAndInvitedUsers.members.actions.remove.notification.success'
  | 'settings.membersAndInvitedUsers.members.actions.remove.notification.error'
  | 'settings.membersAndInvitedUsers.members.form.project.label'
  | 'settings.membersAndInvitedUsers.members.form.project.placeholder'
  | 'settings.membersAndInvitedUsers.members.validation.project.selected'
  | 'settings.membersAndInvitedUsers.invitedUsers.title'
  | 'settings.membersAndInvitedUsers.invitedUsers.actions.add.title'
  | 'settings.membersAndInvitedUsers.invitedUsers.actions.remove.label'
  | 'settings.membersAndInvitedUsers.invitedUsers.actions.remove.description'
  | 'settings.membersAndInvitedUsers.invitedUsers.actions.remove.confirm'
  | 'settings.membersAndInvitedUsers.invitedUsers.actions.remove.notification.success'
  | 'settings.membersAndInvitedUsers.invitedUsers.actions.remove.notification.error'
  | 'settings.membersAndInvitedUsers.invitedUsers.disabled'
  | 'settings.membersAndInvitedUsers.invitedUsers.empty'
  | 'dashboard.action.projectSettings'
  | 'dashboard.action.manageSecrets'
  | 'dashboard.overview.title'
  | 'dashboard.overview.workloadStates.title'
  | 'dashboard.overview.workloadStates.total'
  | 'dashboard.overview.workloadStates.subtitle'
  | 'dashboard.overview.workloadStates.states.failed'
  | 'dashboard.overview.workloadStates.states.pending'
  | 'dashboard.overview.workloadStates.states.running'
  | 'dashboard.overview.workloadStates.states.completed'
  | 'dashboard.overview.waitTimeAvg.title'
  | 'dashboard.overview.waitTimeAvg.description'
  | 'dashboard.overview.gpuDeviceUsage.title'
  | 'dashboard.overview.gpuDeviceUsage.description'
  | 'dashboard.overview.gpuDeviceUsage.upperLimit'
  | 'dashboard.overview.gpuDeviceUsage.upperLimitUnallocated'
  | 'dashboard.overview.vramDeviceUsage.title'
  | 'dashboard.overview.vramDeviceUsage.description'
  | 'dashboard.overview.vramDeviceUsage.upperLimit'
  | 'dashboard.overview.vramDeviceUsage.upperLimitUnallocated'
  | 'dashboard.workloads.title'
  | 'dashboard.users.title';

export type secretsKeys =
  | 'title'
  | 'form.add.title.general'
  | 'form.add.title.project'
  | 'form.add.field.type.label'
  | 'form.add.field.type.placeholder'
  | 'form.add.field.huggingface.token.label'
  | 'form.add.field.huggingface.token.placeholder'
  | 'form.add.field.huggingface.token.description'
  | 'form.add.field.huggingface.name.label'
  | 'form.add.field.huggingface.name.description'
  | 'form.add.field.huggingface.name.placeholder'
  | 'form.add.field.manifest.externalSecret.name'
  | 'form.add.field.manifest.externalSecret.kind'
  | 'form.add.field.manifest.externalSecret.label'
  | 'form.add.field.manifest.externalSecret.description'
  | 'form.add.field.manifest.externalSecret.placeholder'
  | 'form.add.field.manifest.secret.name'
  | 'form.add.field.manifest.secret.kind'
  | 'form.add.field.manifest.secret.label'
  | 'form.add.field.manifest.secret.description'
  | 'form.add.field.manifest.secret.placeholder'
  | 'form.add.field.manifest.error.required'
  | 'form.add.field.manifest.error.yaml.malformed'
  | 'form.add.field.manifest.error.yaml.multiple'
  | 'form.add.field.manifest.error.yaml.incorrectGroup'
  | 'form.add.field.manifest.error.yaml.incorrectVersion'
  | 'form.add.field.manifest.error.yaml.incorrectKind'
  | 'form.add.field.manifest.error.yaml.noName'
  | 'form.add.field.manifest.error.yaml.invalidName'
  | 'form.add.field.manifest.error.yaml.duplicateName'
  | 'form.add.field.projectIds.label'
  | 'form.add.field.projectIds.placeholder'
  | 'form.add.field.projectIds.description'
  | 'form.add.field.name.error.required'
  | 'form.add.field.name.error.invalid'
  | 'form.add.field.name.error.duplicateName'
  | 'form.add.field.useCase.error.required'
  | 'form.add.field.data.error.required'
  | 'form.add.field.key'
  | 'form.add.field.keyPlaceholder'
  | 'form.add.field.value'
  | 'form.add.field.valuePlaceholder'
  | 'form.add.field.valuePlaceholderHuggingFace'
  | 'form.add.field.valuePlaceholderImagePull'
  | 'form.add.field.helpHuggingFace'
  | 'form.add.field.helpImagePull'
  | 'form.add.field.addEntry'
  | 'form.add.field.remove'
  | 'form.add.action.add'
  | 'form.add.action.cancel'
  | 'form.add.validation.nameRequired'
  | 'form.add.validation.nameInvalid'
  | 'form.add.validation.useCaseRequired'
  | 'form.add.validation.dataRequired'
  | 'form.add.validation.keyRequired'
  | 'form.add.validation.dockerConfigJsonInvalid'
  | 'form.add.validation.duplicateName'
  | 'form.add.notification.success'
  | 'form.add.notification.error'
  | 'form.assign.title'
  | 'form.assign.field.projectIds.label'
  | 'form.assign.field.projectIds.placeholder'
  | 'form.assign.action.save'
  | 'form.assign.action.cancel'
  | 'form.assign.notification.success'
  | 'form.assign.notification.error'
  | 'form.assignOrgSecret.title'
  | 'form.assignOrgSecret.field.secretId.label'
  | 'form.assignOrgSecret.field.secretId.placeholder'
  | 'form.assignOrgSecret.field.secretId.error.required'
  | 'form.assignOrgSecret.secretDetails.title'
  | 'form.assignOrgSecret.secretDetails.type.label'
  | 'form.assignOrgSecret.secretDetails.useCase.label'
  | 'form.assignOrgSecret.secretDetails.updatedAt.label'
  | 'form.assignOrgSecret.secretDetails.createdAt.label'
  | 'form.assignOrgSecret.secretDetails.assignedTo.label'
  | 'form.assignOrgSecret.secretDetails.status.label'
  | 'form.assignOrgSecret.action.save'
  | 'form.assignOrgSecret.action.cancel'
  | 'form.assignOrgSecret.notification.success'
  | 'form.assignOrgSecret.notification.error'
  | 'form.delete.title'
  | 'form.delete.description'
  | 'form.delete.action.delete'
  | 'form.delete.action.cancel'
  | 'form.delete.notification.success'
  | 'form.delete.notification.error'
  | 'form.deleteProjectSecret.title'
  | 'form.deleteProjectSecret.description'
  | 'form.deleteProjectSecret.action.delete'
  | 'form.deleteProjectSecret.action.cancel'
  | 'form.deleteProjectSecret.notification.success'
  | 'form.deleteProjectSecret.notification.error'
  | 'list.title'
  | 'list.filter.search.label'
  | 'list.filter.search.placeholder'
  | 'list.filter.scope.label'
  | 'list.filter.scope.placeholder'
  | 'list.filter.scope.options.Organization'
  | 'list.filter.scope.options.Project'
  | 'list.filter.scope.options.User'
  | 'list.filter.type.label'
  | 'list.filter.type.placeholder'
  | 'list.filter.type.options.ExternalSecret'
  | 'list.filter.type.options.KubernetesSecret'
  | 'list.headers.name.title'
  | 'list.headers.type.title'
  | 'list.headers.status.title'
  | 'list.headers.scope.title'
  | 'list.headers.useCase.title'
  | 'list.headers.assignedTo.title'
  | 'list.headers.createdBy.title'
  | 'list.headers.updatedAt.title'
  | 'list.headers.createdAt.title'
  | 'list.headers.actions.title'
  | 'list.empty.description'
  | 'list.pagination.showing'
  | 'list.pagination.pageSize.label'
  | 'list.pagination.pageSize.entities'
  | 'list.actions.assign.label'
  | 'list.actions.assign.hint.actionPending'
  | 'list.actions.assign.hint.scope'
  | 'list.actions.delete.projectSecret.label'
  | 'list.actions.delete.label'
  | 'list.actions.delete.hint.storage'
  | 'actions.add'
  | 'actions.addProjectSecret.label'
  | 'actions.addProjectSecret.options.add.label'
  | 'actions.addProjectSecret.options.assign.label'
  | 'actions.addProjectSecret.back'
  | 'actions.addProjectSecret.disabled'
  | 'actions.assign'
  | 'secretType.ExternalSecret'
  | 'secretType.KubernetesSecret'
  | 'secretStatus.Unassigned'
  | 'secretStatus.PartiallySynced'
  | 'secretStatus.Pending'
  | 'secretStatus.Synced'
  | 'secretStatus.SyncedError'
  | 'secretStatus.Failed'
  | 'secretStatus.Deleting'
  | 'secretStatus.Deleted'
  | 'secretStatus.DeleteFailed'
  | 'secretScope.Organization'
  | 'secretScope.Project'
  | 'secretScope.User'
  | 'statusReason.messageTrigger'
  | 'statusReason.messageHeader'
  | 'useCase.HuggingFace'
  | 'useCase.ImagePullSecret'
  | 'useCase.S3'
  | 'useCase.Database'
  | 'useCase.Generic';

export type sharedComponentsKeys =
  | 'filterDropdown.selectAll.label'
  | 'filterDropdown.clear.label'
  | 'RelevantDocs.title'
  | 'RelevantDocs.learnMore';

export type storagesKeys =
  | 'title'
  | 'list.title'
  | 'list.filter.search.label'
  | 'list.filter.search.placeholder'
  | 'list.filter.scope.label'
  | 'list.filter.scope.placeholder'
  | 'list.filter.scope.options.Organization'
  | 'list.filter.scope.options.Project'
  | 'list.filter.scope.options.User'
  | 'list.filter.type.label'
  | 'list.filter.type.placeholder'
  | 'list.filter.type.options.S3'
  | 'list.filter.type.options.PVC'
  | 'list.headers.name.title'
  | 'list.headers.type.title'
  | 'list.headers.status.title'
  | 'list.headers.scope.title'
  | 'list.headers.assignedTo.title'
  | 'list.headers.createdAt.title'
  | 'list.headers.createdBy.title'
  | 'list.headers.actions.title'
  | 'list.empty.description'
  | 'list.pagination.showing'
  | 'list.pagination.pageSize.label'
  | 'list.pagination.pageSize.entities'
  | 'list.actions.assign.label'
  | 'list.actions.delete.label'
  | 'list.actions.deleteFromProject.label'
  | 'actions.add.label'
  | 'actions.add.options.S3.label'
  | 'actions.addProjectStorage.label'
  | 'actions.addProjectStorage.disabled'
  | 'actions.assignStorage.label'
  | 'actions.assignStorage.options.S3.label'
  | 'actions.assignProjectStorage.disabled'
  | 'form.add.title'
  | 'form.add.description'
  | 'form.add.documentLink'
  | 'form.add.field.name.label'
  | 'form.add.field.name.placeholder'
  | 'form.add.field.name.error.minLength'
  | 'form.add.field.name.error.maxLength'
  | 'form.add.field.name.error.required'
  | 'form.add.field.name.error.invalidName'
  | 'form.add.field.name.error.duplicateName'
  | 'form.add.field.accessKeyName.label'
  | 'form.add.field.accessKeyName.description'
  | 'form.add.field.secretKeyName.label'
  | 'form.add.field.secretKeyName.description'
  | 'form.add.field.bucketUrl.label'
  | 'form.add.field.bucketUrl.placeholder'
  | 'form.add.field.bucketUrl.error.required'
  | 'form.add.field.bucketUrl.error.maxLength'
  | 'form.add.field.bucketUrl.error.invalidUrl'
  | 'form.add.field.secretId.label'
  | 'form.add.field.secretId.placeholder'
  | 'form.add.field.secretId.actions.createSecret'
  | 'form.add.field.projectIds.label'
  | 'form.add.field.projectIds.placeholder'
  | 'form.add.notification.success'
  | 'form.add.notification.error'
  | 'form.add.actions.add.label'
  | 'form.add.actions.cancel.label'
  | 'form.assign.title'
  | 'form.assign.description'
  | 'form.assign.field.projectIds.label'
  | 'form.assign.field.projectIds.placeholder'
  | 'form.assign.action.save'
  | 'form.assign.action.cancel'
  | 'form.assign.notification.success'
  | 'form.assign.notification.error'
  | 'form.assignToProject.title'
  | 'form.assignToProject.description'
  | 'form.assignToProject.noAvailableStorages'
  | 'form.assignToProject.field.storageId.label'
  | 'form.assignToProject.field.storageId.placeholder'
  | 'form.assignToProject.field.storageId.error.required'
  | 'form.assignToProject.action.assign'
  | 'form.assignToProject.action.cancel'
  | 'form.assignToProject.notification.success'
  | 'form.assignToProject.notification.error'
  | 'form.delete.title'
  | 'form.delete.description'
  | 'form.delete.notification.success'
  | 'form.delete.notification.error'
  | 'form.delete.actions.remove.label'
  | 'form.delete.actions.cancel.label'
  | 'form.deleteProjectStorage.title'
  | 'form.deleteProjectStorage.description'
  | 'form.deleteProjectStorage.notification.success'
  | 'form.deleteProjectStorage.notification.error'
  | 'form.deleteProjectStorage.actions.remove.label'
  | 'form.deleteProjectStorage.actions.cancel.label'
  | 'storageType.S3'
  | 'storageType.PVC'
  | 'storageStatus.Unassigned'
  | 'storageStatus.PartiallySynced'
  | 'storageStatus.Pending'
  | 'storageStatus.Synced'
  | 'storageStatus.SyncedError'
  | 'storageStatus.Failed'
  | 'storageStatus.Deleting'
  | 'storageStatus.Deleted'
  | 'storageStatus.DeleteFailed'
  | 'storageScope.Organization'
  | 'storageScope.Project';

export type workloadsKeys =
  | 'title'
  | 'details.title'
  | 'details.sections.inferenceMetrics'
  | 'details.sections.workloadInformation'
  | 'details.sections.basicInformation'
  | 'details.sections.projectInformation'
  | 'details.sections.resources'
  | 'details.sections.timeline'
  | 'details.sections.modelAndDataset'
  | 'details.sections.capabilities'
  | 'details.sections.output'
  | 'details.sections.status'
  | 'details.conditions.ready'
  | 'details.conditions.failed'
  | 'details.conditions.pending'
  | 'details.profile.title'
  | 'details.profile.performanceMetric'
  | 'details.profile.accelerator'
  | 'details.profile.acceleratorCount'
  | 'details.profile.precision'
  | 'details.profile.automatic'
  | 'details.profile.unoptimizedNotice'
  | 'details.fields.updatedAt'
  | 'details.fields.externalHost'
  | 'details.fields.internalHost'
  | 'details.fields.host'
  | 'details.fields.notManagedByWorkbench'
  | 'details.metrics.inferenceRequests.title'
  | 'details.metrics.inferenceRequests.description'
  | 'details.metrics.timeToFirstToken.title'
  | 'details.metrics.timeToFirstToken.description'
  | 'details.metrics.interTokenLatency.title'
  | 'details.metrics.interTokenLatency.description'
  | 'details.metrics.endToEndLatency.title'
  | 'details.metrics.endToEndLatency.description'
  | 'details.metrics.maxRequests.title'
  | 'details.metrics.maxRequests.description'
  | 'details.metrics.minRequests.title'
  | 'details.metrics.minRequests.description'
  | 'details.metrics.avgRequests.title'
  | 'details.metrics.avgRequests.description'
  | 'details.metrics.totalRequests.title'
  | 'details.metrics.totalRequests.description'
  | 'details.metrics.totalTokens.title'
  | 'details.metrics.totalTokens.description'
  | 'details.metrics.kvCacheUsage.title'
  | 'details.metrics.kvCacheUsage.description'
  | 'details.metrics.replicaSelector.label'
  | 'details.metrics.replicaSelector.allReplicas'
  | 'details.metrics.gpuConsumption.title'
  | 'details.metrics.gpuConsumption.description'
  | 'details.metrics.vram.title'
  | 'details.metrics.vram.description'
  | 'details.breadcrumb'
  | 'status.Added'
  | 'status.Pending'
  | 'status.Starting'
  | 'status.Running'
  | 'status.Complete'
  | 'status.Failed'
  | 'status.Degraded'
  | 'status.Deleting'
  | 'status.Deleted'
  | 'status.DeleteFailed'
  | 'status.Downloading'
  | 'status.Terminated'
  | 'status.Unknown'
  | 'type.MODEL_DOWNLOAD'
  | 'type.INFERENCE'
  | 'type.FINE_TUNING'
  | 'type.WORKSPACE'
  | 'type.UNKNOWN'
  | 'type.CUSTOM'
  | 'notifications.refresh.error'
  | 'notifications.logs.error'
  | 'list.errors.noLaunchUrl'
  | 'list.errors.noRunningWorkload'
  | 'list.headers.displayName.title'
  | 'list.headers.id.title'
  | 'list.headers.canonicalName.title'
  | 'list.headers.vram.title'
  | 'list.headers.gpu.title'
  | 'list.headers.type.title'
  | 'list.headers.createdBy.title'
  | 'list.headers.createdAt.title'
  | 'list.headers.status.title'
  | 'list.headers.model.title'
  | 'list.headers.model.id'
  | 'list.headers.model.name'
  | 'list.headers.model.canonicalName'
  | 'list.headers.dataset.title'
  | 'list.headers.dataset.id'
  | 'list.headers.dataset.name'
  | 'list.headers.dataset.description'
  | 'list.headers.chart.title'
  | 'list.headers.chart.id'
  | 'list.headers.chart.name'
  | 'list.headers.chart.description'
  | 'list.headers.aim.title'
  | 'list.headers.aim.id'
  | 'list.headers.aim.canonicalName'
  | 'list.headers.aim.description'
  | 'list.headers.aim.image'
  | 'list.headers.aim.resourceName'
  | 'list.headers.aim.containerVersion'
  | 'list.headers.aim.baseModel'
  | 'list.headers.cluster.title'
  | 'list.headers.cluster.id'
  | 'list.headers.cluster.name'
  | 'list.headers.project.title'
  | 'list.headers.project.id'
  | 'list.headers.project.name'
  | 'list.headers.actions.title'
  | 'list.valueTemplates.gpu'
  | 'list.valueTemplates.vram'
  | 'list.filters.type.label'
  | 'list.filters.status.label'
  | 'list.filters.search.placeholder'
  | 'list.actions.chat.label'
  | 'list.actions.delete.label'
  | 'list.actions.delete.confirmation.title'
  | 'list.actions.delete.confirmation.description'
  | 'list.actions.delete.notification.success'
  | 'list.actions.delete.notification.error'
  | 'list.actions.openWorkspace.label'
  | 'list.actions.details.label'
  | 'list.actions.details.modal.title'
  | 'list.actions.details.modal.close'
  | 'list.actions.details.modal.workloadNotFound'
  | 'list.actions.logs.label'
  | 'list.actions.logs.modal.title'
  | 'list.actions.logs.modal.description'
  | 'list.actions.logs.modal.streaming'
  | 'list.actions.logs.modal.logLevelFilter.label'
  | 'list.actions.logs.modal.logLevelFilter.allLevels'
  | 'list.actions.logs.modal.noLogs'
  | 'list.actions.logs.modal.noEvents'
  | 'list.actions.logs.modal.logTypeFilter.label'
  | 'list.actions.logs.modal.logTypeFilter.workload'
  | 'list.actions.logs.modal.logTypeFilter.event'
  | 'list.actions.logs.modal.workloadNotFound'
  | 'list.pagination.showing'
  | 'list.pagination.pageSize.label'
  | 'list.pagination.pageSize.entities'
  | 'list.empty.description'
  | 'errors.workloadNotFound.title'
  | 'errors.workloadNotFound.description';

declare module 'i18next' {
  interface CustomTypeOptions {
    defaultNS: 'common';
    strictKeyChecks: true;
    resources: {
      'api-keys': {
        list: {
          title: string;
          clusterAuthDisabled: string;
          filters: {
            search: {
              placeholder: string;
            };
          };
          actions: {
            create: {
              title: string;
            };
            edit: {
              title: string;
            };
            delete: {
              title: string;
              confirmation: {
                title: string;
                description: string;
              };
              notification: {
                success: string;
                error: string;
              };
            };
          };
          apiKeys: {
            headers: {
              name: {
                title: string;
              };
              secretKey: {
                title: string;
              };
              createdAt: {
                title: string;
              };
              createdBy: {
                title: string;
              };
              actions: {
                title: string;
              };
            };
            empty: {
              description: string;
            };
            pagination: {
              showing: string;
              pageSize: {
                label: string;
                entities: string;
              };
            };
          };
        };
        form: {
          create: {
            title: string;
            action: {
              create: string;
              cancel: string;
            };
            field: {
              name: {
                label: string;
                placeholder: string;
                error: {
                  minLength: string;
                  maxLength: string;
                };
              };
              expiresAt: {
                label: string;
              };
              validityPeriod: {
                label: string;
                placeholder: string;
                description: string;
                options: {
                  '1day': string;
                  '1week': string;
                  '2weeks': string;
                  '30days': string;
                  '60days': string;
                  '90days': string;
                  never: string;
                };
              };
              modelDeployment: {
                label: string;
                placeholder: string;
                description: string;
              };
            };
            section: {
              endpointAccess: string;
            };
            notification: {
              success: string;
              error: string;
            };
          };
          edit: {
            title: string;
            action: {
              save: string;
              cancel: string;
            };
            section: {
              linkedDeployments: string;
              noLinkedDeployments: string;
            };
            notification: {
              success: string;
              error: string;
            };
            warning: {
              linkedDeploymentsWarning: string;
            };
          };
          keyCreated: {
            title: string;
            description: string;
            warning: string;
            field: {
              name: {
                label: string;
              };
              key: {
                label: string;
              };
            };
            action: {
              done: string;
            };
            notification: {
              copySuccess: string;
              copyError: string;
            };
            aria: {
              copyButton: string;
            };
          };
        };
      };
      autoscaling: {
        title: string;
        settingsTitle: string;
        enable: string;
        helper: string;
        description: string;
        replicaRange: string;
        replicasMinimum: string;
        scalingMetric: {
          label: string;
          placeholder: string;
          defaultDescription: string;
          options: {
            runningRequests: string;
            waitingRequests: string;
          };
          descriptions: {
            runningRequests: string;
            waitingRequests: string;
          };
        };
        aggregation: {
          label: string;
          placeholder: string;
          description: string;
          options: {
            avg: string;
            max: string;
            min: string;
          };
          tooltips: {
            avg: string;
            max: string;
            min: string;
          };
        };
        targetType: {
          label: string;
          placeholder: string;
          description: string;
          options: {
            value: string;
            averageValue: string;
          };
          tooltips: {
            value: string;
            averageValue: string;
          };
        };
        targetValue: {
          label: string;
          descriptions: {
            value: string;
            averageValue: string;
          };
        };
        podPhase: {
          running: string;
          pending: string;
          succeeded: string;
          failed: string;
          unknown: string;
        };
        replicas: {
          toggle: string;
        };
        list: {
          replicas: {
            headers: {
              name: {
                title: string;
              };
              status: {
                title: string;
              };
              gpuCount: {
                title: string;
              };
              createdAt: {
                title: string;
              };
            };
            empty: {
              description: string;
            };
          };
        };
        actions: {
          cancel: string;
          save: string;
          settings: string;
        };
        notifications: {
          noWorkloadId: string;
          updateSuccess: string;
          updateError: string;
          convergenceTimeout: string;
        };
      };
      catalog: {
        actions: {
          search: {
            placeholder: string;
            label: string;
          };
          categoryFilter: {
            label: string;
          };
          refresh: string;
        };
        categories: {
          development: string;
          mlops: string;
          genai: string;
        };
        card: {
          tagsMoreCount: string;
          moreInformation: string;
        };
        list: {
          actions: {
            deploy: string;
            pending: string;
            launch: string;
            view: string;
            details: string;
            undeploy: string;
            deleteFailedWorkload: string;
          };
          errors: {
            undeployError: string;
            noRunningWorkload: string;
          };
          notifications: {
            undeploySuccess: string;
          };
        };
        status: {
          Complete: string;
          Degraded: string;
          Failed: string;
          Deleting: string;
          Deleted: string;
          Pending: string;
          Running: string;
          Starting: string;
          Unknown: string;
        };
        deployModal: {
          title: string;
          settings: {
            title: string;
            displayName: {
              label: string;
              placeholder: string;
              emptyNameError: string;
            };
            containerImage: {
              label: string;
              tooltip: string;
              emptyNameError: string;
              formatError: string;
            };
            imagePullSecrets: {
              label: string;
              tooltip: string;
              placeholder: string;
              noSecrets: string;
            };
            resourceAllocation: {
              req: string;
              belowRequiredWarning: string;
              exceedsQuotaWarning: string;
              belowRequiredExceedsQuotaWarning: string;
              belowRequiredTooltip: string;
              exceedsQuotaTooltip: string;
              belowRequiredExceedsQuotaTooltip: string;
              perGPU: string;
              quotaFormatted: string;
              cpuFormattedValue_one: string;
              cpuFormattedValue_other: string;
              ramFormattedValue: string;
              ramLabel: string;
              gpuLabel: string;
              cpuLabel: string;
              label: string;
              totalResourceAllocation: string;
              gpuCount: string;
              gpuCountValue: string;
              systemMemory: string;
              systemMemoryValue: string;
              cpuCoreCount: string;
              cpuCoreCountValue: string;
            };
          };
          deploymentStatus: {
            deployingMessage: string;
            readyMessage: string;
            launchButtonReady: string;
            launchButtonPending: string;
          };
          actions: {
            deploy: string;
            cancel: string;
          };
        };
        undeployModal: {
          title: string;
          description: string;
        };
        notifications: {
          deployWorkload: {
            success: string;
            error: string;
          };
        };
      };
      chat: {
        title: string;
        edit: {
          saveAndSubmit: string;
          cancel: string;
        };
        modes: {
          chat: string;
          compare: string;
        };
        chat: {
          title: string;
          description: string;
          tips: {
            tip1: string;
            tip2: string;
            tip3: string;
          };
        };
        compare: {
          title: string;
          description: string;
          tips: {
            tip1: string;
            tip2: string;
            tip3: string;
          };
        };
        roles: {
          user: string;
          assistant: string;
          system: string;
        };
        modelSettings: {
          title: string;
          selectModel: string;
          syncSettings: {
            label: string;
            description: string;
          };
          enableRag: {
            label: string;
            description: string;
          };
          collection: {
            label: string;
            description: string;
            tooltip: string;
          };
          documentCount: {
            label: string;
            description: string;
            tooltip: string;
          };
          hybridSearch: {
            label: string;
            description: string;
            tooltip: string;
          };
          alpha: {
            label: string;
            description: string;
            tooltip: string;
          };
          certainty: {
            label: string;
            description: string;
            tooltip: string;
          };
          userPromptTemplate: {
            label: string;
            description: string;
            placeholder: string;
            tooltip: string;
            validationErrorMessage: string;
          };
          temperature: {
            label: string;
            description: string;
            tooltip: string;
          };
          frequencyPenalty: {
            label: string;
            description: string;
            tooltip: string;
          };
          presencePenalty: {
            label: string;
            description: string;
            tooltip: string;
          };
          systemPrompt: {
            label: string;
            placeholder: string;
            description: string;
            tooltip: string;
          };
        };
        chatInput: {
          placeholder: string;
          placeholderDisabled: string;
          regenerateResponse: string;
          attachImages: string;
          attachImage: string;
          removeImage: string;
          attachedImageAlt: string;
          dropImages: string;
        };
        actions: {
          selectModel: string;
          clearAll: string;
        };
        errors: {
          modelLoadingFailed: string;
          workloadLoadingFailed: string;
          chatResponseFailed: string;
          invalidImageFile: string;
          imageTooLarge: string;
          totalAttachmentTooLarge: string;
          failedToReadImage: string;
          failedToSendMessage: string;
        };
        notifications: {
          delayedResponse: string;
        };
        debugInfoModal: {
          title: string;
          subTitle: string;
          ragDocumentsTitle: string;
          ragDocumentsDescription: string;
          noSources: string;
          promptsTitle: string;
          promptsDescription: string;
          noPromptMessages: string;
          tokenUsageTitle: string;
          promptTokens: string;
          completionTokens: string;
          totalTokens: string;
          noTokenUsage: string;
        };
      };
      clusters: {
        title: string;
        connectCluster: {
          title: string;
          start: {
            title: string;
            content: {
              description: string;
              confirmation: string;
            };
            actions: {
              cancel: string;
              next: string;
            };
          };
          script: {
            title: string;
            content: {
              description: string;
              note: string;
              confirmation: string;
            };
            actions: {
              next: string;
            };
          };
          final: {
            title: string;
            content: {
              description: string;
              instruction: string;
              helppage: string;
            };
            actions: {
              complete: string;
            };
          };
          notifications: {
            failure: string;
          };
        };
        form: {
          edit: {
            title: string;
            field: {
              workbenchBaseUrl: {
                label: string;
                placeholder: string;
                emptyError: string;
                error: {
                  invalid: string;
                };
              };
              kubeApiUrl: {
                label: string;
                placeholder: string;
                emptyError: string;
                error: {
                  invalid: string;
                };
              };
            };
            action: {
              cancel: string;
              save: string;
            };
            notification: {
              success: string;
              error: string;
            };
          };
        };
        config: {
          button: string;
          title: string;
          description: string;
          disabled: string;
        };
        list: {
          pending: {
            title: string;
            headers: {
              requestedAt: {
                title: string;
              };
              requestExpiry: {
                title: string;
              };
              status: {
                title: string;
              };
              actions: {
                title: string;
              };
            };
            empty: {
              description: string;
            };
            pagination: {
              showing: string;
              pageSize: {
                label: string;
                entities: string;
              };
            };
            actions: {
              cancel: string;
            };
          };
          active: {
            title: string;
          };
          headers: {
            name: {
              title: string;
            };
            status: {
              title: string;
            };
            nodes: {
              title: string;
              description: string;
            };
            gpuAllocation: {
              title: string;
            };
            cpuAllocation: {
              title: string;
            };
            memoryAllocation: {
              title: string;
            };
            actions: {
              title: string;
            };
          };
          filter: {
            search: {
              placeholder: string;
            };
            status: {
              placeholder: string;
            };
          };
          pagination: {
            showing: string;
            pageSize: {
              label: string;
              entities: string;
            };
          };
          sort: {
            name: {
              asc: string;
              desc: string;
            };
            status: {
              asc: string;
              desc: string;
            };
          };
          empty: {
            description: string;
          };
          actions: {
            delete: {
              label: string;
              confirmation: {
                title: string;
                description: string;
              };
              notification: {
                success: string;
                error: string;
              };
            };
            edit: {
              label: string;
            };
            cancel: {
              label: string;
              confirmation: {
                title: string;
                description: string;
              };
              notification: {
                success: string;
                error: string;
              };
            };
          };
          workloads: {
            title: string;
            empty: {
              description: string;
            };
            headers: {
              displayName: {
                title: string;
              };
              projectId: {
                title: string;
              };
              type: {
                title: string;
              };
              status: {
                title: string;
              };
              gpuCount: {
                title: string;
              };
              vram: {
                title: string;
              };
              createdAt: {
                title: string;
              };
              createdBy: {
                title: string;
              };
              actions: {
                title: string;
              };
            };
            actions: {
              delete: {
                title: string;
                notification: {
                  success: string;
                  error: string;
                };
              };
            };
            pagination: {
              showing: string;
              pageSize: {
                label: string;
                entities: string;
              };
            };
          };
        };
        nodes: {
          title: string;
          list: {
            headers: {
              name: {
                title: string;
              };
              status: {
                title: string;
              };
              cpuMilliCores: {
                title: string;
              };
              memoryBytes: {
                title: string;
              };
              gpuName: {
                title: string;
              };
              gpuCount: {
                title: string;
              };
              gpuMemory: {
                title: string;
              };
            };
            filter: {
              placeholder: string;
            };
            pagination: {
              showing: string;
              pageSize: {
                label: string;
                entities: string;
              };
            };
            empty: {
              description: string;
            };
          };
        };
        projects: {
          title: string;
        };
        statistics: {
          cluster: {
            nodes: {
              title: string;
              tooltip: string;
            };
            projects: {
              title: string;
              tooltip: string;
            };
            gpus: {
              title: string;
              tooltip: string;
            };
            workloads: {
              title: string;
              tooltip: string;
            };
          };
          clusters: {
            clusters: {
              title: string;
              tooltip: string;
            };
            nodes: {
              title: string;
              tooltip: string;
            };
            gpus: {
              title: string;
              tooltip: string;
            };
            workloads: {
              title: string;
              tooltip: string;
            };
          };
        };
        allocationAndWorkloads: {
          charts: {
            gpuDeviceUtilization: {
              title: string;
            };
          };
        };
        dashboard: {
          overview: {
            workloadStates: {
              title: string;
              total: string;
              subtitle: string;
            };
          };
          workloads: {
            title: string;
          };
        };
        workloads: {
          title: string;
          actions: {
            view: string;
            back: string;
          };
        };
        actions: {
          connect: string;
        };
        status: {
          healthy: string;
          unhealthy: string;
          verifying: string;
        };
      };
      collections: {
        title: string;
        collections: {
          select: {
            label: string;
            placeholder: string;
          };
          infoPanel: {
            title: string;
            fields: {
              name: string;
              organization: string;
              createdOn: string;
              embeddings: string;
              chunkSize: string;
              chunkOverlap: string;
              contentAwareness: string;
            };
            enabled: string;
            disabled: string;
          };
          messages: {
            failed: string;
          };
          actions: {
            title: string;
            label: string;
            description: string;
            scrape: string;
            upload: string;
            deleteSelected: string;
            refresh: {
              label: string;
            };
          };
          delete: {
            title: string;
            description: string;
            messages: {
              success: string;
              delete: string;
            };
          };
          errors: {
            noCollection: {
              title: string;
              description: string;
            };
          };
        };
        documents: {
          title: string;
          list: {
            headers: {
              author: {
                title: string;
              };
              documentId: {
                title: string;
              };
              createdAt: {
                title: string;
              };
              updatedAt: {
                title: string;
              };
            };
            empty: {
              title: string;
              description: string;
            };
          };
          messages: {
            failed: string;
          };
          search: {
            label: string;
            placeholder: string;
            clear: string;
          };
        };
        jobs: {
          title: string;
          list: {
            headers: {
              jobType: {
                title: string;
              };
              status: {
                title: string;
              };
              createdAt: {
                title: string;
              };
              totalIndexedFailed: {
                title: string;
              };
            };
            empty: {
              title: string;
              description: string;
            };
          };
          messages: {
            failed: string;
          };
        };
        modals: {
          fileUpload: {
            action: string;
            dragAndDrop: string;
          };
          newCollection: {
            title: string;
            description: string;
            form: {
              name: {
                label: string;
                placeholder: string;
                error: string;
              };
              embeddingServer: {
                label: string;
                placeholder: string;
              };
              chunkSize: {
                label: string;
                subLabel: string;
                description: string;
                placeholder: string;
                error: string;
              };
              overlap: {
                label: string;
                subLabel: string;
                description: string;
                error: string;
              };
              contentAware: {
                label: string;
                subLabel: string;
                description: string;
              };
              seeAdvanced: {
                title: string;
              };
            };
            messages: {
              success: string;
              errors: {
                embeddingServers: string;
                uniqueName: string;
                collection: string;
              };
            };
          };
          deleteDocuments: {
            title: string;
            description: string;
            messages: {
              success: string;
              delete: string;
            };
          };
          scrapeWebsite: {
            title: string;
            subTitle: string;
            description: string;
            form: {
              url: {
                label: string;
              };
              pages: {
                label: string;
              };
            };
            messages: {
              success: string;
              failed: string;
            };
          };
          uploadZip: {
            title: string;
            subTitle: string;
            helpText: string;
            form: {
              host: {
                label: string;
                placeholder: string;
              };
            };
            messages: {
              success: string;
              saveFailed: string;
              uploadFailed: string;
            };
            errors: {
              activeJob: string;
              oneZipFile: string;
              maxFiles: string;
              validation: string;
            };
          };
        };
      };
      common: {
        app: {
          title: string;
        };
        sections: {
          aiWorkbench: {
            title: string;
          };
          resourceManagement: {
            title: string;
          };
        };
        sharedComponents: {
          filterDropdown: {
            selectAll: {
              label: string;
            };
          };
          FormFileUpload: {
            remove: string;
            add_one: string;
            add_other: string;
            drop_one: string;
            drop_other: string;
            dropFail_one: string;
            dropFail_other: string;
            footerFiles_one: string;
            footerFiles_other: string;
          };
        };
        pages: {
          collections: {
            title: string;
          };
          dashboard: {
            title: string;
          };
          clusters: {
            title: string;
          };
          projects: {
            title: string;
          };
          secrets: {
            title: string;
          };
          storages: {
            title: string;
          };
          chat: {
            title: string;
          };
          models: {
            title: string;
          };
          aimCatalog: {
            title: string;
          };
          customModels: {
            title: string;
          };
          deployedModels: {
            title: string;
          };
          datasets: {
            title: string;
          };
          workloads: {
            title: string;
          };
          workspaces: {
            title: string;
          };
          workbenchSecrets: {
            title: string;
          };
          accessControl: {
            title: string;
          };
          users: {
            title: string;
          };
          apiKeys: {
            title: string;
          };
          error: {
            title: string;
          };
        };
        menu: {
          actions: {
            open: string;
            close: string;
            themeToggle: string;
            theme: string;
            logout: string;
            reportIssue: string;
          };
        };
        actions: {
          add: string;
          back: {
            title: string;
          };
          confirm: {
            title: string;
            message: string;
          };
          close: {
            title: string;
          };
          cancel: {
            title: string;
          };
          clear: {
            title: string;
          };
          copy: {
            title: string;
          };
          clearFilters: {
            title: string;
          };
          create: {
            title: string;
          };
          delete: {
            title: string;
          };
          download: {
            title: string;
          };
          next: string;
          previous: string;
          refresh: {
            title: string;
          };
          remove: {
            title: string;
          };
          save: {
            title: string;
          };
          showDetails: {
            title: string;
          };
          start: {
            title: string;
          };
          upload: {
            title: string;
          };
        };
        list: {
          actions: {
            label: string;
            assign: {
              label: string;
            };
            delete: {
              label: string;
            };
          };
        };
        theme: {
          light: string;
          dark: string;
        };
        links: {
          home: string;
          documentation: string;
          support: string;
          about: string;
        };
        error: {
          label: string;
          noSubmittableProjects: {
            title: string;
            description: string;
          };
          fetchFailed: {
            title: string;
            description: string;
          };
          service: {
            title: string;
            description: string;
          };
          projectNotFound: {
            title: string;
            description: string;
          };
          unknown: {
            title: string;
            description: string;
          };
          refreshActionLabel: string;
          misc: {
            unknownEntity: string;
            unknownError: string;
          };
          api: {
            requestFailed: string;
            noProjectSelected: string;
            projectIdRequired: string;
          };
        };
        statistics: {
          upperLimitPrefix: string;
          noData: string;
        };
        projectSelection: {
          placeholder: string;
          label: string;
          tooltip: string;
        };
        projectSelectPrompt: {
          title: string;
          description: string;
        };
        timeRange: {
          description: string;
          range: {
            '15m': string;
            '30m': string;
            '1h': string;
            '24h': string;
            '7d': string;
          };
          lastUpdated: string;
        };
        charts: {
          category: {
            others: string;
          };
          loading: string;
          nodata: string;
          refresh: string;
          refreshing: string;
        };
        data: {
          lastUpdated: string;
          refresh: string;
          refreshing: string;
        };
        status: {
          description: string;
          errorDetail: {
            title: string;
            action: {
              next: string;
              prev: string;
            };
          };
        };
        password: {
          showPassword: string;
          hidePassword: string;
        };
        userMenu: {
          airmAppLabel: string;
        };
        requestSoftware: {
          model: {
            title: string;
            description: string;
            button: string;
          };
          workspace: {
            title: string;
            description: string;
            button: string;
          };
        };
      };
      dashboard: {
        title: string;
        clusterAndNodes: {
          title: string;
          cards: {
            clusters: {
              title: string;
              tooltip: string;
            };
            gpuNodes: {
              title: string;
              tooltip: string;
            };
            availableGPUs: {
              title: string;
              tooltip: string;
            };
            allocatedGPUs: {
              title: string;
              tooltip: string;
            };
          };
        };
        list: {
          headers: {
            name: {
              title: string;
            };
            gpuAllocation: {
              title: string;
            };
            gpuUtilization: {
              title: string;
            };
            running: {
              title: string;
            };
            pending: {
              title: string;
            };
            actions: {
              title: string;
            };
          };
          actions: {
            open: {
              label: string;
            };
          };
          empty: {
            description: string;
          };
          pagination: {
            showing: string;
            pageSize: {
              label: string;
              entities: string;
            };
          };
        };
        allocationAndWorkloads: {
          title: string;
          consumptionByProject: {
            title: string;
          };
          cards: {
            gpuUtilization: {
              title: string;
              tooltip: string;
            };
            runningWorkloads: {
              title: string;
              tooltip: string;
            };
            pendingWorkloads: {
              title: string;
              tooltip: string;
            };
          };
          charts: {
            gpuMemoryUtilization: {
              title: string;
            };
            gpuDeviceUtilization: {
              title: string;
            };
          };
        };
      };
      datasets: {
        title: string;
        list: {
          headers: {
            type: {
              title: string;
            };
            name: {
              title: string;
            };
            description: {
              title: string;
            };
            organization: {
              title: string;
            };
            createdBy: {
              title: string;
            };
            createdAt: {
              title: string;
            };
            actions: {
              title: string;
            };
          };
          pagination: {
            showing: string;
            pageSize: {
              label: string;
              entities: string;
            };
          };
          sort: {
            name: {
              asc: string;
              desc: string;
            };
            dataType: {
              asc: string;
              desc: string;
            };
          };
          empty: {
            description: string;
          };
          actions: {
            download: {
              label: string;
            };
            delete: {
              label: string;
            };
          };
        };
        download: {
          error: string;
          indicator: {
            preparing: {
              title: string;
              subtitle: string;
            };
            done: {
              title: string;
              subtitle: string;
            };
            dismiss: string;
          };
        };
        actions: {
          upload: string;
          refresh: string;
          datasetTypeFilter: string;
          actionsDropdown: string;
          delete: {
            label: string;
            success: string;
            error: string;
            confirm: {
              title: string;
              description: string;
            };
          };
        };
        modals: {
          upload: {
            title: string;
            body: string;
            docs: string;
            actions: {
              confirm: string;
              cancel: string;
            };
            messages: {
              success: string;
              error: string;
            };
            form: {
              datasetName: {
                label: string;
                placeholder: string;
                emptyNameError: string;
                nonUniqueNameError: string;
                invalidCharactersError: string;
              };
              datasetType: {
                label: string;
                placeholder: string;
              };
              description: {
                label: string;
                placeholder: string;
              };
              fileUpload: {
                label: string;
                placeholder: string;
                emptyError: string;
                filesizeError: string;
                formatError: string;
              };
            };
          };
        };
        selector: {
          label: string;
        };
        types: {
          Evaluation: string;
          'Fine-tuning': string;
          unknown: string;
        };
      };
      models: {
        title: string;
        performanceMetrics: {
          values: {
            latency: string;
            throughput: string;
            default: string;
          };
        };
        status: {
          ready: string;
          pending: string;
          starting: string;
          running: string;
          complete: string;
          failed: string;
          degraded: string;
          deleting: string;
          deleted: string;
          unknown: string;
        };
        capabilities: {
          chat: string;
          vision: string;
          browser: string;
          image: string;
          video: string;
          'fine-tune': string;
        };
        notifications: {
          refresh: {
            error: string;
          };
        };
        customModels: {
          list: {
            headers: {
              name: {
                title: string;
              };
              canonicalName: {
                title: string;
              };
              createdBy: {
                title: string;
              };
              createdAt: {
                title: string;
              };
              type: {
                title: string;
              };
              onboardingStatus: {
                title: string;
              };
              status: {
                title: string;
              };
              workloads: {
                title: string;
              };
              actions: {
                title: string;
              };
            };
            filters: {
              type: {
                label: string;
              };
              status: {
                label: string;
                placeholder: string;
              };
              search: {
                placeholder: string;
              };
            };
            pagination: {
              showing: string;
              pageSize: {
                label: string;
                entities: string;
              };
            };
            sort: {
              name: {
                asc: string;
                desc: string;
              };
              status: {
                asc: string;
                desc: string;
              };
            };
            empty: {
              description: string;
            };
            actions: {
              delete: {
                label: string;
                confirmation: {
                  title: string;
                  description: string;
                  conflictDescription: string;
                };
                notification: {
                  success: string;
                  error: string;
                };
                workloadNotification: {
                  success: string;
                  error: string;
                };
              };
              deploy: {
                label: string;
                confirmation: {
                  title: string;
                  description: string;
                };
              };
              undeploy: {
                label: string;
                confirmation: {
                  title: string;
                  description: string;
                };
              };
              details: {
                label: string;
                modal: {
                  title: string;
                  close: string;
                  modelNotFound: string;
                  fields: {
                    name: string;
                    baseModel: string;
                    resourceName: string;
                    status: string;
                    conditions: string;
                  };
                };
              };
              finetune: {
                title: string;
                label: string;
                modal: {
                  title: string;
                  body: string;
                  cancel: string;
                  confirm: string;
                  baseModel: {
                    label: string;
                    placeholder: string;
                    noCompatibleRecipes: string;
                  };
                  dataset: {
                    label: string;
                    placeholder: string;
                  };
                  modelName: {
                    label: string;
                    placeholder: string;
                    description: string;
                    emptyNameError: string;
                    nonUniqueNameError: string;
                    invalidCharactersError: string;
                  };
                  modelDescription: {
                    label: string;
                    placeholder: string;
                  };
                  advancedSettingsAccordion: {
                    title: string;
                  };
                  batchSize: {
                    label: string;
                    description: string;
                    placeholder: string;
                  };
                  learningRateMultiplier: {
                    label: string;
                    description: string;
                    placeholder: string;
                  };
                  epochs: {
                    label: string;
                    description: string;
                    placeholder: string;
                  };
                };
                notification: {
                  success: string;
                  error: string;
                };
              };
            };
          };
        };
        aimCatalog: {
          list: {
            title: string;
            description: string;
            filter: {
              search: {
                placeholder: string;
              };
              deploymentStatus: {
                placeholder: string;
                deployed: string;
                notDeployed: string;
                pending: string;
                starting: string;
                failed: string;
              };
              type: {
                placeholder: string;
                baseModel: string;
                mergedModel: string;
                adapter: string;
              };
              tag: {
                placeholder: string;
              };
            };
            empty: {
              description: string;
            };
            sections: {
              llm: string;
              image: string;
              vision: string;
            };
            capabilities: {
              'text-generation': string;
              chat: string;
              instruction: string;
              reasoning: string;
              vision: string;
            };
          };
          card: {
            versionCount_one: string;
            versionCount_other: string;
            gated: string;
            deploymentsCount_one: string;
            deploymentsCount_other: string;
            actionsMenu: string;
            tagsMoreCount: string;
            descriptionDisclaimer: string;
          };
          actions: {
            deploy: {
              label: string;
            };
            retry: {
              label: string;
            };
            undeploy: {
              label: string;
              confirmation: {
                title: string;
                description: string;
              };
            };
            workloadDetails: {
              label: string;
            };
            chatWithModel: {
              label: string;
            };
            connect: {
              label: string;
              modal: {
                title: string;
                externalUrl: string;
                internalUrl: string;
                codeTitle: string;
                codeExample: string;
                inferenceUrl: string;
                openChat: string;
                useInternalUrl: string;
                languages: {
                  curl: string;
                  python: string;
                  javascript: string;
                };
              };
            };
            notifications: {
              downloadError: string;
              downloadSuccess: string;
              fetchError: string;
              fetchSecretsError: string;
              noActiveProject: string;
              deleteSuccess: string;
              deleteError: string;
            };
          };
          status: {
            running: string;
            deploying: string;
            undeploying: string;
            deploymentFailed: string;
            unsupported: string;
          };
          unsupported: {
            message: string;
            linkText: string;
            linkUrl: string;
          };
          tooltips: {
            hfTokenRequired: string;
          };
          versionSelector: {
            label: string;
          };
        };
        huggingFaceTokenDrawer: {
          title: string;
          actions: {
            cancel: string;
            apply: string;
          };
          fields: {
            selectMode: string;
            selectExisting: string;
            addNew: string;
            selectToken: {
              label: string;
              placeholder: string;
            };
            name: {
              label: string;
              placeholder: string;
            };
            token: {
              label: string;
              placeholder: string;
            };
          };
          validation: {
            selectTokenOrProvideNameAndToken: string;
            nameRequired: string;
            invalidSecretName: string;
            tokenRequired: string;
            invalidTokenFormat: string;
            nameTooLong: string;
          };
          notifications: {
            secretCreated: string;
            secretCreateError: string;
            downloadStarted: string;
            invalidSecretResponse: string;
            noTokenSelected: string;
          };
        };
        deployAIMDrawer: {
          title: string;
          actions: {
            cancel: string;
            deploy: string;
          };
          fields: {
            title: string;
            version: {
              title: string;
              label: string;
              placeholder: string;
              latest: string;
              unsupported: string;
            };
            huggingFaceToken: {
              title: string;
              description: string;
              label: string;
              placeholder: string;
            };
            imagePullSecrets: {
              title: string;
              description: string;
              label: string;
              placeholder: string;
            };
            metric: {
              title: string;
              label: string;
              placeholder: string;
              description: string;
              notOptimized: string;
              unoptimizedLabel: string;
            };
            advancedProfileParams: {
              show: string;
              hide: string;
              optimizationClass: string;
              gpu: string;
              precision: string;
              gpuCount: string;
              profile: string;
              automatic: string;
              automaticSelection: string;
              automaticSelectionFromProfiles: string;
              noMatchingProfiles: string;
              placeholder: string;
              resetParameters: string;
            };
            autoscaling: {
              title: string;
              enable: string;
            };
          };
          notifications: {
            success: string;
            error: string;
            noTemplatesDescription: string;
          };
        };
        tabs: {
          aimCatalog: string;
          customModels: string;
          deployedModels: string;
        };
        deployFinetuneAIMDrawer: {
          title: string;
          actions: {
            cancel: string;
            deploy: string;
          };
          fields: {
            name: {
              label: string;
              description: string;
            };
          };
          notifications: {
            success: string;
            error: string;
            fetchError: string;
          };
        };
      };
      projects: {
        title: string;
        tab: {
          title: string;
          users: {
            title: string;
          };
          overview: {
            title: string;
          };
          secrets: {
            title: string;
          };
          storages: {
            title: string;
          };
          quota: {
            title: string;
          };
          general: {
            title: string;
          };
        };
        actions: {
          createProject: string;
        };
        list: {
          headers: {
            name: {
              title: string;
            };
            description: {
              title: string;
            };
            status: {
              title: string;
            };
            project: {
              title: string;
            };
            actions: {
              title: string;
            };
          };
          filter: {
            search: {
              placeholder: string;
            };
            cluster: {
              placeholder: string;
            };
            status: {
              placeholder: string;
            };
          };
          pagination: {
            showing: string;
            pageSize: {
              label: string;
              entities: string;
            };
          };
          sort: {
            name: {
              asc: string;
              desc: string;
            };
            description: {
              asc: string;
              desc: string;
            };
            users: {
              asc: string;
              desc: string;
            };
          };
          empty: {
            description: string;
            title: string;
          };
          workloads: {
            title: string;
            empty: {
              description: string;
            };
            headers: {
              displayName: {
                title: string;
              };
              type: {
                title: string;
              };
              status: {
                title: string;
              };
              gpuCount: {
                title: string;
              };
              vram: {
                title: string;
              };
              runTime: {
                title: string;
              };
              createdAt: {
                title: string;
              };
              createdBy: {
                title: string;
              };
              actions: {
                title: string;
              };
            };
            actions: {
              delete: {
                title: string;
                notification: {
                  success: string;
                  error: string;
                };
              };
            };
            pagination: {
              showing: string;
              pageSize: {
                label: string;
                entities: string;
              };
            };
          };
          users: {
            title: string;
            empty: {
              description: string;
            };
            headers: {
              name: {
                title: string;
              };
              email: {
                title: string;
              };
              role: {
                title: string;
              };
              lastActive: {
                title: string;
              };
              actions: {
                title: string;
              };
            };
            pagination: {
              showing: string;
              pageSize: {
                label: string;
                entities: string;
              };
            };
          };
          projects: {
            headers: {
              name: {
                title: string;
              };
              status: {
                title: string;
              };
              project: {
                title: string;
              };
              cpu: {
                title: string;
              };
              gpu: {
                title: string;
              };
              memory: {
                title: string;
              };
              actions: {
                title: string;
              };
            };
            filter: {
              name: {
                placeholder: string;
              };
              cluster: {
                placeholder: string;
              };
              project: {
                placeholder: string;
              };
            };
            clusters: {
              unavailable: string;
            };
            empty: {
              title: string;
              description: string;
            };
            warnings: {
              gpuWarning: string;
              cpuWarning: string;
              memoryWarning: string;
            };
            pagination: {
              showing: string;
              pageSize: {
                label: string;
                entities: string;
              };
            };
            actions: {
              delete: {
                label: string;
              };
              edit: {
                label: string;
              };
            };
          };
          clusterUnavailable: string;
        };
        status: {
          Ready: string;
          Failed: string;
          Deleting: string;
          Pending: string;
          PartiallyReady: string;
        };
        modal: {
          create: {
            title: string;
            actions: {
              confirm: string;
              cancel: string;
            };
            form: {
              name: {
                label: string;
                placeholder: string;
                description: string;
                validation: {
                  unique: string;
                  format: string;
                  length: string;
                };
              };
              cluster: {
                label: string;
                placeholder: string;
                validation: {
                  required: string;
                  exceedProjectsCount: string;
                };
              };
              description: {
                label: string;
                placeholder: string;
                validation: {
                  required: string;
                  length: string;
                };
              };
            };
            notification: {
              success: string;
              error: string;
            };
          };
        };
        settings: {
          navigation: string;
          title: string;
          delete: {
            title: string;
            message: string;
            action: string;
            confirmation: {
              title: string;
              description: string;
            };
            notification: {
              success: string;
              error: string;
            };
          };
          form: {
            basicInfo: {
              name: {
                label: string;
              };
              cluster: {
                label: string;
              };
              description: {
                label: string;
                placeholder: string;
                validation: {
                  required: string;
                  length: string;
                };
              };
            };
            guaranteedQuota: {
              info: string;
              groups: {
                resource: string;
                allocation: string;
                available: string;
              };
              fields: {
                cpu: string;
                ram: string;
                gpu: string;
                disk: string;
              };
            };
            deleteProject: {
              title: string;
            };
            actions: {
              confirm: string;
              reset: string;
            };
            notification: {
              success: string;
              error: string;
            };
          };
          membersAndInvitedUsers: {
            title: string;
            members: {
              title: string;
              empty: string;
              actions: {
                add: {
                  title: string;
                  modal: {
                    intro: string;
                    title: string;
                    confirm: string;
                    cancel: string;
                  };
                  form: {
                    users: {
                      label: string;
                      placeholder: string;
                      searchPlaceholder: string;
                      selectedUsers: string;
                      removeUser: string;
                      noUsersFound: string;
                      teamMember: string;
                      section: {
                        users: string;
                        invitedUsers: string;
                      };
                    };
                  };
                  validation: {
                    users: {
                      selected: string;
                    };
                  };
                  notification: {
                    success: string;
                    error: string;
                  };
                };
                remove: {
                  label: string;
                  description: string;
                  confirm: string;
                  notification: {
                    success: string;
                    error: string;
                  };
                };
              };
              form: {
                project: {
                  label: string;
                  placeholder: string;
                };
              };
              validation: {
                project: {
                  selected: string;
                };
              };
            };
            invitedUsers: {
              title: string;
              actions: {
                add: {
                  title: string;
                };
                remove: {
                  label: string;
                  description: string;
                  confirm: string;
                  notification: {
                    success: string;
                    error: string;
                  };
                };
              };
              disabled: string;
              empty: string;
            };
          };
        };
        dashboard: {
          action: {
            projectSettings: string;
            manageSecrets: string;
          };
          overview: {
            title: string;
            workloadStates: {
              title: string;
              total: string;
              subtitle: string;
              states: {
                failed: string;
                pending: string;
                running: string;
                completed: string;
              };
            };
            waitTimeAvg: {
              title: string;
              description: string;
            };
            gpuDeviceUsage: {
              title: string;
              description: string;
              upperLimit: string;
              upperLimitUnallocated: string;
            };
            vramDeviceUsage: {
              title: string;
              description: string;
              upperLimit: string;
              upperLimitUnallocated: string;
            };
          };
          workloads: {
            title: string;
          };
          users: {
            title: string;
          };
        };
      };
      secrets: {
        title: string;
        form: {
          add: {
            title: {
              general: string;
              project: string;
            };
            field: {
              type: {
                label: string;
                placeholder: string;
              };
              huggingface: {
                token: {
                  label: string;
                  placeholder: string;
                  description: string;
                };
                name: {
                  label: string;
                  description: string;
                  placeholder: string;
                };
              };
              manifest: {
                externalSecret: {
                  name: string;
                  kind: string;
                  label: string;
                  description: string;
                  placeholder: string;
                };
                secret: {
                  name: string;
                  kind: string;
                  label: string;
                  description: string;
                  placeholder: string;
                };
                error: {
                  required: string;
                  yaml: {
                    malformed: string;
                    multiple: string;
                    incorrectGroup: string;
                    incorrectVersion: string;
                    incorrectKind: string;
                    noName: string;
                    invalidName: string;
                    duplicateName: string;
                  };
                };
              };
              projectIds: {
                label: string;
                placeholder: string;
                description: string;
              };
              name: {
                error: {
                  required: string;
                  invalid: string;
                  duplicateName: string;
                };
              };
              useCase: {
                error: {
                  required: string;
                };
              };
              data: {
                error: {
                  required: string;
                };
              };
              key: string;
              keyPlaceholder: string;
              value: string;
              valuePlaceholder: string;
              valuePlaceholderHuggingFace: string;
              valuePlaceholderImagePull: string;
              helpHuggingFace: string;
              helpImagePull: string;
              addEntry: string;
              remove: string;
            };
            action: {
              add: string;
              cancel: string;
            };
            validation: {
              nameRequired: string;
              nameInvalid: string;
              useCaseRequired: string;
              dataRequired: string;
              keyRequired: string;
              dockerConfigJsonInvalid: string;
              duplicateName: string;
            };
            notification: {
              success: string;
              error: string;
            };
          };
          assign: {
            title: string;
            field: {
              projectIds: {
                label: string;
                placeholder: string;
              };
            };
            action: {
              save: string;
              cancel: string;
            };
            notification: {
              success: string;
              error: string;
            };
          };
          assignOrgSecret: {
            title: string;
            field: {
              secretId: {
                label: string;
                placeholder: string;
                error: {
                  required: string;
                };
              };
            };
            secretDetails: {
              title: string;
              type: {
                label: string;
              };
              useCase: {
                label: string;
              };
              updatedAt: {
                label: string;
              };
              createdAt: {
                label: string;
              };
              assignedTo: {
                label: string;
              };
              status: {
                label: string;
              };
            };
            action: {
              save: string;
              cancel: string;
            };
            notification: {
              success: string;
              error: string;
            };
          };
          delete: {
            title: string;
            description: string;
            action: {
              delete: string;
              cancel: string;
            };
            notification: {
              success: string;
              error: string;
            };
          };
          deleteProjectSecret: {
            title: string;
            description: string;
            action: {
              delete: string;
              cancel: string;
            };
            notification: {
              success: string;
              error: string;
            };
          };
        };
        list: {
          title: string;
          filter: {
            search: {
              label: string;
              placeholder: string;
            };
            scope: {
              label: string;
              placeholder: string;
              options: {
                Organization: string;
                Project: string;
                User: string;
              };
            };
            type: {
              label: string;
              placeholder: string;
              options: {
                ExternalSecret: string;
                KubernetesSecret: string;
              };
            };
          };
          headers: {
            name: {
              title: string;
            };
            type: {
              title: string;
            };
            status: {
              title: string;
            };
            scope: {
              title: string;
            };
            useCase: {
              title: string;
            };
            assignedTo: {
              title: string;
            };
            createdBy: {
              title: string;
            };
            updatedAt: {
              title: string;
            };
            createdAt: {
              title: string;
            };
            actions: {
              title: string;
            };
          };
          empty: {
            description: string;
          };
          pagination: {
            showing: string;
            pageSize: {
              label: string;
              entities: string;
            };
          };
          actions: {
            assign: {
              label: string;
              hint: {
                actionPending: string;
                scope: string;
              };
            };
            delete: {
              projectSecret: {
                label: string;
              };
              label: string;
              hint: {
                storage: string;
              };
            };
          };
        };
        actions: {
          add: string;
          addProjectSecret: {
            label: string;
            options: {
              add: {
                label: string;
              };
              assign: {
                label: string;
              };
            };
            back: string;
            disabled: string;
          };
          assign: string;
        };
        secretType: {
          ExternalSecret: string;
          KubernetesSecret: string;
        };
        secretStatus: {
          Unassigned: string;
          PartiallySynced: string;
          Pending: string;
          Synced: string;
          SyncedError: string;
          Failed: string;
          Deleting: string;
          Deleted: string;
          DeleteFailed: string;
        };
        secretScope: {
          Organization: string;
          Project: string;
          User: string;
        };
        statusReason: {
          messageTrigger: string;
          messageHeader: string;
        };
        useCase: {
          HuggingFace: string;
          ImagePullSecret: string;
          S3: string;
          Database: string;
          Generic: string;
        };
      };
      sharedComponents: {
        filterDropdown: {
          selectAll: {
            label: string;
          };
          clear: {
            label: string;
          };
        };
        RelevantDocs: {
          title: string;
          learnMore: string;
        };
      };
      storages: {
        title: string;
        list: {
          title: string;
          filter: {
            search: {
              label: string;
              placeholder: string;
            };
            scope: {
              label: string;
              placeholder: string;
              options: {
                Organization: string;
                Project: string;
                User: string;
              };
            };
            type: {
              label: string;
              placeholder: string;
              options: {
                S3: string;
                PVC: string;
              };
            };
          };
          headers: {
            name: {
              title: string;
            };
            type: {
              title: string;
            };
            status: {
              title: string;
            };
            scope: {
              title: string;
            };
            assignedTo: {
              title: string;
            };
            createdAt: {
              title: string;
            };
            createdBy: {
              title: string;
            };
            actions: {
              title: string;
            };
          };
          empty: {
            description: string;
          };
          pagination: {
            showing: string;
            pageSize: {
              label: string;
              entities: string;
            };
          };
          actions: {
            assign: {
              label: string;
            };
            delete: {
              label: string;
            };
            deleteFromProject: {
              label: string;
            };
          };
        };
        actions: {
          add: {
            label: string;
            options: {
              S3: {
                label: string;
              };
            };
          };
          addProjectStorage: {
            label: string;
            disabled: string;
          };
          assignStorage: {
            label: string;
            options: {
              S3: {
                label: string;
              };
            };
          };
          assignProjectStorage: {
            disabled: string;
          };
        };
        form: {
          add: {
            title: string;
            description: string;
            documentLink: string;
            field: {
              name: {
                label: string;
                placeholder: string;
                error: {
                  minLength: string;
                  maxLength: string;
                  required: string;
                  invalidName: string;
                  duplicateName: string;
                };
              };
              accessKeyName: {
                label: string;
                description: string;
              };
              secretKeyName: {
                label: string;
                description: string;
              };
              bucketUrl: {
                label: string;
                placeholder: string;
                error: {
                  required: string;
                  maxLength: string;
                  invalidUrl: string;
                };
              };
              secretId: {
                label: string;
                placeholder: string;
                actions: {
                  createSecret: string;
                };
              };
              projectIds: {
                label: string;
                placeholder: string;
              };
            };
            notification: {
              success: string;
              error: string;
            };
            actions: {
              add: {
                label: string;
              };
              cancel: {
                label: string;
              };
            };
          };
          assign: {
            title: string;
            description: string;
            field: {
              projectIds: {
                label: string;
                placeholder: string;
              };
            };
            action: {
              save: string;
              cancel: string;
            };
            notification: {
              success: string;
              error: string;
            };
          };
          assignToProject: {
            title: string;
            description: string;
            noAvailableStorages: string;
            field: {
              storageId: {
                label: string;
                placeholder: string;
                error: {
                  required: string;
                };
              };
            };
            action: {
              assign: string;
              cancel: string;
            };
            notification: {
              success: string;
              error: string;
            };
          };
          delete: {
            title: string;
            description: string;
            notification: {
              success: string;
              error: string;
            };
            actions: {
              remove: {
                label: string;
              };
              cancel: {
                label: string;
              };
            };
          };
          deleteProjectStorage: {
            title: string;
            description: string;
            notification: {
              success: string;
              error: string;
            };
            actions: {
              remove: {
                label: string;
              };
              cancel: {
                label: string;
              };
            };
          };
        };
        storageType: {
          S3: string;
          PVC: string;
        };
        storageStatus: {
          Unassigned: string;
          PartiallySynced: string;
          Pending: string;
          Synced: string;
          SyncedError: string;
          Failed: string;
          Deleting: string;
          Deleted: string;
          DeleteFailed: string;
        };
        storageScope: {
          Organization: string;
          Project: string;
        };
      };
      workloads: {
        title: string;
        details: {
          title: string;
          sections: {
            inferenceMetrics: string;
            workloadInformation: string;
            basicInformation: string;
            projectInformation: string;
            resources: string;
            timeline: string;
            modelAndDataset: string;
            capabilities: string;
            output: string;
            status: string;
          };
          conditions: {
            ready: string;
            failed: string;
            pending: string;
          };
          profile: {
            title: string;
            performanceMetric: string;
            accelerator: string;
            acceleratorCount: string;
            precision: string;
            automatic: string;
            unoptimizedNotice: string;
          };
          fields: {
            updatedAt: string;
            externalHost: string;
            internalHost: string;
            host: string;
            notManagedByWorkbench: string;
          };
          metrics: {
            inferenceRequests: {
              title: string;
              description: string;
            };
            timeToFirstToken: {
              title: string;
              description: string;
            };
            interTokenLatency: {
              title: string;
              description: string;
            };
            endToEndLatency: {
              title: string;
              description: string;
            };
            maxRequests: {
              title: string;
              description: string;
            };
            minRequests: {
              title: string;
              description: string;
            };
            avgRequests: {
              title: string;
              description: string;
            };
            totalRequests: {
              title: string;
              description: string;
            };
            totalTokens: {
              title: string;
              description: string;
            };
            kvCacheUsage: {
              title: string;
              description: string;
            };
            replicaSelector: {
              label: string;
              allReplicas: string;
            };
            gpuConsumption: {
              title: string;
              description: string;
            };
            vram: {
              title: string;
              description: string;
            };
          };
          breadcrumb: string;
        };
        status: {
          Added: string;
          Pending: string;
          Starting: string;
          Running: string;
          Complete: string;
          Failed: string;
          Degraded: string;
          Deleting: string;
          Deleted: string;
          DeleteFailed: string;
          Downloading: string;
          Terminated: string;
          Unknown: string;
        };
        type: {
          MODEL_DOWNLOAD: string;
          INFERENCE: string;
          FINE_TUNING: string;
          WORKSPACE: string;
          UNKNOWN: string;
          CUSTOM: string;
        };
        notifications: {
          refresh: {
            error: string;
          };
          logs: {
            error: string;
          };
        };
        list: {
          errors: {
            noLaunchUrl: string;
            noRunningWorkload: string;
          };
          headers: {
            displayName: {
              title: string;
            };
            id: {
              title: string;
            };
            canonicalName: {
              title: string;
            };
            vram: {
              title: string;
            };
            gpu: {
              title: string;
            };
            type: {
              title: string;
            };
            createdBy: {
              title: string;
            };
            createdAt: {
              title: string;
            };
            status: {
              title: string;
            };
            model: {
              title: string;
              id: string;
              name: string;
              canonicalName: string;
            };
            dataset: {
              title: string;
              id: string;
              name: string;
              description: string;
            };
            chart: {
              title: string;
              id: string;
              name: string;
              description: string;
            };
            aim: {
              title: string;
              id: string;
              canonicalName: string;
              description: string;
              image: string;
              resourceName: string;
              containerVersion: string;
              baseModel: string;
            };
            cluster: {
              title: string;
              id: string;
              name: string;
            };
            project: {
              title: string;
              id: string;
              name: string;
            };
            actions: {
              title: string;
            };
          };
          valueTemplates: {
            gpu: string;
            vram: string;
          };
          filters: {
            type: {
              label: string;
            };
            status: {
              label: string;
            };
            search: {
              placeholder: string;
            };
          };
          actions: {
            chat: {
              label: string;
            };
            delete: {
              label: string;
              confirmation: {
                title: string;
                description: string;
              };
              notification: {
                success: string;
                error: string;
              };
            };
            openWorkspace: {
              label: string;
            };
            details: {
              label: string;
              modal: {
                title: string;
                close: string;
                workloadNotFound: string;
              };
            };
            logs: {
              label: string;
              modal: {
                title: string;
                description: string;
                streaming: string;
                logLevelFilter: {
                  label: string;
                  allLevels: string;
                };
                noLogs: string;
                noEvents: string;
                logTypeFilter: {
                  label: string;
                  workload: string;
                  event: string;
                };
                workloadNotFound: string;
              };
            };
          };
          pagination: {
            showing: string;
            pageSize: {
              label: string;
              entities: string;
            };
          };
          empty: {
            description: string;
          };
        };
        errors: {
          workloadNotFound: {
            title: string;
            description: string;
          };
        };
      };
    };
  }
}
