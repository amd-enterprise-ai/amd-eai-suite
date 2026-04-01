# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

*** Settings ***
Documentation       Shared AIWB keywords used across multiple resource files.
...                 Contains utility keywords that don't belong to any specific domain.
Resource            resources/common/resource_resolver.resource
Library             Collections


*** Keywords ***
Get Project Namespace
    [Documentation]    Returns the Kubernetes namespace for the current test project.
    ...    Decouples AIWB from AIRM project internals -- if namespace derivation changes,
    ...    only this keyword needs updating.
    ${project}=    The project object
    ${namespace}=    Get From Dictionary    ${project}    name
    RETURN    ${namespace}
