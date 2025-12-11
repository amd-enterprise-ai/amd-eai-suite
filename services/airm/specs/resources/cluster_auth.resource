# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

*** Settings ***
Documentation       Resource file for cluster-auth service integration.
...                 Provides low-level keywords for interacting with the cluster-auth
...                 identity management and API key service.

Library             RequestsLibrary
Library             Collections
Library             String
Library             Process
Library             OperatingSystem


*** Variables ***
${CLUSTER_AUTH_BASE_URL}    %{CLUSTER_AUTH_URL=http://localhost:8081}
${CLUSTER_AUTH_API_VERSION}    v1
${CLUSTER_AUTH_TOKEN}       %{CLUSTER_AUTH_ADMIN_TOKEN=${EMPTY}}
${CLUSTER_AUTH_PORT_FORWARD_PID}    ${None}


*** Keywords ***
# Port Forwarding Setup Keywords
Initialize cluster auth port forwarding
    [Documentation]    Sets up port forwarding for cluster-auth service if not already running.
    ...    Only sets up port forwarding when running outside the cluster.
    ...    When running inside the cluster, updates the URL to use the internal service endpoint.

    # Check if we're running inside Kubernetes
    ${in_cluster}=    Run keyword and return status
    ...    File should exist    /var/run/secrets/kubernetes.io/serviceaccount/token

    IF    ${in_cluster}
        # Running inside cluster - use internal service URL
        ${internal_url}=    Set variable    http://cluster-auth.cluster-auth.svc.cluster.local:8081
        Set suite variable    ${CLUSTER_AUTH_BASE_URL}    ${internal_url}
        Log    Running inside cluster, using internal URL: ${internal_url}    console=yes
        RETURN
    END

    # Running outside cluster - need port forwarding
    Log    Running outside cluster, setting up port forwarding...    DEBUG

    # Check if port forwarding is already active
    ${port_forward_active}=    Run keyword and return status
    ...    Check cluster auth port is accessible

    IF    ${port_forward_active}
        Log    Cluster-auth port forwarding already active    DEBUG
        RETURN
    END

    # Check if cluster-auth service exists
    ${service_check}=    Run process    kubectl get service cluster-auth -n cluster-auth
    ...    shell=True

    IF    ${service_check.rc} != 0
        Log    Cluster-auth service not found in cluster, skipping port forwarding    WARN
        RETURN
    END

    # Start port forwarding in background
    ${process}=    Start process    kubectl    port-forward    service/cluster-auth    8081:8081    -n    cluster-auth

    Set suite variable    ${CLUSTER_AUTH_PORT_FORWARD_PID}    ${process}

    # Wait for port forwarding to be ready
    Wait until keyword succeeds    10s    1s
    ...    Check cluster auth port is accessible

    Log    Cluster-auth port forwarding established on localhost:8081    console=yes

Stop cluster auth port forwarding
    [Documentation]    Stops the cluster-auth port forwarding if it was started by the test

    IF    $CLUSTER_AUTH_PORT_FORWARD_PID is not None
        TRY
            Terminate process    ${CLUSTER_AUTH_PORT_FORWARD_PID}
            Log    Stopped cluster-auth port forwarding    DEBUG
        EXCEPT
            Log    Could not stop cluster-auth port forwarding process    WARN
        END
        Set suite variable    ${CLUSTER_AUTH_PORT_FORWARD_PID}    ${None}
    END

Check cluster auth port is accessible
    [Documentation]    Checks if cluster-auth service is accessible on the configured port

    TRY
        ${headers}=    Create dictionary    Content-Type=application/json
        ${response}=    Get    ${CLUSTER_AUTH_BASE_URL}/health
        ...    headers=${headers}
        ...    timeout=2
        Should be equal as integers    ${response.status_code}    200
    EXCEPT
        Fail    Cluster-auth service not accessible on ${CLUSTER_AUTH_BASE_URL}
    END

# Identity Management Keywords
Create identity
    [Documentation]    Creates a new identity in cluster-auth
    [Arguments]    ${name}    ${type}=user    ${metadata}=${None}

    ${identity_data}=    Create dictionary
    ...    name=${name}
    ...    type=${type}

    IF    ${metadata} is not None
        Set to dictionary    ${identity_data}    metadata=${metadata}
    END

    ${headers}=    Get cluster auth headers

    ${response}=    Post    ${CLUSTER_AUTH_BASE_URL}/api/${CLUSTER_AUTH_API_VERSION}/identities
    ...    json=${identity_data}
    ...    headers=${headers}

    RETURN    ${response}

Get identity
    [Documentation]    Gets an identity by ID
    [Arguments]    ${identity_id}

    ${headers}=    Get cluster auth headers

    ${response}=    Get    ${CLUSTER_AUTH_BASE_URL}/api/${CLUSTER_AUTH_API_VERSION}/identities/${identity_id}
    ...    headers=${headers}

    RETURN    ${response}

List identities
    [Documentation]    Lists all identities
    [Arguments]    ${filter}=${None}

    ${headers}=    Get cluster auth headers
    ${params}=    Create dictionary

    IF    ${filter} is not None
        Set to dictionary    ${params}    filter=${filter}
    END

    ${response}=    Get    ${CLUSTER_AUTH_BASE_URL}/api/${CLUSTER_AUTH_API_VERSION}/identities
    ...    headers=${headers}
    ...    params=${params}

    RETURN    ${response}

Delete identity
    [Documentation]    Deletes an identity
    [Arguments]    ${identity_id}

    ${headers}=    Get cluster auth headers

    ${response}=    Delete    ${CLUSTER_AUTH_BASE_URL}/api/${CLUSTER_AUTH_API_VERSION}/identities/${identity_id}
    ...    headers=${headers}

    RETURN    ${response}

# Group Management Keywords
Create group
    [Documentation]    Creates a new group in cluster-auth
    [Arguments]    ${name}    ${description}=${None}    ${policies}=@{EMPTY}

    ${group_data}=    Create dictionary
    ...    name=${name}

    IF    ${description} is not None
        Set to dictionary    ${group_data}    description=${description}
    END

    IF    ${policies}
        Set to dictionary    ${group_data}    policies=${policies}
    END

    ${headers}=    Get cluster auth headers

    ${response}=    Post    ${CLUSTER_AUTH_BASE_URL}/api/${CLUSTER_AUTH_API_VERSION}/groups
    ...    json=${group_data}
    ...    headers=${headers}

    RETURN    ${response}

Add identity to group
    [Documentation]    Adds an identity to a group
    [Arguments]    ${identity_id}    ${group_id}

    ${membership_data}=    Create dictionary
    ...    identity_id=${identity_id}
    ...    group_id=${group_id}

    ${headers}=    Get cluster auth headers

    ${response}=    Post    ${CLUSTER_AUTH_BASE_URL}/api/${CLUSTER_AUTH_API_VERSION}/groups/${group_id}/members
    ...    json=${membership_data}
    ...    headers=${headers}

    RETURN    ${response}

Remove identity from group
    [Documentation]    Removes an identity from a group
    [Arguments]    ${identity_id}    ${group_id}

    ${headers}=    Get cluster auth headers

    ${response}=    Delete    ${CLUSTER_AUTH_BASE_URL}/api/${CLUSTER_AUTH_API_VERSION}/groups/${group_id}/members/${identity_id}
    ...    headers=${headers}

    RETURN    ${response}

List group members
    [Documentation]    Lists members of a group
    [Arguments]    ${group_id}

    ${headers}=    Get cluster auth headers

    ${response}=    Get    ${CLUSTER_AUTH_BASE_URL}/api/${CLUSTER_AUTH_API_VERSION}/groups/${group_id}/members
    ...    headers=${headers}

    RETURN    ${response}

# API Key Management Keywords
Create api key
    [Documentation]    Creates a new API key
    [Arguments]    ${name}    ${description}=${None}    ${ttl}=${None}    ${policies}=@{EMPTY}

    ${key_data}=    Create dictionary
    ...    name=${name}

    IF    ${description} is not None
        Set to dictionary    ${key_data}    description=${description}
    END

    IF    ${ttl} is not None
        Set to dictionary    ${key_data}    ttl=${ttl}
    END

    IF    ${policies}
        Set to dictionary    ${key_data}    policies=${policies}
    END

    ${headers}=    Get cluster auth headers

    ${response}=    Post    ${CLUSTER_AUTH_BASE_URL}/apikey/create
    ...    json=${key_data}
    ...    headers=${headers}

    RETURN    ${response}

Get api key
    [Documentation]    Gets API key metadata (not the key value)
    [Arguments]    ${key_id}

    ${headers}=    Get cluster auth headers

    # Using lookup endpoint as per Jira SDA-2382
    ${lookup_data}=    Create dictionary    key_id=${key_id}
    ${response}=    Post    ${CLUSTER_AUTH_BASE_URL}/apikey/lookup
    ...    json=${lookup_data}
    ...    headers=${headers}

    RETURN    ${response}

List api keys
    [Documentation]    Lists all API keys for the current identity
    [Arguments]    ${status}=${None}

    ${headers}=    Get cluster auth headers
    ${params}=    Create dictionary

    IF    ${status} is not None
        Set to dictionary    ${params}    status=${status}
    END

    ${response}=    Get    ${CLUSTER_AUTH_BASE_URL}/api/${CLUSTER_AUTH_API_VERSION}/keys
    ...    headers=${headers}
    ...    params=${params}

    RETURN    ${response}

Revoke api key
    [Documentation]    Revokes an API key
    [Arguments]    ${key_id}

    ${headers}=    Get cluster auth headers

    ${response}=    Delete    ${CLUSTER_AUTH_BASE_URL}/api/${CLUSTER_AUTH_API_VERSION}/keys/${key_id}
    ...    headers=${headers}

    RETURN    ${response}

Rotate api key
    [Documentation]    Rotates an API key
    [Arguments]    ${key_id}

    ${headers}=    Get cluster auth headers

    ${response}=    Post    ${CLUSTER_AUTH_BASE_URL}/api/${CLUSTER_AUTH_API_VERSION}/keys/${key_id}/rotate
    ...    headers=${headers}

    RETURN    ${response}

# Key-Resource Mapping Keywords
Assign key to resource
    [Documentation]    Assigns an API key to a resource (e.g., model)
    [Arguments]    ${key_id}    ${resource_type}    ${resource_id}    ${permissions}=@{EMPTY}

    ${mapping_data}=    Create dictionary
    ...    key_id=${key_id}
    ...    resource_type=${resource_type}
    ...    resource_id=${resource_id}

    IF    ${permissions}
        Set to dictionary    ${mapping_data}    permissions=${permissions}
    END

    ${headers}=    Get cluster auth headers

    ${response}=    Post    ${CLUSTER_AUTH_BASE_URL}/api/${CLUSTER_AUTH_API_VERSION}/keys/${key_id}/mappings
    ...    json=${mapping_data}
    ...    headers=${headers}

    RETURN    ${response}

Remove key from resource
    [Documentation]    Removes API key mapping from a resource
    [Arguments]    ${key_id}    ${mapping_id}

    ${headers}=    Get cluster auth headers

    ${response}=    Delete    ${CLUSTER_AUTH_BASE_URL}/api/${CLUSTER_AUTH_API_VERSION}/keys/${key_id}/mappings/${mapping_id}
    ...    headers=${headers}

    RETURN    ${response}

Get key mappings
    [Documentation]    Gets all resource mappings for an API key
    [Arguments]    ${key_id}

    ${headers}=    Get cluster auth headers

    ${response}=    Get    ${CLUSTER_AUTH_BASE_URL}/api/${CLUSTER_AUTH_API_VERSION}/keys/${key_id}/mappings
    ...    headers=${headers}

    RETURN    ${response}

# Policy Management Keywords
Create policy
    [Documentation]    Creates a new access policy
    [Arguments]    ${name}    ${rules}    ${description}=${None}

    ${policy_data}=    Create dictionary
    ...    name=${name}
    ...    rules=${rules}

    IF    ${description} is not None
        Set to dictionary    ${policy_data}    description=${description}
    END

    ${headers}=    Get cluster auth headers

    ${response}=    Post    ${CLUSTER_AUTH_BASE_URL}/api/${CLUSTER_AUTH_API_VERSION}/policies
    ...    json=${policy_data}
    ...    headers=${headers}

    RETURN    ${response}

Attach policy to key
    [Documentation]    Attaches a policy to an API key
    [Arguments]    ${key_id}    ${policy_id}

    ${attachment_data}=    Create dictionary
    ...    policy_id=${policy_id}

    ${headers}=    Get cluster auth headers

    ${response}=    Post    ${CLUSTER_AUTH_BASE_URL}/api/${CLUSTER_AUTH_API_VERSION}/keys/${key_id}/policies
    ...    json=${attachment_data}
    ...    headers=${headers}

    RETURN    ${response}

Detach policy from key
    [Documentation]    Detaches a policy from an API key
    [Arguments]    ${key_id}    ${policy_id}

    ${headers}=    Get cluster auth headers

    ${response}=    Delete    ${CLUSTER_AUTH_BASE_URL}/api/${CLUSTER_AUTH_API_VERSION}/keys/${key_id}/policies/${policy_id}
    ...    headers=${headers}

    RETURN    ${response}

# Audit and Logging Keywords
Get api key audit log
    [Documentation]    Gets audit log for an API key
    [Arguments]    ${key_id}    ${limit}=100

    ${headers}=    Get cluster auth headers
    ${params}=    Create dictionary    limit=${limit}

    ${response}=    Get    ${CLUSTER_AUTH_BASE_URL}/api/${CLUSTER_AUTH_API_VERSION}/keys/${key_id}/audit
    ...    headers=${headers}
    ...    params=${params}

    RETURN    ${response}

Get access logs
    [Documentation]    Gets access logs for API keys
    [Arguments]    ${key_id}=${None}    ${resource_id}=${None}    ${status}=${None}    ${limit}=100

    ${headers}=    Get cluster auth headers
    ${params}=    Create dictionary    limit=${limit}

    IF    ${key_id} is not None
        Set to dictionary    ${params}    key_id=${key_id}
    END

    IF    ${resource_id} is not None
        Set to dictionary    ${params}    resource_id=${resource_id}
    END

    IF    ${status} is not None
        Set to dictionary    ${params}    status=${status}
    END

    ${response}=    Get    ${CLUSTER_AUTH_BASE_URL}/api/${CLUSTER_AUTH_API_VERSION}/logs/access
    ...    headers=${headers}
    ...    params=${params}

    RETURN    ${response}

# Rate Limiting Keywords
Set key rate limit
    [Documentation]    Sets rate limit for an API key
    [Arguments]    ${key_id}    ${requests_per_minute}    ${burst_size}=${None}

    ${rate_limit_data}=    Create dictionary
    ...    requests_per_minute=${requests_per_minute}

    IF    ${burst_size} is not None
        Set to dictionary    ${rate_limit_data}    burst_size=${burst_size}
    END

    ${headers}=    Get cluster auth headers

    ${response}=    Put    ${CLUSTER_AUTH_BASE_URL}/api/${CLUSTER_AUTH_API_VERSION}/keys/${key_id}/rate-limit
    ...    json=${rate_limit_data}
    ...    headers=${headers}

    RETURN    ${response}

Get key rate limit status
    [Documentation]    Gets current rate limit status for an API key
    [Arguments]    ${key_id}

    ${headers}=    Get cluster auth headers

    ${response}=    Get    ${CLUSTER_AUTH_BASE_URL}/api/${CLUSTER_AUTH_API_VERSION}/keys/${key_id}/rate-limit
    ...    headers=${headers}

    RETURN    ${response}

Reset key rate limit
    [Documentation]    Resets rate limit counter for an API key
    [Arguments]    ${key_id}

    ${headers}=    Get cluster auth headers

    ${response}=    Post    ${CLUSTER_AUTH_BASE_URL}/api/${CLUSTER_AUTH_API_VERSION}/keys/${key_id}/rate-limit/reset
    ...    headers=${headers}

    RETURN    ${response}

# Authentication Keywords
Validate api key
    [Documentation]    Validates an API key and returns its metadata
    [Arguments]    ${api_key}

    ${headers}=    Create dictionary
    ...    X-API-Key=${api_key}

    ${response}=    Post    ${CLUSTER_AUTH_BASE_URL}/api/${CLUSTER_AUTH_API_VERSION}/auth/validate
    ...    headers=${headers}

    RETURN    ${response}

Exchange token for api key
    [Documentation]    Exchanges a JWT token for an API key
    [Arguments]    ${jwt_token}

    ${exchange_data}=    Create dictionary
    ...    token=${jwt_token}

    ${headers}=    Create dictionary
    ...    Content-Type=application/json

    ${response}=    Post    ${CLUSTER_AUTH_BASE_URL}/api/${CLUSTER_AUTH_API_VERSION}/auth/exchange
    ...    json=${exchange_data}
    ...    headers=${headers}

    RETURN    ${response}

# Helper Keywords
Get cluster auth headers
    [Documentation]    Returns headers for cluster-auth API requests
    # Validate token is set
    IF    "${CLUSTER_AUTH_TOKEN}" == "${EMPTY}"
        Fail    CLUSTER_AUTH_ADMIN_TOKEN environment variable is not set.
        ...    Please export CLUSTER_AUTH_ADMIN_TOKEN='your-admin-token'
    END

    ${headers}=    Create dictionary
    ...    Content-Type=application/json
    ...    X-Admin-Token=${CLUSTER_AUTH_TOKEN}

    RETURN    ${headers}

Parse cluster auth response
    [Documentation]    Parses cluster-auth API response
    [Arguments]    ${response}

    ${status_code}=    Set variable    ${response.status_code}
    ${content}=    Set variable    ${response.text}

    TRY
        ${json_content}=    Evaluate    json.loads('''${content}''')    json
    EXCEPT
        ${json_content}=    Set variable    ${None}
    END

    ${result}=    Create dictionary
    ...    status_code=${status_code}
    ...    content=${content}
    ...    json=${json_content}

    RETURN    ${result}

Verify cluster auth response
    [Documentation]    Verifies cluster-auth API response is successful
    [Arguments]    ${response}    ${expected_status}=200

    ${parsed}=    Parse cluster auth response    ${response}

    Should be equal as integers    ${parsed}[status_code]    ${expected_status}
    ...    msg=Expected status ${expected_status} but got ${parsed}[status_code]: ${parsed}[content]

    RETURN    ${parsed}[json]

# HTTPRoute Authorization Keywords
Create httproute authorization
    [Documentation]    Creates HTTPRoute authorization for a route
    [Arguments]    ${route_name}    ${namespace}    ${api_keys}

    ${auth_data}=    Create dictionary
    ...    route_name=${route_name}
    ...    namespace=${namespace}
    ...    api_keys=${api_keys}

    ${headers}=    Get cluster auth headers

    ${response}=    Post    ${CLUSTER_AUTH_BASE_URL}/api/${CLUSTER_AUTH_API_VERSION}/httproute/auth
    ...    json=${auth_data}
    ...    headers=${headers}

    RETURN    ${response}

Update httproute authorization
    [Documentation]    Updates HTTPRoute authorization
    [Arguments]    ${route_name}    ${namespace}    ${api_keys}

    ${auth_data}=    Create dictionary
    ...    api_keys=${api_keys}

    ${headers}=    Get cluster auth headers

    ${response}=    Put    ${CLUSTER_AUTH_BASE_URL}/api/${CLUSTER_AUTH_API_VERSION}/httproute/auth/${namespace}/${route_name}
    ...    json=${auth_data}
    ...    headers=${headers}

    RETURN    ${response}

Delete httproute authorization
    [Documentation]    Deletes HTTPRoute authorization
    [Arguments]    ${route_name}    ${namespace}

    ${headers}=    Get cluster auth headers

    ${response}=    Delete    ${CLUSTER_AUTH_BASE_URL}/api/${CLUSTER_AUTH_API_VERSION}/httproute/auth/${namespace}/${route_name}
    ...    headers=${headers}

    RETURN    ${response}

Get httproute authorization
    [Documentation]    Gets HTTPRoute authorization configuration
    [Arguments]    ${route_name}    ${namespace}

    ${headers}=    Get cluster auth headers

    ${response}=    Get    ${CLUSTER_AUTH_BASE_URL}/api/${CLUSTER_AUTH_API_VERSION}/httproute/auth/${namespace}/${route_name}
    ...    headers=${headers}

    RETURN    ${response}
