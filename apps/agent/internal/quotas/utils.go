// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

package quotas

import (
	"context"
	"fmt"
	"time"

	agent "github.com/silogen/agent/internal/common"
	"github.com/silogen/agent/internal/messaging"
	kaiwov1alpha1 "github.com/silogen/kaiwo/apis/kaiwo/v1alpha1"
	corev1 "k8s.io/api/core/v1"
	"k8s.io/apimachinery/pkg/api/resource"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	ctrl "sigs.k8s.io/controller-runtime"
	"sigs.k8s.io/controller-runtime/pkg/client"
	"sigs.k8s.io/controller-runtime/pkg/controller/controllerutil"
	kueuev1alpha1 "sigs.k8s.io/kueue/apis/kueue/v1alpha1"
	kueuev1beta1 "sigs.k8s.io/kueue/apis/kueue/v1beta1"
)

// buildKaiwoQueueConfigManifest creates a KaiwoQueueConfig matching the cluster allocation.
func buildKaiwoQueueConfigManifest(msg *messaging.ClusterQuotasAllocationMessage) *kaiwov1alpha1.KaiwoQueueConfig {
	// Determine covered resources based on GPU vendor
	coveredResources := []corev1.ResourceName{
		CPUResource,
		MemoryResource,
		EphemeralStorageResource,
	}

	if msg.GPUVendor != nil {
		switch *msg.GPUVendor {
		case messaging.GPUVendorNVIDIA:
			coveredResources = append(coveredResources, NVIDIAGPUResource)
		case messaging.GPUVendorAMD:
			coveredResources = append(coveredResources, AMDGPUResource)
		}
	}

	var clusterQueues []kaiwov1alpha1.ClusterQueue
	for _, quota := range msg.QuotaAllocations {
		resources := []kueuev1beta1.ResourceQuota{
			{
				Name:         CPUResource,
				NominalQuota: resource.MustParse(fmt.Sprintf("%dm", quota.CPUMilliCores)),
			},
			{
				Name:         MemoryResource,
				NominalQuota: resource.MustParse(fmt.Sprintf("%d", quota.MemoryBytes)),
			},
			{
				Name:         EphemeralStorageResource,
				NominalQuota: resource.MustParse(fmt.Sprintf("%d", quota.EphemeralStorageBytes)),
			},
		}

		// Add GPU resource if vendor is specified
		if msg.GPUVendor != nil {
			gpuResource := kueuev1beta1.ResourceQuota{
				NominalQuota: resource.MustParse(fmt.Sprintf("%d", quota.GPUCount)),
			}
			switch *msg.GPUVendor {
			case messaging.GPUVendorNVIDIA:
				gpuResource.Name = NVIDIAGPUResource
			case messaging.GPUVendorAMD:
				gpuResource.Name = AMDGPUResource
			}
			resources = append(resources, gpuResource)
		}

		stopPolicyNone := kueuev1beta1.None

		clusterQueue := kaiwov1alpha1.ClusterQueue{
			Name:       quota.QuotaName,
			Namespaces: quota.Namespaces,
			Spec: kaiwov1alpha1.ClusterQueueSpec{
				Cohort: DefaultCohortName,
				FlavorFungibility: &kueuev1beta1.FlavorFungibility{
					WhenCanBorrow:  kueuev1beta1.Borrow,
					WhenCanPreempt: kueuev1beta1.Preempt,
				},
				NamespaceSelector: &metav1.LabelSelector{},
				Preemption: &kueuev1beta1.ClusterQueuePreemption{
					BorrowWithinCohort: &kueuev1beta1.BorrowWithinCohort{
						Policy: kueuev1beta1.BorrowWithinCohortPolicyNever,
					},
					ReclaimWithinCohort: kueuev1beta1.PreemptionPolicyAny,
					WithinClusterQueue:  kueuev1beta1.PreemptionPolicyLowerPriority,
				},
				QueueingStrategy: kueuev1beta1.BestEffortFIFO,
				ResourceGroups: []kueuev1beta1.ResourceGroup{
					{
						CoveredResources: coveredResources,
						Flavors: []kueuev1beta1.FlavorQuotas{
							{
								Name:      kueuev1beta1.ResourceFlavorReference(DefaultResourceFlavourName),
								Resources: resources,
							},
						},
					},
				},
				StopPolicy: &stopPolicyNone,
			},
		}
		clusterQueues = append(clusterQueues, clusterQueue)
	}

	var workloadPriorityClasses []kueuev1beta1.WorkloadPriorityClass
	for _, pc := range msg.PriorityClasses {
		wpc := kueuev1beta1.WorkloadPriorityClass{
			ObjectMeta: metav1.ObjectMeta{
				Name: pc.Name,
			},
			Value:       pc.Priority,
			Description: fmt.Sprintf("Priority class %s with priority %d", pc.Name, pc.Priority),
		}
		workloadPriorityClasses = append(workloadPriorityClasses, wpc)
	}

	return &kaiwov1alpha1.KaiwoQueueConfig{
		TypeMeta: metav1.TypeMeta{
			APIVersion: kaiwov1alpha1.GroupVersion.String(),
			Kind:       "KaiwoQueueConfig",
		},
		ObjectMeta: metav1.ObjectMeta{
			Name: KaiwoQueueConfigDefaultName,
		},
		Spec: kaiwov1alpha1.KaiwoQueueConfigSpec{
			ResourceFlavors: []kaiwov1alpha1.ResourceFlavorSpec{
				{
					Name: DefaultResourceFlavourName,
				},
			},
			ClusterQueues:           clusterQueues,
			WorkloadPriorityClasses: workloadPriorityClasses,
			// Kueue needs this section for it to function, so hardcode it for now.
			Topologies: []kaiwov1alpha1.Topology{
				{
					ObjectMeta: metav1.ObjectMeta{Name: DefaultTopologyName},
					Spec: kaiwov1alpha1.TopologySpec{
						Levels: []kueuev1alpha1.TopologyLevel{
							{NodeLabel: TopologyLevelBlockNodeLabel},
							{NodeLabel: TopologyLevelRackNodeLabel},
							{NodeLabel: corev1.LabelHostname},
						},
					},
				},
			},
		},
	}
}

