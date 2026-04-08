# Multi-Niche Viral Content Engine

## Documentation & Usage Guide

---

## 📋 Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Supported Niches](#supported-niches)
4. [API Reference](#api-reference)
5. [Usage Examples](#usage-examples)
6. [Celery Tasks](#celery-tasks)
7. [Configuration](#configuration)
8. [Best Practices](#best-practices)

---

## Overview

The **Multi-Niche Viral Content Engine** is a scalable, production-ready system for generating viral-optimized video content across multiple niches. It replaces the single-niche (current affairs) limitation with a dynamic, extensible architecture.

### Key Features

- **12 Supported Niches**: Motivation, Finance, AI/Tech, Islamic, Health, History, Facts, Horror, Relationships, Business, Trending, Current Affairs
- **Smart Topic Discovery**: Trend-aware topic generation with virality scoring (0-100)
- **Viral Script Generation**: Proven hook frameworks, retention optimization, emotional triggers
- **Algorithm Optimization**: CTR-optimized titles, SEO descriptions, search-optimized tags
- **Content Variation**: Ensures each video feels unique through tone/style randomization
- **Smart Upload Scheduling**: Rate limiting, queue management, optimal timing

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        VIRAL CONTENT ENGINE                              │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐               │
│  │    Niche     │    │    Smart     │    │    Viral     │               │
│  │   Manager    │───▶│  Discovery   │───▶│   Script     │               │
│  │              │    │    Engine    │    │  Generator   │               │
│  └──────────────┘    └──────────────┘    └──────────────┘               │
│         │                   │                   │                        │
│         ▼                   ▼                   ▼                        │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐               │
│  │   Niche      │    │   Virality   │    │     Hook     │               │
│  │   Configs    │    │  Calculator  │    │   Library    │               │
│  └──────────────┘    └──────────────┘    └──────────────┘               │
│                                                                          │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐               │
│  │  Algorithm   │    │   Content    │    │    Upload    │               │
│  │  Optimizer   │◀───│  Variation   │◀───│  Strategy    │               │
│  │              │    │    Engine    │    │  Optimizer   │               │
│  └──────────────┘    └──────────────┘    └──────────────┘               │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

### Module Structure

```
automedia-ai-m1/
├── config/
│   └── niche_config.py          # Niche configurations & strategies
├── modules/
│   ├── niche_manager/           # Niche selection & strategy
│   ├── smart_discovery/         # Topic discovery & virality scoring
│   ├── viral_script_generator/  # Script generation with hooks
│   ├── algorithm_optimizer/     # Metadata optimization
│   ├── content_variation/       # Content diversity engine
│   └── upload_optimizer/        # Upload scheduling & rate limiting
├── workers/
│   └── viral_tasks.py           # Celery tasks for async processing
└── api/
    └── viral_router.py          # REST API endpoints
```

---

## Supported Niches

| Niche | ID | Target Duration | Daily Limit | Best For |
|-------|-----|-----------------|-------------|----------|
| Motivation | `motivation` | 120s | 4 | Self-improvement, success stories |
| Finance | `finance` | 150s | 3 | Investing, money tips, crypto |
| AI/Tech | `ai_tech` | 120s | 5 | AI tools, tech news, future tech |
| Islamic | `islamic` | 90s | 3 | Reminders, Quran, hadith, stories |
| Health & Fitness | `health_fitness` | 120s | 4 | Workouts, nutrition, wellness |
| History | `history` | 180s | 2 | Documentaries, historical events |
| Facts/Did You Know | `facts_did_you_know` | 60s | 6 | Mind-blowing facts, trivia |
| Horror Stories | `horror_stories` | 180s | 2 | True crime, paranormal, scary |
| Relationships | `relationships` | 120s | 4 | Dating advice, psychology |
| Business | `business` | 150s | 3 | Entrepreneurship, success stories |
| Trending/Viral | `trending_viral` | 60s | 8 | Currently trending topics |
| Current Affairs | `current_affairs` | 120s | 5 | Breaking news, politics |

---

## API Reference

### Base URL
```
http://localhost:8000/api/v2/viral
```

### Niche Management

#### Get All Niches
```http
GET /niches
```

Response:
```json
{
  "success": true,
  "niches": [
    {
      "id": "motivation",
      "name": "Motivation & Self-Improvement",
      "description": "Inspirational content to motivate and uplift viewers",
      "virality_threshold": 65,
      "daily_limit": 4
    }
  ]
}
```

#### Get Niche Configuration
```http
GET /niches/{niche}
```

#### Get Niche Sources
```http
GET /niches/{niche}/sources
```

#### Get Optimal Posting Time
```http
GET /niches/{niche}/optimal-time
```

### Topic Discovery

#### Discover Viral Topics
```http
POST /topics/discover
Content-Type: application/json

{
  "niche": "motivation",
  "region": "US",
  "language": "en",
  "max_topics": 10,
  "min_virality_score": 60,
  "exclude_keywords": ["politics", "religion"]
}
```

Response:
```json
{
  "success": true,
  "niche": "motivation",
  "topics": [
    {
      "niche": "motivation",
      "topic": "Why Successful People Wake Up at 5 AM",
      "normalized_keyword": "successful_people_wake_5am",
      "virality_score": 85.5,
      "virality_breakdown": {
        "trend": 80.0,
        "emotional": 85.0,
        "ctr": 88.0,
        "engagement": 82.0,
        "novelty": 75.0
      },
      "reason": "Topic shows highly trending and strong emotional impact",
      "emotional_triggers": ["inspiration", "curiosity"],
      "ctr_patterns": ["why_question"],
      "is_validated": true,
      "tags": ["motivation", "success", "habits"]
    }
  ],
  "total_discovered": 10,
  "total_validated": 8,
  "avg_virality_score": 78.5
}
```

#### Score Topic Virality
```http
POST /topics/score
Content-Type: application/json

{
  "niche": "finance",
  "topic": "Why The Stock Market Is About To Crash"
}
```

### Script Generation

#### Generate Viral Script
```http
POST /scripts/generate
Content-Type: application/json

{
  "niche": "ai_tech",
  "topic": "This New AI Can Do What Humans Can't",
  "target_duration_sec": 90,
  "creativity_factor": 0.7,
  "hook_framework": "you_wont_believe"
}
```

Response:
```json
{
  "success": true,
  "script": {
    "niche": "ai_tech",
    "topic": "This New AI Can Do What Humans Can't",
    "title": "This New AI {topic} Will Blow Your Mind",
    "hook_framework": "you_wont_believe",
    "hook_text": "You won't believe what just happened with AI.",
    "segments": [
      {
        "type": "hook",
        "order": 1,
        "text": "You won't believe what just happened with AI.",
        "duration_estimate_sec": 3.0,
        "has_pattern_interrupt": true
      }
    ],
    "full_text": "You won't believe what just happened with AI...",
    "estimated_duration_sec": 90.5,
    "retention_score": 85.0,
    "pacing_score": 82.0
  },
  "retention_analysis": {
    "retention_score": 85,
    "hook_effectiveness": 90,
    "pattern_interrupt_count": 4,
    "recommendations": ["Strong pattern interrupts throughout"]
  }
}
```

### Metadata Optimization

#### Optimize Metadata
```http
POST /metadata/optimize
Content-Type: application/json

{
  "niche": "motivation",
  "topic": "The Morning Routine That Changed My Life",
  "script_title": "Why Your Morning Routine Is Failing",
  "script_content": "Full script text here...",
  "platform": "youtube",
  "video_format": "standard"
}
```

### Content Variation

#### Generate Variation Profile
```http
POST /variation/generate
Content-Type: application/json

{
  "niche": "motivation",
  "topic": "Success Habits",
  "min_uniqueness_score": 0.7
}
```

### Upload Scheduling

#### Schedule Upload
```http
POST /upload/schedule
Content-Type: application/json

{
  "video_path": "./output/video.mp4",
  "niche": "motivation",
  "topic": "Success Habits",
  "title": "Why Your Morning Routine Is Failing",
  "metadata": {"tags": ["motivation"]},
  "priority": "high",
  "scheduled_time": "2025-03-27T18:00:00Z"
}
```

#### Get Queue Status
```http
GET /upload/queue/status
```

#### Get Rate Limit Status
```http
GET /upload/rate-limit
```

### Full Pipeline

#### Run Complete Pipeline
```http
POST /pipeline/run
Content-Type: application/json

{
  "niche": "ai_tech",
  "auto_upload": false,
  "target_duration_sec": 90,
  "creativity_factor": 0.7
}
```

---

## Usage Examples

### Example 1: Discover Topics for Motivation Niche

```python
import requests

response = requests.post(
    "http://localhost:8000/api/v2/viral/topics/discover",
    json={
        "niche": "motivation",
        "max_topics": 5,
        "min_virality_score": 70,
    }
)

data = response.json()
print(f"Discovered {data['total_discovered']} topics")
print(f"Average virality: {data['avg_virality_score']:.1f}")

for topic in data['topics'][:3]:
    print(f"  - {topic['topic']} (Score: {topic['virality_score']})")
```

### Example 2: Generate Script for Selected Topic

```python
# Select best topic
best_topic = data['topics'][0]['topic']

# Generate script
script_response = requests.post(
    "http://localhost:8000/api/v2/viral/scripts/generate",
    json={
        "niche": "motivation",
        "topic": best_topic,
        "target_duration_sec": 90,
        "creativity_factor": 0.7,
    }
)

script = script_response.json()['script']
print(f"Title: {script['title']}")
print(f"Hook: {script['hook_text']}")
print(f"Duration: {script['estimated_duration_sec']:.1f}s")
print(f"Retention Score: {script['retention_score']}")
```

### Example 3: Optimize Metadata

```python
metadata_response = requests.post(
    "http://localhost:8000/api/v2/viral/metadata/optimize",
    json={
        "niche": "motivation",
        "topic": best_topic,
        "script_title": script['title'],
        "script_content": script['full_text'],
        "platform": "youtube",
    }
)

metadata = metadata_response.json()['metadata']
print(f"Best Title: {metadata['best_title']}")
print(f"SEO Score: {metadata['seo_score']}")
print(f"CTR Score: {metadata['ctr_score']}")
print(f"Tags: {', '.join(metadata['tags'][:5])}")
```

### Example 4: Using Celery Tasks (Async)

```python
from workers.viral_tasks import (
    discover_viral_topics,
    generate_viral_script,
    optimize_video_metadata,
    run_viral_content_pipeline,
)

# Run complete pipeline asynchronously
result = run_viral_content_pipeline.delay(
    niche="ai_tech",
    auto_upload=False,
    target_duration_sec=90,
    creativity_factor=0.7,
)

# Get result
pipeline_result = result.get()
print(f"Pipeline completed: {pipeline_result['success']}")
```

### Example 5: Full Workflow

```python
# Step 1: Discover topics
topics = discover_viral_topics(
    niche="finance",
    max_topics=3,
    min_virality_score=75,
)

# Step 2: Select best topic
best = topics['topics'][0]
print(f"Selected: {best['topic']} (Virality: {best['virality_score']})")

# Step 3: Generate script
script = generate_viral_script(
    niche="finance",
    topic=best['topic'],
    target_duration_sec=120,
)

# Step 4: Optimize metadata
metadata = optimize_video_metadata(
    niche="finance",
    topic=best['topic'],
    script_title=script['script']['title'],
)

# Step 5: Schedule upload (after video generation)
# upload_job = schedule_video_upload(...)
```

---

## Celery Tasks

### Available Tasks

| Task | Description |
|------|-------------|
| `discover_viral_topics` | Discover viral topics for a niche |
| `score_topic_virality` | Calculate virality score for a topic |
| `generate_viral_script` | Generate viral-optimized script |
| `optimize_video_metadata` | Generate optimized metadata |
| `generate_content_variation` | Generate content variation profile |
| `schedule_video_upload` | Schedule video upload |
| `process_upload_queue` | Process next upload in queue |
| `get_upload_queue_status` | Get queue status |
| `run_viral_content_pipeline` | Run complete pipeline |
| `get_available_niches` | Get all available niches |
| `get_niche_config` | Get niche configuration |

### Task Usage

```python
from workers.viral_tasks import discover_viral_topics

# Sync call
result = discover_viral_topics(
    niche="motivation",
    max_topics=5,
)

# Async call with callback
result = discover_viral_topics.apply_async(
    kwargs={"niche": "motivation", "max_topics": 5},
    link=process_result.s(),
)
```

---

## Configuration

### Environment Variables

Add to `.env`:

```env
# Niche Settings
DEFAULT_NICHE=motivation
TARGET_VIDEO_DURATION=90
CONTENT_LANGUAGE=en
TRENDING_REGION=US

# Upload Limits
DAILY_UPLOAD_LIMIT=5
UPLOAD_COOLDOWN_SEC=300

# Virality Thresholds
MIN_VIRALITY_SCORE=60
DEFAULT_VIRALITY_THRESHOLD=70
```

### Niche Configuration

Niche configurations are defined in `config/niche_config.py`. Each niche has:

- **Discovery settings**: Sources, focus keywords, validation rules
- **Content settings**: Tones, hook strategies, emotional triggers
- **Script settings**: Duration, pacing, voice preferences
- **Upload settings**: Daily limits, optimal times, priority

### Adding a New Niche

```python
# In config/niche_config.py

self._configs[NicheType.YOUR_NICHE] = NicheConfig(
    niche=NicheType.YOUR_NICHE,
    display_name="Your Niche Name",
    description="Description of your niche",
    primary_sources=["youtube", "twitter"],
    focus_keywords=["keyword1", "keyword2"],
    min_sources_to_validate=2,
    virality_threshold=65,
    default_tones=[ContentTone.EDUCATIONAL],
    hook_strategies=[HookStrategy.THIS_IS_WHY],
    emotional_triggers=[EmotionalTrigger.CURIOSITY],
    target_duration_sec=90,
    daily_upload_limit=3,
    # ... more settings
)
```

---

## Best Practices

### 1. Topic Selection

- **Minimum Virality Score**: Use 70+ for best results
- **Emotional Triggers**: Select topics with 2+ emotional triggers
- **Source Validation**: Prefer topics validated across 3+ sources

### 2. Script Generation

- **Hook Framework**: Match hook to niche (e.g., `story_based` for Islamic content)
- **Duration**: Keep scripts under 120s for Shorts, 180s for standard
- **Creativity**: Use 0.6-0.8 for balanced content

### 3. Metadata Optimization

- **Title Length**: 40-60 characters for optimal CTR
- **Description**: 200+ words with keywords in first 2 lines
- **Tags**: 15-25 relevant tags
- **Hashtags**: 3-5 niche-specific + viral tags

### 4. Upload Strategy

- **Timing**: Use niche-specific optimal posting times
- **Rate Limiting**: Respect daily limits to avoid API blocks
- **Priority**: Use `high` for trending topics, `normal` for evergreen

### 5. Content Variation

- **Uniqueness Score**: Maintain 0.7+ uniqueness
- **Tone Diversity**: Rotate through different tones
- **Style Variation**: Mix narrative styles across videos

### 6. Error Handling

```python
try:
    result = generate_viral_script(niche="motivation", topic="Success")
except Exception as e:
    if "rate_limit" in str(e).lower():
        # Wait and retry
        time.sleep(3600)
    elif "quota" in str(e).lower():
        # Daily quota exceeded
        schedule_for_tomorrow()
```

---

## Troubleshooting

### Common Issues

**Issue**: "Unknown niche" error
- **Solution**: Check niche ID against available niches: `GET /api/v2/viral/niches`

**Issue**: Low virality scores
- **Solution**: Lower `min_virality_score` or try different niche

**Issue**: Upload queue stuck
- **Solution**: Check rate limit status: `GET /api/v2/viral/upload/rate-limit`

**Issue**: Script generation fails
- **Solution**: Verify OpenAI API key is valid and has quota

---

## Performance Benchmarks

| Metric | Target | Excellent |
|--------|--------|-----------|
| Virality Score | 70+ | 85+ |
| Retention Score | 75+ | 90+ |
| CTR Score | 70+ | 85+ |
| SEO Score | 70+ | 85+ |
| Uniqueness Score | 0.7+ | 0.9+ |

---

## Support

For issues or questions:
1. Check this documentation
2. Review API response error messages
3. Check Celery task logs
4. Verify environment configuration

---

**Version**: 2.0.0  
**Last Updated**: March 2025
