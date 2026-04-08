"""
YouTube Analytics Tracker for monitoring video performance.

Tracks:
- Views, likes, comments, shares
- Click-through rate (CTR)
- Average view duration / retention
- Traffic sources
- Demographics
- Revenue (if monetized)

Auto-generates reports and recommendations.
"""

import asyncio
from datetime import datetime, timedelta
from typing import Optional
from loguru import logger

from config.settings import get_settings


class YouTubeAnalyticsTracker:
    """
    Track and analyze YouTube video performance.
    
    Metrics tracked:
    - Basic: views, likes, comments, shares
    - Engagement: CTR, watch time, retention
    - Growth: subscriber changes
    - Revenue: RPM, CPM (if applicable)
    """

    SCOPES = [
        "https://www.googleapis.com/auth/youtube.analytics.readonly",
        "https://www.googleapis.com/auth/youtube",
    ]
    TOKEN_FILE = "youtube_token.json"
    SECRETS_FILE = "client_secrets.json"

    def __init__(self):
        self.settings = get_settings()
        self._service = None

    async def get_video_stats(self, video_id: str, days: int = 7) -> dict:
        """
        Get comprehensive stats for a video.
        
        Returns:
        {
            "views": int,
            "likes": int,
            "comments": int,
            "shares": int,
            "ctr": float,  # Click-through rate %
            "watch_time_hours": float,
            "avg_view_duration_sec": float,
            "subscribers_gained": int,
        }
        """
        try:
            service = self._get_service()
        except Exception as e:
            logger.error(f"YouTube analytics auth failed: {e}")
            return self._empty_stats()

        loop = asyncio.get_event_loop()
        
        # Date range
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)

        metrics = await loop.run_in_executor(
            None,
            self._fetch_analytics_sync,
            service,
            video_id,
            start_date.strftime("%Y-%m-%d"),
            end_date.strftime("%Y-%m-%d"),
        )

        return metrics

    async def get_performance_report(self, video_id: str) -> dict:
        """
        Generate performance report with recommendations.
        
        Returns:
        {
            "video_id": "...",
            "status": "trending" | "stable" | "declining",
            "metrics": {...},
            "recommendations": [...],
            "next_milestone": {...},
        }
        """
        stats = await self.get_video_stats(video_id, days=7)
        
        # Analyze performance
        status = self._analyze_performance(stats)
        recommendations = self._generate_recommendations(stats, status)
        milestone = self._calculate_next_milestone(stats)

        return {
            "video_id": video_id,
            "status": status,
            "metrics": stats,
            "recommendations": recommendations,
            "next_milestone": milestone,
            "generated_at": datetime.utcnow().isoformat(),
        }

    async def track_all_videos(self, video_ids: list[str]) -> dict:
        """Track multiple videos and return comparative analytics."""
        tasks = [self.get_performance_stats(vid) for vid in video_ids]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        reports = {}
        for video_id, result in zip(video_ids, results):
            if isinstance(result, Exception):
                reports[video_id] = {"error": str(result)}
            else:
                reports[video_id] = result
        
        return reports

    def _fetch_analytics_sync(
        self,
        service,
        video_id: str,
        start_date: str,
        end_date: str,
    ) -> dict:
        """Fetch analytics data (sync)."""
        try:
            from googleapiclient.errors import HttpError

            # Fetch core metrics
            response = service.reports().query(
                ids="channel==MINE",
                startDate=start_date,
                endDate=end_date,
                metrics="views,estimatedMinutesWatched,averageViewDuration,likes,comments,sharesSubscribed",
                dimensions="day",
                filters=f"video=={video_id}",
            ).execute()

            # Parse response
            if "rows" not in response:
                return self._empty_stats()

            rows = response.get("rows", [])
            
            # Aggregate metrics
            total_views = sum(int(row[0]) for row in rows)
            total_watch_minutes = sum(float(row[1]) for row in rows)
            total_avg_duration = sum(float(row[2]) for row in rows) / len(rows) if rows else 0
            total_likes = sum(int(row[3]) for row in rows)
            total_comments = sum(int(row[4]) for row in rows)
            total_subscribers = sum(int(row[5]) for row in rows)

            # Calculate CTR (need separate request)
            ctr_response = service.reports().query(
                ids="channel==MINE",
                startDate=start_date,
                endDate=end_date,
                metrics="impressions,impressionsClickThroughRate",
                filters=f"video=={video_id}",
            ).execute()

            ctr = 0.0
            if "rows" in ctr_response and ctr_response["rows"]:
                ctr = float(ctr_response["rows"][0][1]) * 100  # Convert to percentage

            return {
                "views": total_views,
                "likes": total_likes,
                "comments": total_comments,
                "shares": 0,  # Not available in API
                "ctr": round(ctr, 2),
                "watch_time_hours": round(total_watch_minutes / 60, 2),
                "avg_view_duration_sec": round(total_avg_duration, 2),
                "subscribers_gained": total_subscribers,
                "period_days": (datetime.strptime(end_date, "%Y-%m-%d") - 
                               datetime.strptime(start_date, "%Y-%m-%d")).days,
            }

        except HttpError as e:
            logger.warning(f"Analytics fetch failed: {e}")
            return self._empty_stats()

    def _empty_stats(self) -> dict:
        """Return empty stats dict."""
        return {
            "views": 0,
            "likes": 0,
            "comments": 0,
            "shares": 0,
            "ctr": 0.0,
            "watch_time_hours": 0.0,
            "avg_view_duration_sec": 0.0,
            "subscribers_gained": 0,
            "period_days": 7,
        }

    def _analyze_performance(self, stats: dict) -> str:
        """Analyze performance status."""
        views = stats.get("views", 0)
        ctr = stats.get("ctr", 0)
        avg_duration = stats.get("avg_view_duration_sec", 0)

        # Trending: High views + high CTR
        if views > 1000 and ctr > 5:
            return "trending"
        
        # Declining: Low CTR + low retention
        if ctr < 2 and avg_duration < 30:
            return "declining"
        
        # Stable: Everything else
        return "stable"

    def _generate_recommendations(
        self,
        stats: dict,
        status: str,
    ) -> list[str]:
        """Generate improvement recommendations."""
        recommendations = []

        ctr = stats.get("ctr", 0)
        avg_duration = stats.get("avg_view_duration_sec", 0)
        views = stats.get("views", 0)

        # CTR recommendations
        if ctr < 3:
            recommendations.append(
                "📊 Low CTR: Consider updating thumbnail and title for better click appeal"
            )
        elif ctr > 8:
            recommendations.append(
                "✅ Great CTR! Your thumbnail/title combination is working well"
            )

        # Retention recommendations
        if avg_duration < 30:
            recommendations.append(
                "⏱️ Low retention: Hook viewers in first 15 seconds"
            )
        elif avg_duration > 60:
            recommendations.append(
                "✅ Strong retention: Viewers are engaged throughout"
            )

        # Growth recommendations
        if views > 5000:
            recommendations.append(
                "🚀 Momentum building: Consider creating a follow-up video"
            )

        return recommendations

    def _calculate_next_milestone(self, stats: dict) -> dict:
        """Calculate next view milestone."""
        views = stats.get("views", 0)
        
        # Determine next milestone
        if views < 1000:
            next_milestone = 1000
        elif views < 5000:
            next_milestone = 5000
        elif views < 10000:
            next_milestone = 10000
        elif views < 100000:
            next_milestone = 100000
        else:
            next_milestone = 1000000

        remaining = next_milestone - views
        progress_pct = (views / next_milestone) * 100

        return {
            "type": "views",
            "next": next_milestone,
            "remaining": max(0, remaining),
            "progress_pct": round(progress_pct, 1),
        }

    def _get_service(self):
        """Build authenticated YouTube Analytics API service."""
        if self._service:
            return self._service

        from google.oauth2.credentials import Credentials
        from google.auth.transport.requests import Request
        from google_auth_oauthlib.flow import InstalledAppFlow
        from googleapiclient.discovery import build

        creds = None

        if os.path.exists(self.TOKEN_FILE):
            creds = Credentials.from_authorized_user_file(self.TOKEN_FILE, self.SCOPES)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                if not os.path.exists(self.SECRETS_FILE):
                    raise FileNotFoundError(
                        f"Missing {self.SECRETS_FILE}."
                    )
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.SECRETS_FILE, self.SCOPES
                )
                creds = flow.run_local_server(port=0)

            with open(self.TOKEN_FILE, "w") as f:
                f.write(creds.to_json())

        self._service = build("youtubeAnalytics", "v2", credentials=creds)
        return self._service


# Convenience function
async def get_video_performance(video_id: str) -> dict:
    """Quick performance report for a video."""
    tracker = YouTubeAnalyticsTracker()
    return await tracker.get_performance_report(video_id)


import os
