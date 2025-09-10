"""
Render service for Manim animation processing.
Handles job creation, file management, and Manim CLI execution.
"""
import os
import uuid
import asyncio
import subprocess
import logging
from datetime import datetime
from typing import Dict, Optional, List
from pathlib import Path
import shutil

from app.config import config
from app.models import RenderJob, JobStore
from app.services.job_store import enhanced_job_store

logger = logging.getLogger(__name__)

class RenderService:
    """Service for managing Manim animation rendering."""
    
    def __init__(self):
        """Initialize render service with storage paths."""
        # Storage directories
        self.base_dir = Path(__file__).parent.parent.parent
        self.storage_dir = self.base_dir / "app" / "storage"
        self.code_dir = self.storage_dir / "code"
        self.videos_dir = self.storage_dir / "videos"
        
        # Use enhanced job store
        self.job_store = enhanced_job_store
        
        # Ensure directories exist
        self._ensure_directories()
        
        logger.info(f"Render service initialized")
        logger.info(f"Code directory: {self.code_dir}")
        logger.info(f"Videos directory: {self.videos_dir}")
    
    def _ensure_directories(self):
        """Ensure all required directories exist."""
        self.code_dir.mkdir(parents=True, exist_ok=True)
        self.videos_dir.mkdir(parents=True, exist_ok=True)
        
        # Create .gitkeep files if directories are empty
        if not any(self.code_dir.iterdir()):
            (self.code_dir / ".gitkeep").write_text("# Temp Manim code files")
        
        if not any(self.videos_dir.iterdir()):
            (self.videos_dir / ".gitkeep").write_text("# Rendered video files")
    
    def _generate_job_id(self) -> str:
        """Generate unique job ID."""
        return str(uuid.uuid4())
    
    def _get_safe_filepath(self, filename: str, extension: str) -> Path:
        """
        Get safe file path for given filename.
        
        Args:
            filename: Base filename (already validated)
            extension: File extension (with dot)
            
        Returns:
            Safe file path
        """
        # Add timestamp to prevent conflicts
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_filename = f"{filename}_{timestamp}{extension}"
        
        if extension == ".py":
            return self.code_dir / safe_filename
        elif extension == ".mp4":
            return self.videos_dir / safe_filename
        else:
            raise ValueError(f"Unsupported file extension: {extension}")
    
    def _save_code_file(self, filename: str, code: str) -> Path:
        """
        Save Manim code to file.
        
        Args:
            filename: Base filename
            code: Python code content
            
        Returns:
            Path to saved file
        """
        code_path = self._get_safe_filepath(filename, ".py")
        
        try:
            code_path.write_text(code, encoding="utf-8")
            logger.info(f"Saved code file: {code_path}")
            return code_path
            
        except Exception as e:
            logger.error(f"Failed to save code file: {e}")
            raise ValueError(f"Failed to save code file: {e}")
    
    def _get_scene_class_name(self, code: str) -> str:
        """
        Extract Scene class name from Manim code.
        
        Args:
            code: Python code content
            
        Returns:
            Scene class name
        """
        import re
        
        # Look for class that inherits from Scene
        pattern = r'class\s+(\w+)\s*\(\s*Scene\s*\)'
        match = re.search(pattern, code)
        
        if match:
            return match.group(1)
        
        # Fallback: look for any class definition
        pattern = r'class\s+(\w+)\s*\('
        match = re.search(pattern, code)
        
        if match:
            return match.group(1)
        
        raise ValueError("No Scene class found in code")
    
    async def _execute_manim_render(self, code_path: Path, scene_class: str, output_path: Path) -> bool:
        """
        Execute Manim rendering using subprocess.
        
        Args:
            code_path: Path to Python code file
            scene_class: Name of Scene class to render
            output_path: Expected output video path
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Construct Manim command
            cmd = [
                "manim",
                str(code_path),
                scene_class,
                f"--quality={config.MANIM_QUALITY.lower()}",
                f"--output_file={output_path.name}",
                "--disable_caching",
                "--write_to_movie"
            ]
            
            logger.info(f"Executing Manim command: {' '.join(cmd)}")
            
            # Execute with timeout
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=self.videos_dir  # Run in videos directory
            )
            
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=config.RENDER_TIMEOUT_SEC
            )
            
            # Check if process succeeded
            if process.returncode == 0:
                logger.info(f"Manim render successful: {output_path}")
                return True
            else:
                logger.error(f"Manim render failed with code {process.returncode}")
                logger.error(f"Stdout: {stdout.decode()}")
                logger.error(f"Stderr: {stderr.decode()}")
                return False
                
        except asyncio.TimeoutError:
            logger.error(f"Manim render timed out after {config.RENDER_TIMEOUT_SEC}s")
            return False
        except Exception as e:
            logger.error(f"Manim render exception: {e}")
            return False
    
    def create_render_job(self, filename: str, code: str) -> RenderJob:
        """
        Create a new render job.
        
        Args:
            filename: Base filename for output
            code: Manim code to render
            
        Returns:
            RenderJob with job ID and initial status
        """
        job_id = self._generate_job_id()
        current_time = datetime.utcnow().isoformat()
        
        # Create job record
        job_store = JobStore(
            id=job_id,
            status="queued",
            filename=filename,
            code=code,
            created_at=current_time,
            updated_at=current_time
        )
        
        self.job_store.add_job(job_store)
        
        logger.info(f"Created render job {job_id} for filename: {filename}")
        
        # Start rendering asynchronously
        asyncio.create_task(self._process_render_job(job_id))
        
        return RenderJob(
            jobId=job_id,
            status="queued",
            videoUrl=None,
            error=None
        )
    
    async def _process_render_job(self, job_id: str):
        """
        Process a render job asynchronously.
        
        Args:
            job_id: Job identifier
        """
        job = enhanced_job_store.get_job(job_id)
        if not job:
            logger.error(f"Job {job_id} not found")
            return
        
        try:
            logger.info(f"Starting render job {job_id}")
            
            # Update status to rendering
            self.job_store.update_job(job_id, status="rendering")
            
            # Save code to file
            code_path = self._save_code_file(job.filename, job.code)
            
            # Extract scene class name
            scene_class = self._get_scene_class_name(job.code)
            
            # Prepare output path
            video_path = self._get_safe_filepath(job.filename, ".mp4")
            
            # Execute Manim render
            success = await self._execute_manim_render(code_path, scene_class, video_path)
            
            if success and video_path.exists():
                # Render successful
                self.job_store.update_job(job_id, status="ready", video_path=str(video_path))
                logger.info(f"Render job {job_id} completed successfully")
            else:
                # Render failed
                self.job_store.update_job(job_id, status="error", error_message="Manim rendering failed")
                logger.error(f"Render job {job_id} failed")
            
            # Cleanup code file
            try:
                code_path.unlink()
                logger.info(f"Cleaned up code file: {code_path}")
            except Exception as e:
                logger.warning(f"Failed to cleanup code file: {e}")
                
        except Exception as e:
            # Handle any unexpected errors
            self.job_store.update_job(job_id, status="error", error_message=f"Render processing error: {str(e)}")
            logger.error(f"Render job {job_id} processing error: {e}")
    
    def get_job_status(self, job_id: str) -> Optional[RenderJob]:
        """
        Get current status of a render job.
        
        Args:
            job_id: Job identifier
            
        Returns:
            RenderJob with current status or None if not found
        """
        job = enhanced_job_store.get_job(job_id)
        if not job:
            return None
        
        # Generate video URL if ready
        video_url = None
        if job.status == "ready" and job.video_path:
            video_filename = Path(job.video_path).name
            video_url = f"/static/videos/{video_filename}"
        
        return RenderJob(
            jobId=job.id,
            status=job.status,
            videoUrl=video_url,
            error=job.error_message
        )
    
    def cleanup_old_jobs(self, max_age_hours: int = 24):
        """
        Clean up old jobs and files to prevent storage bloat.
        
        Args:
            max_age_hours: Maximum age of jobs to keep
        """
        return self.job_store.cleanup_old_jobs(max_age_hours)
    
    def get_job_stats(self) -> Dict[str, int]:
        """Get statistics about current jobs."""
        metrics = self.job_store.get_metrics()
        return {
            "total": metrics.total_jobs,
            **metrics.jobs_by_status
        }

# Global render service instance
render_service = RenderService()