func HandleDeletion(
	ctx context.Context,
	c client.Client,
	publisher messaging.MessagePublisher,
	obj client.Object,
) error {
	if !controllerutil.ContainsFinalizer(obj, kaiwoQueueConfigFinalizer) {
		return nil
	}

	statusMsg := &messaging.ClusterQuotasStatusMessage{
		MessageType:      messaging.MessageTypeClusterQuotasStatusMessage,
		UpdatedAt:        time.Now(),
		QuotaAllocations: []messaging.ClusterQuotaAllocation{},
	}
	if err := publisher.Publish(ctx, statusMsg); err != nil {
		return err
	}

	return agent.RemoveFinalizer(ctx, c, obj, kaiwoQueueConfigFinalizer)
}

func publishStatusUpdate(ctx context.Context, publisher messaging.MessagePublisher, config *kaiwov1alpha1.KaiwoQueueConfig) error {
	log := ctrl.LoggerFrom(ctx)
	var quotaAllocations []messaging.ClusterQuotaAllocation

	for _, cq := range config.Spec.ClusterQueues {
		namespaces := cq.Namespaces
		if namespaces == nil {
			namespaces = []string{}
		}

		allocation := messaging.ClusterQuotaAllocation{
			QuotaName:  cq.Name,
			Namespaces: namespaces,
		}

		if len(cq.Spec.ResourceGroups) > 0 {
			rg := cq.Spec.ResourceGroups[0]
			if len(rg.Flavors) > 0 {
				for _, res := range rg.Flavors[0].Resources {
					switch res.Name {
					case CPUResource:
						allocation.CPUMilliCores = res.NominalQuota.MilliValue()
					case MemoryResource:
						allocation.MemoryBytes = res.NominalQuota.Value()
					case EphemeralStorageResource:
						allocation.EphemeralStorageBytes = res.NominalQuota.Value()
					case NVIDIAGPUResource, AMDGPUResource:
						allocation.GPUCount = res.NominalQuota.Value()
					}
				}
			}
		}

		quotaAllocations = append(quotaAllocations, allocation)
	}

	statusMsg := &messaging.ClusterQuotasStatusMessage{
		MessageType:      messaging.MessageTypeClusterQuotasStatusMessage,
		UpdatedAt:        time.Now(),
		QuotaAllocations: quotaAllocations,
	}

	if err := publisher.Publish(ctx, statusMsg); err != nil {
		return err
	}

	log.Info("published quota status",
		"name", config.Name,
		"cluster_queues", len(config.Spec.ClusterQueues),
	)

	return nil
}

func publishQuotasFailureMessage(ctx context.Context, publisher messaging.MessagePublisher, config *kaiwov1alpha1.KaiwoQueueConfig) error {
	log := ctrl.LoggerFrom(ctx)
	failureMessage := &messaging.ClusterQuotaFailureMessage{
		MessageType: messaging.MessageTypeClusterQuotasFailureMessage,
		UpdatedAt:   time.Now(),
		Reason:      "KaiwoQueueConfig status is failed",
	}

	if err := publisher.Publish(ctx, failureMessage); err != nil {
		return err
	}

	log.Info("published quota failure message",
		"name", config.Name,
	)

	return nil
}
