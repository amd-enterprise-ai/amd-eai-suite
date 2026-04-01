# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

import asyncio
import os
import sys
from asyncio import Task
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import APIRouter, Depends, FastAPI
from fastapi_mcp import FastApiMCP
from loguru import logger
from sqlalchemy.exc import IntegrityError

from .clusters.router import router as clusters_router
from .health.router import router as health_router
from .messaging.admin import configure_inbound_vhost
from .messaging.consumer import start_consuming_from_common_feedback_queue
from .messaging.queues import configure_queues_for_common_vhost
from .metrics.service import init_prometheus_client
from .organizations.router import router as organizations_router
from .projects.router import router as projects_router
from .secrets.router import router as secrets_router
from .storages.router import router as storages_router
from .users.router import router as users_router
from .utilities.database import dispose_db, init_db
from .utilities.exceptions import (
    BaseAirmException,
    ConflictException,
    ExternalServiceError,
    ForbiddenException,
    InconsistentStateException,
    NotFoundException,
    PreconditionNotMetException,
    UnhealthyException,
    UploadFailedException,
    ValidationException,
)
from .utilities.fastapi import (
    base_airm_exception_handler,
    conflict_exception_handler,
    exception_group_handler,
    external_service_error_handler,
    forbidden_exception_handler,
    generic_exception_handler,
    inconsistent_state_exception_handler,
    integrity_error_handler,
    not_found_exception_handler,
    precondition_not_met_exception_handler,
    unhealthy_exception_handler,
    upload_failed_exception_handler,
    validation_exception_handler,
    value_error_handler,
)
from .utilities.keycloak_admin import init_keycloak_admin_client
from .utilities.prometheus_instrumentation import setup_instrumentation, start_metrics_server
from .utilities.security import create_logged_in_user_in_system, track_user_activity_from_token
from .workloads.router import router as workloads_router

load_dotenv(override=False)

consumer_task: Task | None = None


@asynccontextmanager
async def lifespan(app_lifespan: FastAPI) -> AsyncIterator[None]:
    await startup_event(app_lifespan)
    yield
    await shutdown_event(app_lifespan)


async def startup_event(app_lifespan: FastAPI) -> None:
    global consumer_task
    app_state = app_lifespan.state

    # Set logging level
    logger.remove()
    logger.add(sys.stderr, level="INFO")

    try:
        init_db()
    except Exception as e:
        logger.exception("Failed to connect to database", e)
        sys.exit(1)

    try:
        # Initialize Keycloak Admin Client and store in app.state
        app_state.keycloak_admin_client = await init_keycloak_admin_client()
    except Exception as e:
        logger.exception("Failed to initialize Keycloak admin client", e)
        sys.exit(1)

    try:
        # Initialize Prometheus Client and store in app.state
        app_state.prometheus_client = init_prometheus_client()
    except Exception as e:
        logger.exception("Failed to initialize Prometheus client", e)

    try:
        # Start listening inbound queue from the agents.
        await configure_inbound_vhost()
        await configure_queues_for_common_vhost()
        consumer_task = start_consuming_from_common_feedback_queue(app_state=app_state)
    except Exception as e:
        logger.exception("Failed to start listening inbound queue", e)
        sys.exit(1)

    try:
        start_metrics_server()
    except Exception as e:
        logger.exception("Failed to expose metrics", e)
        sys.exit(1)


async def shutdown_event(app_lifespan: FastAPI) -> None:
    global consumer_task
    if consumer_task:
        consumer_task.cancel()
        try:
            await consumer_task  # Wait for the task to actually cancel
        except asyncio.CancelledError:
            logger.info("Message consumer task cancelled successfully.")
        except Exception as e:
            logger.error(f"Error during consumer task shutdown: {e}")

    await dispose_db()


app = FastAPI(
    name="AMD Resource Manager API",
    lifespan=lifespan,
    title="AMD Resource Manager API",
    swagger_ui_init_oauth={
        "clientId": os.getenv("OPENID_CLIENT_ID", "354a0fa1-35ac-4a6d-9c4d-d661129c2cd0"),
        "scopes": "openid",
    },
)

api_unsecured_router = APIRouter()
api_unsecured_router.include_router(health_router, prefix="/v1")

api_secured_router = APIRouter(
    dependencies=[Depends(create_logged_in_user_in_system), Depends(track_user_activity_from_token)]
)
api_secured_router.include_router(users_router, prefix="/v1")
api_secured_router.include_router(organizations_router, prefix="/v1")
api_secured_router.include_router(clusters_router, prefix="/v1")
api_secured_router.include_router(workloads_router, prefix="/v1")
api_secured_router.include_router(projects_router, prefix="/v1")
api_secured_router.include_router(secrets_router, prefix="/v1")
api_secured_router.include_router(storages_router, prefix="/v1")


app.include_router(api_unsecured_router)
app.include_router(api_secured_router)

# Initialize MCP support AFTER routers are included
mcp = FastApiMCP(app)
mcp.mount()
# Refresh MCP server to ensure all routes are discovered
mcp.setup_server()

# Register exception handlers
app.add_exception_handler(Exception, generic_exception_handler)
app.add_exception_handler(ValueError, value_error_handler)  # type: ignore
app.add_exception_handler(ExceptionGroup, exception_group_handler)
app.add_exception_handler(BaseAirmException, base_airm_exception_handler)
app.add_exception_handler(NotFoundException, not_found_exception_handler)
app.add_exception_handler(IntegrityError, integrity_error_handler)
app.add_exception_handler(ConflictException, conflict_exception_handler)  # Handles DeletionConflictException too
app.add_exception_handler(ValidationException, validation_exception_handler)
app.add_exception_handler(UploadFailedException, upload_failed_exception_handler)
app.add_exception_handler(ForbiddenException, forbidden_exception_handler)
app.add_exception_handler(UnhealthyException, unhealthy_exception_handler)
app.add_exception_handler(PreconditionNotMetException, precondition_not_met_exception_handler)
app.add_exception_handler(ExternalServiceError, external_service_error_handler)
app.add_exception_handler(InconsistentStateException, inconsistent_state_exception_handler)

setup_instrumentation(app)
