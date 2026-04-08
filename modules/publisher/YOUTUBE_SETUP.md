# YouTube Auto-Upload System - Complete Setup Guide

## 🚀 A-Z Automated YouTube Posting

Your AutoMedia AI system now has **complete YouTube automation**:

```
Video Ready → Auto Metadata → Upload → Schedule → Publish → Analytics
```

---

## 📋 What's Automated

### ✅ Before Upload
- [x] SEO-optimized title generation (5 variants)
- [x] Description with hooks, timestamps, CTAs
- [x] Tag generation (broad + specific + trending)
- [x] Hashtag optimization
- [x] Thumbnail enhancement (text overlay, branding)
- [x] A/B test thumbnail variants

### ✅ During Upload
- [x] Video upload (resumable, chunked)
- [x] Custom thumbnail upload
- [x] Privacy management (private → scheduled → public)
- [x] Optimal timing calculation

### ✅ After Upload
- [x] Pinned comment posting (3 variants)
- [x] Community tab post
- [x] Analytics tracking (views, CTR, retention)
- [x] Performance reports with recommendations

---

## 🔧 Setup Instructions

### Step 1: Google Cloud Console Setup

1. **Create Project**
   - Go to https://console.cloud.google.com
   - Create new project: "AutoMedia AI"

2. **Enable APIs**
   - YouTube Data API v3
   - YouTube Analytics API

3. **Create OAuth Credentials**
   - Go to: APIs & Services → Credentials
   - Click "Create Credentials" → "OAuth client ID"
   - Application type: **Web application**
   - Authorized redirect URIs: `http://localhost:8080`
   - Download JSON → Save as `client_secrets.json` in project root

4. **Enable Required APIs**
   ```bash
   # Or enable via console:
   # YouTube Data API v3
   # YouTube Analytics API
   ```

### Step 2: Install Google API Libraries

```bash
pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib
```

### Step 3: First-Time OAuth Authorization

```bash
# Run this once to authorize
python -c "from modules.publisher.youtube_uploader_pro import YouTubeUploaderPro; YouTubeUploaderPro()._get_service()"
```

This will:
1. Open browser
2. Ask for Google account login
3. Request YouTube permissions
4. Save token to `youtube_token.json`

**Note:** Use the channel account you want to upload to.

### Step 4: Configure Upload Settings

Edit `.env`:

```bash
# Upload Defaults
YOUTUBE_DEFAULT_PRIVACY=private    # private | unlisted | public
YOUTUBE_SCHEDULE_HOURS=24          # Hours before publishing
YOUTUBE_CATEGORY=25                # 25=News, 24=Entertainment, 28=Science

# Auto-publish settings
AUTO_PUBLISH_ENABLED=true
AUTO_SCHEDULE_OPTIMAL=true         # Auto-calculate best time
```

---

## 📁 New Files Created

```
modules/publisher/
├── youtube_metadata.py        # SEO metadata generation
├── youtube_uploader_pro.py    # Enhanced uploader with scheduling
├── thumbnail_pro.py           # Pro thumbnail with variants
├── analytics_tracker.py       # Performance tracking
├── review_queue.py            # Updated with auto-approve
└── models.py                  # Updated models

workers/
└── tasks.py                   # Updated upload task
```

---

## 🎯 Usage

### Method 1: Automatic (Recommended)

Videos auto-upload after assembly when review is approved:

```bash
# Approve video (triggers auto-upload)
curl -X POST http://localhost:8000/api/v1/review/{job_id}/approve
```

### Method 2: Manual Upload

```bash
# Upload specific video
curl -X POST http://localhost:8000/api/v1/youtube/upload/{normalized_keyword}

# With scheduling
curl -X POST "http://localhost:8000/api/v1/youtube/schedule/{normalized_keyword}?hours=48"
```

### Method 3: API Endpoint

```python
from modules.publisher.youtube_uploader_pro import YouTubeUploaderPro
from modules.publisher.youtube_metadata import YouTubeMetadataOptimizer

# Generate metadata
optimizer = YouTubeMetadataOptimizer()
metadata = await optimizer.generate_complete_metadata(script, topic)

# Upload with scheduling
uploader = YouTubeUploaderPro()
result = await uploader.schedule_upload(
    video_path=Path("output/video.mp4"),
    metadata=metadata,
    thumbnail_path=Path("output/thumb.png"),
    hours_from_now=24,
)
```

---

## 📊 Metadata Generation

### Titles (5 Variants)

Generated using GPT-4o with SEO best practices:
- Under 60 characters (mobile display)
- Primary keyword in first 3 words
- Power words (BREAKING, EXCLUSIVE, REVEALED)
- Curiosity gap (not clickbait)

Example output:
```json
[
  "Breaking: Imran Khan Arrest Shocker",
  "Why Pakistan's Crisis Changed Everything",
  "The Truth About Khan's Arrest Revealed",
  "Pakistan Eruption: What They're Not Telling",
  "Khan Arrest: Inside the Political Earthquake"
]
```

### Description Structure

