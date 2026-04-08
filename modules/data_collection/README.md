# Multi-Source Data Collection System

## Overview

The enhanced data collection system eliminates dependency on mainstream media APIs (NewsAPI) by collecting from **6 independent source types**:

```
┌─────────────────────────────────────────────────────────────┐
│                    DATA SOURCES                              │
├─────────────────────────────────────────────────────────────┤
│  1. TWITTER/X        → Real-time opinions, eyewitnesses     │
│  2. REDDIT           → Community discussions, fact-checking │
│  3. RSS FEEDS        → Independent journalists, Substack    │
│  4. TELEGRAM         → On-ground reports, local channels    │
│  5. YOUTUBE          → Visual confirmation, citizen journalism │
│  6. NEWSAPI          → Mainstream coverage (for comparison) │
└─────────────────────────────────────────────────────────────┘
```

## Key Features

### ✓ 3+ Source Verification
Topics are **only validated** if they appear in **3+ independent source categories**:
- Social Media (Twitter, Telegram)
- Community Discussions (Reddit)
- Independent Media (RSS feeds)
- Video Evidence (YouTube)
- Mainstream Media (NewsAPI - for narrative tracking only)

### ✓ Bias Detection
Simple language analysis flags:
- **Loaded language**: Emotional/manipulative words
- **Sensationalism**: Clickbait patterns
- **Propaganda techniques**: False dichotomies, bandwagon appeals
- **One-sided sourcing**: All sources from same perspective
- **Unverified claims**: "Reportedly", "sources say"

### ✓ Focus Keywords
Your priority topics are **always collected** regardless of trending status:
- Pakistan politics
- Israel-Gaza conflict
- Imran Khan
- Regional developments

---

## Setup Instructions

### 1. Install New Dependencies

```bash
pip install -r requirements.txt
```

New packages:
- `praw` - Reddit API
- `tweepy` - Twitter API
- `feedparser` - RSS feeds
- `telethon` - Telegram client
- `textblob` - Sentiment analysis
- `nltk` - Language processing

### 2. Configure API Credentials

Edit `.env` file with your credentials:

#### Twitter/X (Optional but recommended)
```bash
TWITTER_BEARER_TOKEN=your_bearer_token_here
```
Get from: https://developer.twitter.com/en/portal/dashboard

**Note**: Free tier has limited search. Consider premium or use fallback.

#### Reddit (Recommended)
```bash
REDDIT_CLIENT_ID=your_client_id
REDDIT_CLIENT_SECRET=your_client_secret
REDDIT_USER_AGENT=AutoMediaAI/1.0
```
Get from: https://www.reddit.com/prefs/apps
- Create "script" app type
- Redirect URI: `http://localhost:8080`

#### Telegram (Optional)
```bash
TELEGRAM_API_ID=your_api_id
TELEGRAM_API_HASH=your_api_hash
TELEGRAM_CHANNELS=DawnNews,GeoNews,AlJazeera,Reuters
```
Get from: https://my.telegram.org/apps
- Login with phone number
- Create new application
- Copy `api_id` and `api_hash`

#### RSS Feeds (Auto-configured)
Default independent media feeds are pre-configured. Customize via:
```bash
CUSTOM_RSS_FEEDS=feed1_url|feed2_url|feed3_url
```

---

## Usage

### Automatic Collection

Celery Beat runs collection every 2 hours automatically:
```bash
docker-compose up -d
```

### Manual Trigger

```bash
curl -X POST http://localhost:8000/api/v1/collect/run
```

### Check Topics

```bash
curl http://localhost:8000/api/v1/topics
```

---

## Validation Logic

### Before (OLD - Flawed)
```
Topic validated if: NewsAPI + YouTube confirm
Problem: Both can be mainstream/controlled narrative
```

### After (NEW - Robust)
```
Topic validated if: 3+ INDEPENDENT categories confirm

Example validation:
✓ Twitter (eyewitness accounts)
✓ Reddit (community discussion)
✓ RSS feeds (independent journalists)
→ VALIDATED (3 categories)

Example rejection:
✗ Only NewsAPI + YouTube
→ NOT VALIDATED (both mainstream, only 1 category)
```

---

## Source Categories

| Source | Category | Trust Weight |
|--------|----------|--------------|
| Twitter (verified) | Expert | High |
| Twitter (eyewitness) | Eyewitness | Very High |
| Reddit discussions | Community | Medium-High |
| RSS (independent) | Independent | High |
| Telegram channels | Social | Medium |
| YouTube | Video | Medium-High |
| NewsAPI | Mainstream | Low-Medium |

---

## Bias Flags Explained

When a topic is validated, bias analysis runs:

```json
{
  "loaded_language": true,      // 3+ emotional words detected
  "sensationalism": false,      // No clickbait patterns
  "propaganda_patterns": false, // No manipulation techniques
  "one_sided_sources": true,    // All from same category
  "bias_score": 0.45            // 0-1 scale (higher = more biased)
}
```

