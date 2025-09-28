#!/usr/bin/env python3
"""
Cron Management Routes - Only accessible to super admins
Integration of the render-cron-api functionality into the dashboard
"""

from fastapi import APIRouter, HTTPException, Depends, status
from typing import List, Dict, Any
from cron_models.cron_job import (
    CronJobCreate,
    CronJobUpdate,
    CronJobResponse,
    CronJobRunResponse,
    DealershipOnboard
)
from cron_services.cron_job_service import CronJobService
from cron_services.dealership_service import DealershipOnboardService
import httpx

# Authentication is enforced via UI; server-side enforcement can be added later

# Create router with prefix
router = APIRouter(prefix="/api/cron", tags=["Cron Management"])

# Initialize services
cron_service = CronJobService()
dealership_service = DealershipOnboardService()


@router.post("/jobs", response_model=Dict[str, Any], status_code=status.HTTP_201_CREATED)
async def create_cron_job(
    cron_job_data: CronJobCreate
):
    """
    Create a new cron job for dealership automation.

    This endpoint creates a Docker-based cron job that will:
    - Clone the specified GitHub repository
    - Run the automation script on schedule
    - Use customer-specific environment variables

    **Super Admin Only**
    """
    try:
        result = await cron_service.create_cron_job(cron_job_data)
        return {
            "success": True,
            "message": "Cron job created successfully",
            "service_id": result.get("id"),
            "service": result
        }
    except httpx.HTTPStatusError as e:
        raise HTTPException(
            status_code=e.response.status_code,
            detail=f"Render API error: {e.response.text}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create cron job: {str(e)}"
        )


@router.post("/onboard", response_model=Dict[str, Any])
async def onboard_dealership(
    onboard_data: DealershipOnboard
):
    """
    Complete dealership onboarding - creates both AM and PM cron jobs and dashboard user.

    This streamlined endpoint:
    - Creates AM processing job at specified time
    - Creates PM processing job at specified time
    - Creates dashboard user with access credentials
    - Returns all created resources

    **Super Admin Only**
    """
    try:
        result = await dealership_service.onboard_dealership(onboard_data)
        return {
            "success": True,
            "message": "Dealership onboarded successfully",
            "data": result
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to onboard dealership: {str(e)}"
        )


@router.get("/jobs", response_model=Dict[str, Any])
async def list_cron_jobs():
    """
    List all cron jobs configured in the system.

    **Super Admin Only**
    """
    try:
        services = await cron_service.list_cron_jobs()
        return {
            "success": True,
            "count": len(services),
            "services": services
        }
    except httpx.HTTPStatusError as e:
        raise HTTPException(
            status_code=e.response.status_code,
            detail=f"Render API error: {e.response.text}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list cron jobs: {str(e)}"
        )


@router.get("/jobs/{service_id}", response_model=Dict[str, Any])
async def get_cron_job(
    service_id: str
):
    """
    Get details of a specific cron job.

    **Super Admin Only**
    """
    try:
        service = await cron_service.get_cron_job(service_id)
        return {
            "success": True,
            "service": service
        }
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Cron job not found"
            )
        raise HTTPException(
            status_code=e.response.status_code,
            detail=f"Render API error: {e.response.text}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get cron job: {str(e)}"
        )


@router.patch("/jobs/{service_id}", response_model=Dict[str, Any])
async def update_cron_job(
    service_id: str,
    update_data: CronJobUpdate
):
    """
    Update an existing cron job.

    **Super Admin Only**
    """
    try:
        result = await cron_service.update_cron_job(service_id, update_data)
        return {
            "success": True,
            "message": "Cron job updated successfully",
            "service": result
        }
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Cron job not found"
            )
        raise HTTPException(
            status_code=e.response.status_code,
            detail=f"Render API error: {e.response.text}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update cron job: {str(e)}"
        )


@router.delete("/jobs/{service_id}", response_model=Dict[str, Any])
async def delete_cron_job(
    service_id: str
):
    """
    Delete a cron job.

    **Super Admin Only**
    """
    try:
        result = await cron_service.delete_cron_job(service_id)
        return {
            "success": True,
            "message": "Cron job deleted successfully"
        }
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Cron job not found"
            )
        raise HTTPException(
            status_code=e.response.status_code,
            detail=f"Render API error: {e.response.text}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete cron job: {str(e)}"
        )


@router.post("/jobs/{service_id}/trigger", response_model=Dict[str, Any])
async def trigger_cron_job(
    service_id: str
):
    """
    Manually trigger a cron job run.

    This will start an immediate execution of the cron job,
    regardless of its schedule.

    **Super Admin Only**
    """
    try:
        result = await cron_service.trigger_cron_job(service_id)
        return {
            "success": True,
            "message": "Cron job triggered successfully",
            "run_id": result.get("id"),
            "run": result
        }
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Cron job not found"
            )
        raise HTTPException(
            status_code=e.response.status_code,
            detail=f"Render API error: {e.response.text}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to trigger cron job: {str(e)}"
        )


@router.get("/jobs/{service_id}/runs", response_model=Dict[str, Any])
async def list_cron_job_runs(
    service_id: str
):
    """
    List runs for a specific cron job.

    **Super Admin Only**
    """
    try:
        runs = await cron_service.list_cron_job_runs(service_id)
        return {
            "success": True,
            "count": len(runs),
            "runs": runs
        }
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Cron job not found"
            )
        raise HTTPException(
            status_code=e.response.status_code,
            detail=f"Render API error: {e.response.text}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list cron job runs: {str(e)}"
        )


@router.delete("/jobs/{service_id}/runs/{run_id}", response_model=Dict[str, Any])
async def cancel_cron_job_run(
    service_id: str,
    run_id: str
):
    """
    Cancel a running cron job.

    This will terminate the currently running instance of the specified cron job.

    **Super Admin Only**
    """
    try:
        result = await cron_service.cancel_cron_job_run(service_id, run_id)
        return {
            "success": True,
            "message": "Cron job run cancelled successfully",
            "result": result
        }
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Cron job or run not found"
            )
        raise HTTPException(
            status_code=e.response.status_code,
            detail=f"Render API error: {e.response.text}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to cancel cron job run: {str(e)}"
        )
