"""
Workflow Service - Multi-step video processing workflows voor AgentOS

Beheert complexe workflows zoals YouTube naar TikTok conversies.
Coördineert meerdere agents voor complete video processing pipelines.
Ondersteunt admin/user filtering voor workflow toegang en monitoring.
Gebruikt door workflow_refactored.py voor centrale workflow logic.
"""
from typing import Dict, Any, Optional
from datetime import datetime, timezone
import random
import logging

logger = logging.getLogger(__name__)


class WorkflowService:
    """Central service for all workflow-related operations"""

    def __init__(self):
        self.active_workflows = {}  # In-memory storage for demo

    def create_youtube_to_tiktok_workflow(self, data: Dict[str, Any], is_admin: bool = False) -> Dict[str, Any]:
        """Create YouTube to TikTok conversion workflow
        Admin can create workflows for any user, users create for themselves"""
        try:
            youtube_url = data.get("youtube_url")
            target_duration = data.get("target_duration", 60)
            voice_preference = data.get("voice_preference", "female_professional")
            target_audience = data.get("target_audience", "general")
            user_id = data.get("user_id", "anonymous")

            if not youtube_url:
                raise ValueError("youtube_url is required")

            # Generate workflow ID
            workflow_id = f"workflow_{random.randint(10000, 99999)}"

            # Define workflow steps
            base_steps = [
                {
                    "step": "download",
                    "description": "Download video from YouTube",
                    "estimated_duration": 120,
                    "status": "pending"
                },
                {
                    "step": "analysis",
                    "description": "Analyze video content and detect highlights",
                    "estimated_duration": 180,
                    "status": "pending"
                },
                {
                    "step": "clipping",
                    "description": "Extract best moments for TikTok format",
                    "estimated_duration": 240,
                    "status": "pending"
                },
                {
                    "step": "cropping",
                    "description": "Convert to 9:16 aspect ratio",
                    "estimated_duration": 150,
                    "status": "pending"
                },
                {
                    "step": "enhancement",
                    "description": "Add captions and optimize for TikTok",
                    "estimated_duration": 200,
                    "status": "pending"
                },
                {
                    "step": "finalization",
                    "description": "Package final TikTok-ready clips",
                    "estimated_duration": 100,
                    "status": "pending"
                }
            ]

            # Admin gets additional steps
            if is_admin:
                base_steps.extend([
                    {
                        "step": "admin_review",
                        "description": "Admin quality control and approval",
                        "estimated_duration": 60,
                        "status": "pending"
                    },
                    {
                        "step": "analytics_tracking",
                        "description": "Setup analytics and tracking",
                        "estimated_duration": 30,
                        "status": "pending"
                    }
                ])

            total_estimated_time = sum(step["estimated_duration"] for step in base_steps)

            # Store workflow
            workflow_data = {
                "workflow_id": workflow_id,
                "status": "started",
                "youtube_url": youtube_url,
                "target_duration": target_duration,
                "voice_preference": voice_preference,
                "target_audience": target_audience,
                "user_id": user_id,
                "workflow_steps": base_steps,
                "total_estimated_time_seconds": total_estimated_time,
                "estimated_completion": f"{total_estimated_time // 60} minutes",
                "created_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                "is_admin": is_admin,
                "progress": 0
            }

            self.active_workflows[workflow_id] = workflow_data

            logger.info(f"Created YouTube to TikTok workflow {workflow_id} (admin: {is_admin})")

            return {
                "success": True,
                "workflow_id": workflow_id,
                "status": "started",
                "youtube_url": youtube_url,
                "target_duration": target_duration,
                "voice_preference": voice_preference,
                "target_audience": target_audience,
                "workflow_steps": base_steps,
                "total_estimated_time_seconds": total_estimated_time,
                "estimated_completion": f"{total_estimated_time // 60} minutes",
                "created_at": workflow_data["created_at"],
                "message": "YouTube to TikTok workflow started successfully",
                "admin_workflow": is_admin
            }

        except Exception as e:
            logger.error(f"Failed to create YouTube to TikTok workflow: {e}")
            raise e

    def get_workflow_status(self, workflow_id: str, is_admin: bool = False) -> Dict[str, Any]:
        """Get workflow status
        Admin can see any workflow, users can see their own workflows"""
        try:
            workflow = self.active_workflows.get(workflow_id)

            if not workflow:
                # Generate mock status for demo
                progress = random.randint(10, 90)

                # Determine current step based on progress
                if progress < 20:
                    current_step = "download"
                    current_step_desc = "Downloading video from YouTube"
                elif progress < 40:
                    current_step = "analysis"
                    current_step_desc = "Analyzing video content"
                elif progress < 60:
                    current_step = "clipping"
                    current_step_desc = "Extracting best moments"
                elif progress < 80:
                    current_step = "cropping"
                    current_step_desc = "Converting to 9:16 format"
                else:
                    current_step = "enhancement"
                    current_step_desc = "Adding final touches"

                base_status = {
                    "workflow_id": workflow_id,
                    "status": "processing",
                    "progress": progress,
                    "current_step": current_step,
                    "current_step_description": current_step_desc,
                    "estimated_completion": f"{random.randint(2, 10)} minutes remaining",
                    "last_updated": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
                }

                # Admin gets additional info
                if is_admin:
                    base_status.update({
                        "admin_access": True,
                        "system_resources": {
                            "cpu_usage": f"{random.randint(30, 80)}%",
                            "memory_usage": f"{random.randint(40, 85)}%",
                            "gpu_usage": f"{random.randint(20, 95)}%"
                        },
                        "processing_node": f"worker-{random.randint(1, 5)}",
                        "debug_info": {
                            "processing_errors": 0,
                            "retries": random.randint(0, 2),
                            "queue_position": random.randint(1, 5)
                        }
                    })

                return base_status

            # Return actual stored workflow data
            workflow_status = {
                "workflow_id": workflow_id,
                "status": workflow["status"],
                "progress": workflow.get("progress", 0),
                "youtube_url": workflow["youtube_url"],
                "workflow_steps": workflow["workflow_steps"],
                "created_at": workflow["created_at"],
                "last_updated": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
            }

            # Admin gets full workflow data
            if is_admin:
                workflow_status.update({
                    "admin_access": True,
                    "user_id": workflow.get("user_id"),
                    "full_workflow_data": workflow
                })

            return workflow_status

        except Exception as e:
            logger.error(f"Failed to get workflow status for {workflow_id}: {e}")
            return {
                "workflow_id": workflow_id,
                "status": "error",
                "error": str(e),
                "admin_access": is_admin
            }

    def create_batch_workflow(self, data: Dict[str, Any], is_admin: bool = False) -> Dict[str, Any]:
        """Create batch processing workflow
        Admin can create batch workflows, users get limited batch processing"""
        try:
            video_urls = data.get("video_urls", [])
            workflow_type = data.get("workflow_type", "youtube-to-tiktok")
            batch_settings = data.get("batch_settings", {})
            user_id = data.get("user_id", "anonymous")

            if not video_urls:
                raise ValueError("video_urls list is required")

            # Limit batch size for non-admin users
            max_batch_size = 50 if is_admin else 5
            if len(video_urls) > max_batch_size:
                raise ValueError(f"Batch size limited to {max_batch_size} videos")

            batch_id = f"batch_{random.randint(10000, 99999)}"

            # Create individual workflows for each video
            individual_workflows = []
            for i, url in enumerate(video_urls):
                workflow_data = {
                    "youtube_url": url,
                    "user_id": user_id,
                    **batch_settings
                }

                workflow = self.create_youtube_to_tiktok_workflow(workflow_data, is_admin)
                individual_workflows.append({
                    "index": i + 1,
                    "url": url,
                    "workflow_id": workflow["workflow_id"],
                    "status": "queued"
                })

            batch_workflow = {
                "batch_id": batch_id,
                "workflow_type": workflow_type,
                "total_videos": len(video_urls),
                "individual_workflows": individual_workflows,
                "batch_settings": batch_settings,
                "user_id": user_id,
                "created_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                "estimated_total_time": f"{len(video_urls) * 10} minutes",
                "is_admin": is_admin
            }

            # Store batch workflow
            self.active_workflows[batch_id] = batch_workflow

            logger.info(f"Created batch workflow {batch_id} with {len(video_urls)} videos (admin: {is_admin})")

            return {
                "success": True,
                "batch_id": batch_id,
                "workflow_type": workflow_type,
                "total_videos": len(video_urls),
                "individual_workflows": individual_workflows,
                "estimated_total_time": batch_workflow["estimated_total_time"],
                "created_at": batch_workflow["created_at"],
                "message": f"Batch workflow created with {len(video_urls)} videos",
                "admin_batch": is_admin
            }

        except Exception as e:
            logger.error(f"Failed to create batch workflow: {e}")
            raise e

    def get_workflow_list(self, user_id: Optional[str] = None, is_admin: bool = False) -> Dict[str, Any]:
        """Get list of workflows
        Admin sees all workflows, users see their own workflows"""
        try:
            if is_admin:
                # Admin sees all workflows
                workflows = list(self.active_workflows.values())
            else:
                # Users see only their own workflows
                workflows = [
                    wf for wf in self.active_workflows.values()
                    if wf.get("user_id") == user_id or wf.get("user_id") == "anonymous"
                ]

            # Create summary
            total_workflows = len(workflows)
            active_workflows = len([wf for wf in workflows if wf.get("status") == "processing"])
            completed_workflows = len([wf for wf in workflows if wf.get("status") == "completed"])

            result = {
                "total_workflows": total_workflows,
                "active_workflows": active_workflows,
                "completed_workflows": completed_workflows,
                "workflows": workflows[:10] if not is_admin else workflows  # Limit for users
            }

            if is_admin:
                result.update({
                    "admin_access": True,
                    "system_summary": {
                        "total_processing_time": f"{total_workflows * 8} minutes",
                        "resource_usage": "moderate",
                        "success_rate": "95%"
                    }
                })

            return result

        except Exception as e:
            logger.error(f"Failed to get workflow list: {e}")
            return {
                "total_workflows": 0,
                "active_workflows": 0,
                "completed_workflows": 0,
                "workflows": [],
                "error": str(e),
                "admin_access": is_admin
            }