**Action**: Topics with high bias scores (>0.7) still validated but flagged for script generation to handle carefully.

---

## Example Flow

### Topic: "Pakistan Imran Khan arrest"

1. **Discovery**:
   - Twitter: Trending hashtag #ImranKhan
   - Reddit: r/Pakistan hot posts
   - RSS: Independent journalists covering
   - NewsAPI: Mainstream headlines

2. **Validation**:
   - Twitter search → 50 tweets (engagement: 15K)
   - Reddit search → 20 discussions (5K upvotes)
   - RSS search → 15 articles
   - YouTube → 10 videos with transcripts

3. **Category Check**:
   - Social (Twitter) ✓
   - Community (Reddit) ✓
   - Independent (RSS) ✓
   - Video (YouTube) ✓
   - **Result**: 4 categories → VALIDATED ✓

4. **Bias Analysis**:
   - Loaded language: 2 sources (flagged)
   - Perspective diversity: High (good)
   - **Verdict**: Proceed with balanced script

---

## Troubleshooting

### "Zero candidates" error
- Check API credentials in `.env`
- Verify internet connection
- Some APIs rate-limited? Wait and retry

### Twitter not working
- Free API has limited search
- Consider premium or rely on other sources
- System works fine without Twitter (5 other sources)

### Reddit returning empty
- Check `REDDIT_CLIENT_ID` and `REDDIT_CLIENT_SECRET`
- Ensure app type is "script"
- User-agent must be descriptive

### Telegram not connecting
- Verify `TELEGRAM_API_ID` and `TELEGRAM_API_HASH`
- Phone number verification required first time
- Some channels may be private

---

## Customization

### Add More RSS Feeds

Edit `modules/data_collection/rss_feed_scraper.py`:

```python
INDEPENDENT_FEEDS = [
    {
        "name": "Your Feed Name",
        "url": "https://example.com/feed.xml",
        "category": "independent",
    },
    # Add more...
]
```

### Add More Telegram Channels

Edit `.env`:
```bash
TELEGRAM_CHANNELS=Channel1,Channel2,Channel3,YourChannel
```

### Adjust Validation Strictness

Edit `.env`:
```bash
MIN_SOURCES_TO_VALIDATE=3  # Increase to 4 for stricter validation
```

---

## Benefits Over Old System

| Aspect | Old (NewsAPI-dependent) | New (Multi-source) |
|--------|------------------------|-------------------|
| **Narrative Control** | Mainstream media decides | Ground truth from multiple sources |
| **Bias** | Single perspective | Diverse viewpoints |
| **Verification** | 2 sources min | 3+ independent categories |
| **Real-time** | Delayed (editorial process) | Instant (social media) |
| **Eyewitness** | None | Twitter, Telegram |
| **Expert Analysis** | Corporate media pundits | Independent journalists |
| **Community Input** | None | Reddit discussions |
| **Censorship Resistance** | Low (API can block topics) | High (decentralized sources) |

---

## Next Steps

1. **Get API credentials** (Reddit minimum, others optional)
2. **Test collection**: `curl -X POST http://localhost:8000/api/v1/collect/run`
3. **Monitor logs**: Check which sources are contributing
4. **Customize feeds**: Add your preferred independent journalists
5. **Review bias flags**: Adjust script generation based on flags

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    DATA COLLECTION ENGINE                    │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │ Twitter  │  │  Reddit  │  │ RSS Feeds│  │ Telegram │   │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘   │
│       │             │             │             │           │
│       └─────────────┴──────┬──────┴─────────────┘           │
│                            │                                 │
│                   ┌────────▼────────┐                       │
│                   │  Aggregation &  │                       │
│                   │  Deduplication  │                       │
│                   └────────┬────────┘                       │
│                            │                                 │
│       ┌────────────────────┼────────────────────┐           │
│       │                    │                    │           │
│  ┌────▼─────┐      ┌──────▼──────┐     ┌──────▼──────┐     │
│  │Validate  │      │Bias Analysis│     │Engagement   │     │
│  │(3+ cats) │      │(simple flags)│    │Scoring      │     │
│  └────┬─────┘      └──────┬──────┘     └──────┬──────┘     │
│       │                    │                    │           │
│       └────────────────────┼────────────────────┘           │
│                            │                                 │
│                   ┌────────▼────────┐                       │
│                   │  MongoDB Save   │                       │
│                   │  (VALIDATED)    │                       │
│                   └────────┬────────┘                       │
│                            │                                 │
│                   ┌────────▼────────┐                       │
│                   │ Script Gen Queue│                       │
│                   └─────────────────┘                       │
└─────────────────────────────────────────────────────────────┘
```

---

## Support

For issues or questions:
1. Check logs: `docker-compose logs -f worker`
2. Verify API credentials
3. Test individual scrapers manually
4. Review bias flags in validated topics