```
[HOOK - First 2 lines]
Latest breaking news on [topic]...

[BODY - 150-200 words]
Detailed summary with context...

[CALL TO ACTION]
Subscribe for more updates...

[TIMESTAMPS]
0:00 - Intro
0:15 - Key development
0:45 - Expert analysis

[HASHTAGS]
#pakistan #imrankhan #breaking
```

### Tags Strategy

- **Primary (3-5)**: Exact match keywords
- **Broad (5-8)**: General category tags
- **Long-tail (8-12)**: Specific phrases
- **Trending (5-7)**: Currently trending terms

---

## 🕐 Optimal Scheduling

Auto-calculated based on:

### Best Days for News/Politics
- **Tuesday - Thursday**: Highest engagement
- **Avoid**: Weekends (lower engagement)

### Best Times (UTC)
- **6-9 PM**: After work hours (peak)
- **12-2 PM**: Lunch break viewing

### Auto-Schedule Logic

```python
# If weekend → Move to Monday
# If Monday → Move to Tuesday
# Set to 7 PM UTC (midnight PK / 3 PM EST)
```

---

## 📈 Analytics Tracking

### Tracked Metrics

| Metric | Description |
|--------|-------------|
| Views | Total views in period |
| CTR | Click-through rate (%) |
| Watch Time | Total hours watched |
| Avg Duration | Average view duration |
| Likes/Comments | Engagement |
| Subscribers Gained | New subs from video |

### Performance Status

- **Trending**: High views + CTR > 5%
- **Stable**: Normal performance
- **Declining**: Low CTR + retention

### Auto-Recommendations

Generated based on performance:
- Low CTR → Update thumbnail/title
- Low retention → Improve hook
- High momentum → Create follow-up

---

## 🔍 API Endpoints

### Upload Video

```http
POST /api/v1/youtube/upload/{normalized_keyword}
```

**Response:**
```json
{
  "status": "success",
  "video_id": "abc123xyz",
  "url": "https://youtube.com/watch?v=abc123xyz",
  "privacy": "private",
  "scheduled_for": "2026-03-26T19:00:00Z",
  "thumbnail_uploaded": true,
  "pinned_comment_id": "comment123",
  "community_post_id": "post456"
}
```

### Schedule Upload

```http
POST /api/v1/youtube/schedule/{normalized_keyword}?hours=48
```

### Get Analytics

```http
GET /api/v1/youtube/analytics/{video_id}
```

**Response:**
```json
{
  "video_id": "abc123xyz",
  "status": "trending",
  "metrics": {
    "views": 5420,
    "likes": 342,
    "ctr": 6.8,
    "watch_time_hours": 180.5
  },
  "recommendations": [
    "Great CTR! Your thumbnail is working well",
    "Momentum building: Consider follow-up video"
  ]
}
```

### List Uploads

```http
GET /api/v1/youtube/uploads?limit=20
```

---

## 🎨 Thumbnail A/B Testing

### Generated Variants

Each video gets 3 thumbnails:
1. **Main**: Primary design
2. **Variant A**: Different color scheme
3. **Variant B**: Alternative layout

### Testing Workflow

1. Upload main thumbnail initially
2. Monitor CTR for 48 hours
3. If CTR < 3%, swap to variant A
4. Monitor another 48 hours
5. If still low, try variant B

### Manual Thumbnail Swap

```http
POST /api/v1/youtube/thumbnail/{video_id}/swap
{
  "variant": "A"  # or "B"
}
```

---

## ⚠️ Important Notes

### Upload Limits

- **New channels**: 50 videos/day
- **Verified channels**: 100 videos/day
- **Phone verification required** for custom thumbnails

### Privacy Workflow

```
Upload → Private (metadata check) → Scheduled → Public
```

**Why private first?**
- Verify metadata accuracy
- Check thumbnail quality
- Ensure proper scheduling
- Avoid public mistakes

### Copyright

- All content is original (GPT-4o scripts)
- Stock footage from Pexels/Pixabay (royalty-free)
- TTS voices licensed via OpenAI
- **You own all uploaded content**

---

## 🐛 Troubleshooting

### "Missing client_secrets.json"

**Solution:** Download from Google Cloud Console → Credentials

### "Thumbnail upload blocked"

**Cause:** Channel needs phone verification
**Fix:** Verify at youtube.com/verify

### "Quota exceeded"

YouTube API limits:
- 10,000 units/day (free tier)
- Upload = 1,600 units
- ~6 uploads/day on free tier

**Solution:** Request quota increase or upgrade

### "OAuth token expired"

**Fix:** Delete `youtube_token.json` and re-authorize

---

## 📊 Monitoring Dashboard

Coming soon: Real-time dashboard showing:
- Upload queue status
- Recent uploads with stats
- CTR comparison (thumbnail variants)
- Performance trends
- Revenue (if monetized)

---

## 🎯 Next Steps

1. ✅ Complete setup above
2. Test with single video upload
3. Review metadata quality
4. Enable auto-upload in production
5. Monitor analytics daily
6. Optimize based on performance

---

## 📞 Support

For issues:
1. Check logs: `docker-compose logs -f worker`
2. Verify OAuth setup
3. Check API quota: https://console.cloud.google.com/apis/dashboard

---

**Your AutoMedia AI system is now fully automated from topic discovery to YouTube upload! 🚀**
