# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

*** Settings ***
Documentation       Page object for AIRM UI cluster detail page.
...                 Provides selectors and atomic browser interactions for cluster statistics,
...                 nodes table, actions menu, kubeconfig drawer, and edit drawer.


*** Variables ***
${ACTIONS_BUTTON_TEXT}               Actions
${NODES_HEADING}                    Nodes
${GPU_UTILIZATION_TITLE}            GPU device utilization
${EDIT_CLUSTER_TITLE}               Edit Cluster
${KUBECONFIG_TITLE}                 View cluster kubeconfig


*** Keywords ***
Cluster detail should be loaded
    [Documentation]    Waits for the cluster detail page to load by checking for key elements.
    Wait For Elements State    css=main    visible    timeout=15s
    VAR    ${breadcrumb}    css=nav[aria-label="Breadcrumbs"]
    Wait For Elements State    ${breadcrumb}    visible    timeout=10s

Get cluster detail stats text
    [Documentation]    Returns the text content of the cluster detail statistics section.
    ...                Stats include: Available nodes, Assigned projects, Allocated GPUs, Running workloads.
    ${text}=    Get Text    css=main
    RETURN    ${text}

Nodes section should be visible
    [Documentation]    Waits for the Nodes accordion section heading to be visible.
    ...                Scrolls to the Nodes section since it may be below the viewport.
    Scroll To Element    css=h2:has-text("${NODES_HEADING}")
    Wait For Elements State    css=h2:has-text("${NODES_HEADING}")    visible    timeout=15s

GPU utilization chart should be visible
    [Documentation]    Waits for the GPU device utilization chart section to be visible.
    Wait For Elements State    css=span:text-is("${GPU_UTILIZATION_TITLE}")    visible    timeout=15s

Get node row count
    [Documentation]    Returns the number of node rows visible in the nodes table.
    ...                The nodes table is the last grid on the cluster detail page.
    ${count}=    Evaluate JavaScript    ${None}
    ...    (elem) => {
    ...        const grids = document.querySelectorAll('[role="grid"]');
    ...        const nodesGrid = grids[grids.length - 1];
    ...        if (!nodesGrid) return 0;
    ...        const bodyGroup = nodesGrid.querySelectorAll('[role="rowgroup"]')[1];
    ...        if (!bodyGroup) return 0;
    ...        return bodyGroup.querySelectorAll('[role="row"]').length;
    ...    }
    RETURN    ${count}

Click first node row
    [Documentation]    Clicks the first node row in the nodes table.
    ...                Gets the first node name via JavaScript and clicks it.
    ...                Caller must ensure nodes exist before calling this keyword.
    ${node_name}=    Evaluate JavaScript    ${None}
    ...    (elem) => {
    ...        const grids = document.querySelectorAll('[role="grid"]');
    ...        const nodesGrid = grids[grids.length - 1];
    ...        if (!nodesGrid) return null;
    ...        const bodyGroup = nodesGrid.querySelectorAll('[role="rowgroup"]')[1];
    ...        if (!bodyGroup) return null;
    ...        const firstHeader = bodyGroup.querySelector('[role="rowheader"]');
    ...        return firstHeader ? firstHeader.textContent.trim() : null;
    ...    }
    Click    text="${node_name}"

Open actions menu
    [Documentation]    Opens the Actions dropdown menu on the cluster detail page.
    Wait For Elements State    css=button:has-text("${ACTIONS_BUTTON_TEXT}")    visible    timeout=10s
    Click    css=button:has-text("${ACTIONS_BUTTON_TEXT}")

Click actions menu item
    [Documentation]    Clicks a specific item in the Actions dropdown menu.
    [Arguments]    ${item_text}
    VAR    ${item}    css=[role="menuitem"]:has-text("${item_text}")
    Wait For Elements State    ${item}    visible    timeout=10s
    Click    ${item}

Kubeconfig drawer should be visible
    [Documentation]    Checks that the kubeconfig drawer is visible with YAML content.
    Wait For Elements State    css=*:text-is("${KUBECONFIG_TITLE}")    visible    timeout=15s

Get kubeconfig drawer text
    [Documentation]    Returns the text content of the kubeconfig drawer.
    # The drawer is rendered outside main, as a sibling
    ${text}=    Get Text    css=body
    RETURN    ${text}

Edit drawer should be visible
    [Documentation]    Checks that the edit cluster drawer is visible.
    Wait For Elements State    css=*:text-is("${EDIT_CLUSTER_TITLE}")    visible    timeout=10s

Get edit drawer text
    [Documentation]    Returns the text content of the edit cluster drawer.
    ${text}=    Get Text    css=body
    RETURN    ${text}

Workloads page should be loaded
    [Documentation]    Waits for the cluster workloads page to load.
    ...                The workloads page shows a table or empty state for cluster workloads.
    Wait For Elements State    css=main    visible    timeout=15s

Get workloads page text
    [Documentation]    Returns the text content of the cluster workloads page.
    ${text}=    Get Text    css=main
    RETURN    ${text}

Node detail page should be loaded
    [Documentation]    Waits for the node detail page to load.
    Wait For Elements State    css=main    visible    timeout=15s

Get node detail page text
    [Documentation]    Returns the text content of the current node detail page.
    ${text}=    Get Text    css=main
    RETURN    ${text}
