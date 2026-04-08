"""
Upload Strategy Optimizer

Handles upload scheduling, rate limiting, queue management, and smart retry logic.
"""

import asyncio
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from collections import deque

from config.niche_config import niche_config_manager
from .models import (
    UploadJob,
    UploadStatus,
    UploadPriority,
    RateLimitConfig,
    UploadStrategy,
    UploadQueueStatus,
    UploadAnalytics,
    RetryConfig,
)


class UploadQueue:
    """
    Priority queue for upload jobs.
    
    Features:
    - Priority-based ordering
    - Rate limit awareness
    - Automatic retry scheduling
    """
    
    def __init__(self, max_size: int = 100):
        """
        Initialize the upload queue.
        
        Args:
            max_size: Maximum queue size
        """
        self._max_size = max_size
        self._queue: List[UploadJob] = []
        self._job_index: Dict[str, UploadJob] = {}
        self._completed_jobs: deque = deque(maxlen=100)
        self._lock = asyncio.Lock()
    
    async def add_job(self, job: UploadJob) -> bool:
        """
        Add a job to the queue.
        
        Args:
            job: Upload job to add
            
        Returns:
            True if added, False if queue is full
        """
        async with self._lock:
            if len(self._queue) >= self._max_size:
                return False
            
            self._queue.append(job)
            self._job_index[job.job_id] = job
            self._sort_queue()
            
            return True
    
    async def get_next_job(self) -> Optional[UploadJob]:
        """
        Get the next job to process.
        
        Returns:
            Next UploadJob or None if queue is empty
        """
        async with self._lock:
            if not self._queue:
                return None
            
            # Get highest priority job that's ready
            now = datetime.utcnow()
            
            for i, job in enumerate(self._queue):
                # Skip scheduled jobs that aren't ready
                if job.scheduled_time and job.scheduled_time > now:
                    continue
                
                # Skip jobs that are cooling down
                if job.next_retry_at and job.next_retry_at > now:
                    continue
                
                # Remove from queue and return
                self._queue.pop(i)
                if job.job_id in self._job_index:
                    del self._job_index[job.job_id]
                
                return job
            
            return None
    
    async def remove_job(self, job_id: str) -> Optional[UploadJob]:
        """Remove a job from the queue."""
        async with self._lock:
            if job_id not in self._job_index:
                return None
            
            job = self._job_index[job_id]
            self._queue.remove(job)
            del self._job_index[job_id]
            
            return job
    
    async def requeue_job(
        self,
        job: UploadJob,
        delay_seconds: int = 0
    ) -> None:
        """
        Requeue a job for retry.
        
        Args:
            job: Job to requeue
            delay_seconds: Delay before retry
        """
        async with self._lock:
            if delay_seconds > 0:
                job.next_retry_at = datetime.utcnow() + timedelta(seconds=delay_seconds)
                job.status = UploadStatus.RETRYING
            
            self._queue.append(job)
            self._job_index[job.job_id] = job
            self._sort_queue()
    
    async def mark_completed(self, job: UploadJob) -> None:
        """Mark a job as completed."""
        async with self._lock:
            job.completed_at = datetime.utcnow()
            job.status = UploadStatus.COMPLETED
            
            self._completed_jobs.append(job)
            
            if job.job_id in self._job_index:
                del self._job_index[job.job_id]
    
    async def mark_failed(
        self,
        job: UploadJob,
        error: str
    ) -> None:
        """Mark a job as failed."""
        async with self._lock:
            job.last_error = error
            job.retry_count += 1
            
            if job.retry_count >= job.max_retries:
                job.status = UploadStatus.FAILED
                self._completed_jobs.append(job)
            else:
                job.status = UploadStatus.RETRYING
            
            if job.job_id in self._job_index:
                del self._job_index[job.job_id]
    
    def _sort_queue(self) -> None:
        """Sort queue by priority and scheduled time."""
        priority_order = {
            UploadPriority.CRITICAL: 0,
            UploadPriority.HIGH: 1,
            UploadPriority.NORMAL: 2,
            UploadPriority.LOW: 3,
        }
        
        self._queue.sort(key=lambda j: (
            priority_order.get(j.priority, 2),
            j.scheduled_time or datetime.min,
        ))
    
    async def get_queue_status(self) -> UploadQueueStatus:
        """Get current queue status."""
        async with self._lock:
            now = datetime.utcnow()
            
            pending = sum(1 for j in self._queue if j.status == UploadStatus.PENDING)
            processing = sum(1 for j in self._queue if j.status == UploadStatus.PROCESSING)
            scheduled = sum(1 for j in self._queue if j.scheduled_time and j.scheduled_time > now)
            failed = sum(1 for j in self._completed_jobs if j.status == UploadStatus.FAILED)
            
            return UploadQueueStatus(
                total_jobs=len(self._queue) + len(self._completed_jobs),
                pending_jobs=pending,
                processing_jobs=processing,
                scheduled_jobs=scheduled,
                failed_jobs=failed,
                can_upload=True,  # Simplified
                rate_limit_reason="OK",
                uploads_today=len([
                    j for j in self._completed_jobs
                    if j.completed_at and j.completed_at.date() == now.date()
                ]),
                daily_limit=10,
                remaining_today=10,
                avg_upload_time_sec=0.0,
                success_rate=0.0,
            )
    
    async def get_jobs_by_status(
        self,
        status: UploadStatus
    ) -> List[UploadJob]:
        """Get all jobs with a specific status."""
        async with self._lock:
            return [j for j in self._queue if j.status == status]
    
    async def clear_completed(self) -> int:
        """Clear completed jobs from memory."""
        async with self._lock:
            count = len(self._completed_jobs)
            self._completed_jobs.clear()
            return count


