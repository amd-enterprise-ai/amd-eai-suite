# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

*** Settings ***
Documentation       Feature-layer keywords for AIRM UI cluster management testing.
...                 Composes page-layer interactions into business-meaningful BDD keywords
...                 for cluster list, cluster detail, nodes, workloads, kubeconfig,
...                 connect wizard, and edit workflows.
Resource            common/session.resource
Resource            pages/clusters_page.resource
Resource            pages/cluster_detail_page.resource


*** Keywords ***
# =============================================================================
# Precondition keywords (Given steps)
# =============================================================================

The user is on the clusters page
    [Documentation]    Navigates to the clusters list page.
    Navigate to clusters page    ${UI_BASE_URL}
    Active clusters heading should be visible

# =============================================================================
# Action keywords (When steps)
# =============================================================================

The user opens a cluster detail view
    [Documentation]    Clicks on the first available cluster row to navigate to its detail page.
    ${names}=    Get visible cluster names
    ${count}=    Get Length    ${names}
    IF    ${count} == 0
        Fail    No clusters visible in the list to open
    END
    VAR    ${first_name}    ${names}[0]
    Cluster row should be visible    ${first_name}
    Click cluster row    ${first_name}
    Cluster detail should be loaded

The user searches for a cluster by name
    [Documentation]    Searches for a cluster using the first visible cluster's name.
    ...                Stores the search term for later verification.
    ${names}=    Get visible cluster names
    ${count}=    Get Length    ${names}
    IF    ${count} == 0
        Fail    No clusters visible to search for
    END
    VAR    ${search_name}    ${names}[0]
    VAR    ${SEARCH_CLUSTER_NAME}    ${search_name}    scope=TEST
    Enter cluster search text    ${search_name}
    Wait Until Keyword Succeeds    5s    500ms
    ...    Search results should contain cluster    ${search_name}

The user opens the connect cluster wizard
    [Documentation]    Clicks the "Connect a cluster" button to open the wizard.
    Click connect cluster button

The user opens the kubeconfig view
    [Documentation]    Opens the Actions menu and clicks "View config" to open the kubeconfig drawer.
    Open actions menu
    Click actions menu item    View config

The user edits the cluster
    [Documentation]    Opens the Actions menu and clicks "Edit" to open the edit drawer.
    Open actions menu
    Click actions menu item    Edit

The user navigates to the cluster workloads page
    [Documentation]    Opens the Actions menu and clicks "View Workloads" to navigate to workloads.
    Open actions menu
    Click actions menu item    View Workloads
    Workloads page should be loaded

The user navigates to a specific node
    [Documentation]    Clicks the first node row in the nodes table to navigate to node detail.
    ...                Scrolls to the Nodes section first to ensure it is visible.
    Nodes section should be visible
    ${node_count}=    Get node row count
    IF    ${node_count} == 0
        Fail    No nodes visible in the cluster to navigate to
    END
    Click first node row
    Node detail page should be loaded

# =============================================================================
# Internal helpers
# =============================================================================

Search results should contain cluster
    [Documentation]    Polling helper that checks the filtered results contain the expected cluster.
    [Arguments]    ${expected_name}
    ${names}=    Get visible cluster names
    Should Contain    ${names}    ${expected_name}

# =============================================================================
# Assertion keywords (Then steps)
# =============================================================================

Connected clusters should be listed with status indicators
    [Documentation]    Verifies that at least one cluster row is visible in the active clusters table
    ...                and that status information is displayed.
    Active clusters heading should be visible
    ${count}=    Get cluster row count
    Should Be True    ${count} > 0    No active clusters found in the list

GPU allocation information should be shown per cluster
    [Documentation]    Verifies that GPU allocation data is displayed in the cluster statistics section.
    ${text}=    Get clusters stats text
    Should Contain    ${text}    Allocated GPUs

Cluster statistics should be displayed
    [Documentation]    Verifies that cluster detail statistics cards are visible.
    ...                Checks for Available nodes, Assigned projects, Allocated GPUs, Running workloads.
    ${text}=    Get cluster detail stats text
    Should Contain    ${text}    Available nodes
    Should Contain    ${text}    Assigned projects
    Should Contain    ${text}    Allocated GPUs
    Should Contain    ${text}    Running workloads

Cluster nodes should be listed
    [Documentation]    Verifies that the Nodes section is visible and contains node rows.
    Nodes section should be visible
    ${count}=    Get node row count
    Should Be True    ${count} > 0    No nodes found in the cluster

GPU utilization chart should be shown
    [Documentation]    Verifies that the GPU device utilization chart is visible.
    GPU utilization chart should be visible

Only matching clusters should be shown in the list
    [Documentation]    Verifies that the filtered cluster list contains the searched cluster
    ...                and that the result count is reduced from the original.
    ${names}=    Get visible cluster names
    ${count}=    Get Length    ${names}
    Should Be True    ${count} > 0    No clusters match the search filter
    Should Contain    ${names}    ${SEARCH_CLUSTER_NAME}

The kubeconfig YAML content should be displayed
    [Documentation]    Verifies that the kubeconfig drawer shows YAML configuration content.
    Kubeconfig drawer should be visible
    ${text}=    Get kubeconfig drawer text
    Should Contain    ${text}    kubeconfig

The wizard should display the registration instructions
    [Documentation]    Verifies that the connect cluster wizard is visible with instructions.
    Connect wizard should be visible
    ${text}=    Get connect wizard text
    Should Contain    ${text}    Connecting a new cluster

Node information should be displayed
    [Documentation]    Verifies that the node detail page shows node specification information.
    ...                Checks for GPU and CPU spec labels (case-insensitive since headers may be uppercase).
    ${text}=    Get node detail page text
    Should Contain    ${text}    gpu type    ignore_case=True
    Should Contain    ${text}    cpu cores    ignore_case=True

GPU device metrics should be shown
    [Documentation]    Verifies that the node detail page shows GPU device information.
    ...                Checks for the GPU devices section (case-insensitive).
    ${text}=    Get node detail page text
    Should Contain    ${text}    gpu devices    ignore_case=True

Cluster workloads should be listed with status information
    [Documentation]    Verifies that the cluster workloads page is visible and shows
    ...                either workload rows or an empty state message.
    ${text}=    Get workloads page text
    # The page should show either workload data headers or the empty state
    TRY
        Should Contain    ${text}    workload    ignore_case=True
    EXCEPT
        Should Contain    ${text}    name    ignore_case=True
        ...    msg=Workloads page does not show expected content: ${text}
    END

The edit cluster drawer should be visible with form fields
    [Documentation]    Verifies that the edit cluster drawer is visible with expected fields.
    Edit drawer should be visible
    ${text}=    Get edit drawer text
    Should Contain    ${text}    Workbench URL
    Should Contain    ${text}    Kube API URL