class UploadStrategyOptimizer:
    """
    Upload strategy optimizer with rate limiting and smart retry.
    
    Features:
    - Rate limit management
    - Smart retry with exponential backoff
    - Optimal timing scheduling
    - Priority-based queue management
    - Error handling and recovery
    """
    
    # Upload costs in API quota units
    UPLOAD_COSTS = {
        "video_insert": 1600,
        "thumbnail_upload": 50,
        "metadata_update": 50,
        "comment_insert": 50,
    }
    
    def __init__(self, db=None):
        """
        Initialize the upload optimizer.
        
        Args:
            db: MongoDB database connection
        """
        self._db = db
        self._queue = UploadQueue(max_size=100)
        self._rate_limit = RateLimitConfig()
        self._retry_config = RetryConfig()
        self._strategies: Dict[str, UploadStrategy] = {}
        self._upload_callbacks: List[Callable] = []
        
        # Initialize default strategies
        self._initialize_default_strategies()
    
    def _initialize_default_strategies(self) -> None:
        """Initialize default upload strategies."""
        # Default strategy
        self._strategies["default"] = UploadStrategy(
            name="default",
            optimal_times=["09:00", "14:00", "18:00", "21:00"],
            uploads_per_day=5,
            min_interval_minutes=30,
        )
        
        # High-volume strategy
        self._strategies["high_volume"] = UploadStrategy(
            name="high_volume",
            optimal_times=["06:00", "09:00", "12:00", "15:00", "18:00", "21:00"],
            uploads_per_day=8,
            min_interval_minutes=20,
        )
        
        # Conservative strategy
        self._strategies["conservative"] = UploadStrategy(
            name="conservative",
            optimal_times=["10:00", "18:00"],
            uploads_per_day=2,
            min_interval_minutes=120,
        )
    
    async def create_upload_job(
        self,
        video_path: str,
        niche: str,
        topic: str,
        title: str,
        metadata: Optional[Dict[str, Any]] = None,
        thumbnail_path: Optional[str] = None,
        priority: Optional[UploadPriority] = None,
        scheduled_time: Optional[datetime] = None,
    ) -> UploadJob:
        """
        Create a new upload job.
        
        Args:
            video_path: Path to video file
            niche: Content niche
            topic: Video topic
            title: Video title
            metadata: Video metadata
            thumbnail_path: Path to thumbnail
            priority: Upload priority
            scheduled_time: Optional scheduled upload time
            
        Returns:
            Created UploadJob
        """
        # Get niche-specific settings
        niche_config = niche_config_manager.get_niche_by_value(niche)
        
        # Determine priority
        if priority is None:
            if niche_config:
                # Higher priority for niches with lower daily limits
                if niche_config.daily_upload_limit <= 2:
                    priority = UploadPriority.HIGH
                else:
                    priority = UploadPriority.NORMAL
            else:
                priority = UploadPriority.NORMAL
        
        # Determine scheduled time
        if scheduled_time is None and niche_config:
            # Schedule for next optimal time
            optimal_times = niche_config.optimal_posting_times
            if optimal_times:
                scheduled_time = self._get_next_optimal_time(optimal_times)
        
        # Create job
        job = UploadJob(
            job_id=str(uuid.uuid4()),
            video_path=video_path,
            niche=niche,
            topic=topic,
            title=title,
            thumbnail_path=thumbnail_path,
            metadata=metadata or {},
            priority=priority,
            scheduled_time=scheduled_time,
            max_retries=self._retry_config.max_retries,
        )
        
        # Add to queue
        await self._queue.add_job(job)
        
        return job
    
    def _get_next_optimal_time(
        self,
        optimal_times: List[str]
    ) -> datetime:
        """Get the next optimal upload time."""
        now = datetime.utcnow()
        
        # Parse optimal times
        times = []
        for t in optimal_times:
            hour, minute = map(int, t.split(":"))
            time = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
            if time <= now:
                time += timedelta(days=1)
            times.append(time)
        
        # Return earliest
        return min(times)
    
    async def process_next_upload(self) -> Optional[UploadJob]:
        """
        Process the next upload in the queue.
        
        Returns:
            Processed UploadJob or None
        """
        # Check rate limits
        allowed, reason = self._rate_limit.can_upload()
        if not allowed:
            return None
        
        # Get next job
        job = await self._queue.get_next_job()
        if not job:
            return None
        
        # Start processing
        job.status = UploadStatus.PROCESSING
        job.started_at = datetime.utcnow()
        
        try:
            # Execute upload (callback to actual uploader)
            await self._execute_upload(job)
            
            # Success
            self._rate_limit.record_upload()
            job.status = UploadStatus.COMPLETED
            job.completed_at = datetime.utcnow()
            
            await self._queue.mark_completed(job)
            
            # Notify callbacks
            await self._notify_upload_complete(job)
            
        except Exception as e:
            error_message = str(e)
            job.last_error = error_message
            
            # Determine if we should retry
            if self._retry_config.should_retry(error_message):
                delay = self._retry_config.get_delay_for_error(
                    error_message,
                    job.retry_count
                )
                
                job.status_message = f"Retry in {delay}s: {error_message}"
                await self._queue.requeue_job(job, delay)
            else:
                job.status_message = f"Failed: {error_message}"
                await self._queue.mark_failed(job, error_message)
        
        return job
    
    async def _execute_upload(self, job: UploadJob) -> None:
        """
        Execute the actual upload.
        
        This is a placeholder - in production, this would call
        the actual YouTube uploader.
        """
        # Simulate upload
        await asyncio.sleep(1)
        
        # In production, this would be:
        # result = await youtube_uploader.upload(
        #     video_path=job.video_path,
        #     metadata=job.metadata,
        #     thumbnail_path=job.thumbnail_path,
        # )
        # job.youtube_video_id = result.video_id
        # job.youtube_url = result.url
        # job.upload_response = result.response
    
    async def _notify_upload_complete(self, job: UploadJob) -> None:
        """Notify callbacks of upload completion."""
        for callback in self._upload_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(job)
                else:
                    callback(job)
            except Exception:
                pass  # Don't let callback errors affect upload
    
    def register_upload_callback(self, callback: Callable) -> None:
        """Register a callback for upload completion."""
        self._upload_callbacks.append(callback)
    
    async def handle_upload_error(
        self,
        job: UploadJob,
        error: str
    ) -> Dict[str, Any]:
        """
        Handle an upload error with smart retry logic.
        
        Args:
            job: Upload job that failed
            error: Error message
            
        Returns:
            Dict with retry decision and delay
        """
        # Check if error is retryable
        if not self._retry_config.should_retry(error):
            return {
                "retry": False,
                "reason": "Non-retryable error",
                "action": "mark_failed",
            }
        
        # Special handling for specific errors
        if "uploadLimitExceeded" in error or "daily limit" in error.lower():
            # 24 hour delay for daily limit
            return {
                "retry": True,
                "delay_seconds": 86400,
                "reason": "Daily upload limit - retry tomorrow",
                "action": "schedule_retry",
            }
        
        if "quota" in error.lower():
            # API quota exceeded - retry next day
            return {
                "retry": True,
                "delay_seconds": 86400,
                "reason": "API quota exceeded - retry tomorrow",
                "action": "schedule_retry",
            }
        
        if "network" in error.lower() or "connection" in error.lower():
            # Network error - quick retry
            delay = 60 * (2 ** job.retry_count)  # Exponential backoff
            return {
                "retry": True,
                "delay_seconds": min(delay, 3600),
                "reason": "Network error - quick retry",
                "action": "retry_soon",
            }
        
        # Default exponential backoff
        delay = self._retry_config.get_delay_for_error(error, job.retry_count)
        
        return {
            "retry": True,
            "delay_seconds": delay,
            "reason": f"Retry with exponential backoff ({delay}s)",
            "action": "retry",
        }
    
    def get_rate_limit_status(self) -> Dict[str, Any]:
        """Get current rate limit status."""
        allowed, reason = self._rate_limit.can_upload()
        
        return {
            "can_upload": allowed,
            "reason": reason,
            "daily_uploads": self._rate_limit.daily_uploads_count,
            "daily_limit": self._rate_limit.daily_upload_limit,
            "hourly_uploads": self._rate_limit.hourly_uploads_count,
            "hourly_limit": self._rate_limit.hourly_upload_limit,
            "consecutive_errors": self._rate_limit.consecutive_errors,
            "last_upload": self._rate_limit.last_upload_time.isoformat() if self._rate_limit.last_upload_time else None,
            "next_available": self._get_next_available_slot(),
        }
    
    def _get_next_available_slot(self) -> Optional[str]:
        """Get next available upload slot time."""
        if self._rate_limit.last_upload_time:
            next_time = self._rate_limit.last_upload_time + timedelta(
                seconds=self._rate_limit.upload_cooldown_sec
            )
            return next_time.isoformat()
        return None
    
    async def get_queue_status(self) -> UploadQueueStatus:
        """Get upload queue status."""
        return await self._queue.get_queue_status()
    
    def get_strategy(self, name: str) -> Optional[UploadStrategy]:
        """Get an upload strategy by name."""
        return self._strategies.get(name)
    
    def set_strategy(self, name: str, strategy: UploadStrategy) -> None:
        """Set or update an upload strategy."""
        self._strategies[name] = strategy
    
    async def get_analytics(
        self,
        days: int = 7
    ) -> Optional[UploadAnalytics]:
        """
        Get upload analytics.
        
        Args:
            days: Number of days to analyze
            
        Returns:
            UploadAnalytics or None if no data
        """
        if not self._db:
            return None
        
        try:
            from datetime import timedelta
            cutoff = datetime.utcnow() - timedelta(days=days)
            
            # Aggregate upload data
            pipeline = [
                {
                    "$match": {
                        "completed_at": {"$gte": cutoff},
                        "status": "completed",
                    }
                },
                {
                    "$group": {
                        "_id": "$niche",
                        "count": {"$sum": 1},
                        "avg_duration": {"$avg": "$upload_duration_sec"},
                    }
                },
            ]
            
            results = await self._db.video_uploads.aggregate(pipeline).to_list(length=100)
            
            if not results:
                return None
            
            return UploadAnalytics(
                period_start=cutoff,
                period_end=datetime.utcnow(),
                total_uploads=sum(r["count"] for r in results),
                successful_uploads=sum(r["count"] for r in results),
                failed_uploads=0,
                avg_upload_duration_sec=0.0,
                fastest_upload_sec=0.0,
                slowest_upload_sec=0.0,
                uploads_by_niche={r["_id"]: r["count"] for r in results},
                success_by_niche={r["_id"]: 100.0 for r in results},
            )
            
        except Exception:
            return None
    
    def reset_daily_limits(self) -> None:
        """Reset daily upload limits."""
        self._rate_limit.daily_uploads_count = 0
        self._rate_limit.hourly_uploads_count = 0
    
    async def cancel_job(self, job_id: str) -> bool:
        """Cancel an upload job."""
        job = await self._queue.remove_job(job_id)
        if job:
            job.status = UploadStatus.CANCELLED
            return True
        return False
    
    async def prioritize_job(
        self,
        job_id: str,
        priority: UploadPriority
    ) -> bool:
        """Change the priority of a job."""
        job = await self._queue.remove_job(job_id)
        if job:
            job.priority = priority
            await self._queue.add_job(job)
            return True
        return False
