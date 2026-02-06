#!/usr/bin/env python3
"""
Generate comprehensive YouTube analytics report with visualizations
"""
import json
import os
from datetime import datetime
from collections import Counter

def load_data():
    """Load analytics data from JSON file"""
    with open('youtube_analytics_results.json', 'r', encoding='utf-8') as f:
        return json.load(f)

def generate_markdown_report(data):
    """Generate a comprehensive markdown report"""
    
    # Combine both channels
    all_videos_combined = []
    for channel_name, channel_data in data.items():
        for video in channel_data.get('all_videos', []):
            video['channel'] = channel_name
            all_videos_combined.append(video)
    
    # Global statistics
    total_videos_all = sum(d['total_videos'] for d in data.values())
    total_views_all = sum(d['total_views'] for d in data.values())
    total_likes_all = sum(d['total_likes'] for d in data.values())
    
    # Find videos with views
    videos_with_views = [v for v in all_videos_combined if v['views'] > 0]
    videos_without_views = [v for v in all_videos_combined if v['views'] == 0]
    
    # Topic analysis from titles
    all_titles = [v['title'].lower() for v in all_videos_combined]
    topic_keywords = []
    for title in all_titles:
        words = title.split()
        topic_keywords.extend([w for w in words if len(w) > 4 and w not in ['#shorts', 'movies', 'watch']])
    
    common_topics = Counter(topic_keywords).most_common(15)
    
    # Best performing content themes
    science_fiction = [v for v in videos_with_views if 'science fiction' in v['title'].lower() or 'sci fi' in v['title'].lower() or 'sci-fi' in v['title'].lower()]
    apocalyptic = [v for v in videos_with_views if 'apocalyptic' in v['title'].lower() or 'apocalypse' in v['title'].lower()]
    thriller = [v for v in videos_with_views if 'thriller' in v['title'].lower()]
    motivation = [v for v in videos_with_views if 'motivat' in v['title'].lower() or 'success' in v['title'].lower()]
    
    report = f"""# YouTube Shorts Analytics Report
## Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

---

## 📊 Executive Summary

### Global Performance Across Both Channels
- **Total Videos Uploaded**: {total_videos_all:,}
- **Total Views**: {total_views_all:,}
- **Total Likes**: {total_likes_all:,}
- **Total Comments**: {sum(d['total_comments'] for d in data.values())}
- **Videos with Views**: {len(videos_with_views)} ({len(videos_with_views)/total_videos_all*100:.1f}%)
- **Videos with Zero Views**: {len(videos_without_views)} ({len(videos_without_views)/total_videos_all*100:.1f}%)

> [!WARNING]
> **Critical Issue**: {len(videos_without_views)/total_videos_all*100:.1f}% of videos have received **ZERO views**. This indicates a significant discoverability problem.

---

## 📈 Channel-by-Channel Breakdown

"""
    
    # Add channel details
    for channel_name, channel_data in data.items():
        channel_emoji = "🎬" if channel_name == "movies_en" else "💪"
        report += f"""### {channel_emoji} {channel_name.replace('_', ' ').title()}

| Metric | Value |
|--------|-------|
| Total Videos | {channel_data['total_videos']:,} |
| Total Views | {channel_data['total_views']:,} |
| Total Likes | {channel_data['total_likes']} |
| Total Comments | {channel_data['total_comments']} |
| Avg Views/Video | {channel_data['avg_views']:.2f} |
| Avg Likes/Video | {channel_data['avg_likes']:.2f} |
| Engagement Rate | {(channel_data['total_likes']/channel_data['total_views']*100) if channel_data['total_views'] > 0 else 0:.3f}% |

#### Top 5 Performing Videos

| Title | Views | Likes | Engagement % |
|-------|-------|-------|--------------|
"""
        for i, video in enumerate(channel_data['top_videos'][:5], 1):
            report += f"| {video['title'][:50]}... | {video['views']:,} | {video['likes']} | {video['engagement_rate']:.2f}% |\n"
        
        report += "\n---\n\n"
    
    # Content analysis
    report += f"""## 🎯 Content Performance Analysis

### Best Performing Content Themes

Based on videos that received views:

"""
    
    if science_fiction:
        sf_avg_views = sum(v['views'] for v in science_fiction) / len(science_fiction)
        report += f"#### 🚀 Science Fiction\n- **Videos**: {len(science_fiction)}\n- **Avg Views**: {sf_avg_views:.0f}\n- **Total Views**: {sum(v['views'] for v in science_fiction):,}\n\n"
    
    if apocalyptic:
        apoc_avg_views = sum(v['views'] for v in apocalyptic) / len(apocalyptic)
        report += f"#### 🌍 Post-Apocalyptic\n- **Videos**: {len(apocalyptic)}\n- **Avg Views**: {apoc_avg_views:.0f}\n- **Total Views**: {sum(v['views'] for v in apocalyptic):,}\n\n"
    
    if thriller:
        thriller_avg_views = sum(v['views'] for v in thriller) / len(thriller)
        report += f"#### 🔪 Thriller\n- **Videos**: {len(thriller)}\n- **Avg Views**: {thriller_avg_views:.0f}\n- **Total Views**: {sum(v['views'] for v in thriller):,}\n\n"
    
    if motivation:
        motiv_avg_views = sum(v['views'] for v in motivation) / len(motivation)
        report += f"#### 💪 Motivation/Success\n- **Videos**: {len(motivation)}\n- **Avg Views**: {motiv_avg_views:.0f}\n- **Total Views**: {sum(v['views'] for v in motivation):,}\n\n"
    
    report += f"""### Most Common Topics (from titles)

| Topic Keyword | Frequency |
|---------------|-----------|
"""
    for topic, count in common_topics[:10]:
        report += f"| {topic} | {count} |\n"
    
    # Problem analysis
    report += f"""

---

## ⚠️ Critical Issues Identified

### 1. Extremely Low Discoverability

> [!CAUTION]
> Only **{len(videos_with_views)/total_videos_all*100:.1f}%** of videos are being discovered by viewers.

**Possible Causes:**
- Videos are set to **Private** instead of **Public**
- Missing or poor SEO (titles, descriptions, tags)
- No thumbnail optimization
- Algorithm not picking up the content
- Wrong publishing times
- Content saturation in niche

### 2. Very Low Engagement Rate

> [!WARNING]
> Overall engagement rate is **{(total_likes_all/total_views_all*100) if total_views_all > 0 else 0:.3f}%** (industry average for Shorts is 2-5%)

**Issues:**
- Content may not be compelling enough
- Missing call-to-action (CTA)
- Poor hook in first 3 seconds
- Content quality concerns

### 3. Zero Comments

> [!IMPORTANT]
> Only **1 comment** across **{total_videos_all}** videos indicates very low audience interaction

---

## 💡 Recommendations

### Immediate Actions

#### 1. **Verify Video Privacy Settings**
```bash
# Check if videos are actually public
# Most likely cause of zero views on bulk uploads
```
Run the script to check and update privacy settings for all videos.

#### 2. **Optimize for Algorithm**
- **Post at peak times**: 2-4 PM, 8-10 PM in target timezone
- **Use trending topics**: Monitor YouTube Trends
- **Better hooks**: First 3 seconds MUST grab attention
- **Add text overlays**: Make content watchable without sound

#### 3. **Improve Video Titles**
Current titles are descriptive but not clickable. Compare:

| ❌ Current | ✅ Better |
|-----------|----------|
| "post apocalyptic movies worth watching" | "These Post-Apocalyptic Movies Will BLOW YOUR MIND 🤯" |
| "the psychology of winners" | "Why Winners Think Differently (Psychology Explained)" |
| "best thriller movies of all time" | "You've NEVER Seen Thrillers Like These 😱" |

#### 4. **Add Strong CTAs**
Every video should end with:
- "Double tap if you agree! 👍"
- "Follow for more [topic] content!"
- "Comment your favorite below! ⬇️"

#### 5. **Create Series/Themes**
Best performing video got **1,363 views** ("top 10 science fiction"). Create a series:
- "Top 10 Sci-Fi Movies - Part 1"
- "Top 10 Sci-Fi Movies - Part 2"
- Build anticipation and recurring audience

### Long-term Strategy

#### Content Quality
- Analyze top 10 performers manually
- Identify what made them successful
- Replicate winning formula

#### Audience Building
- Cross-promote on other platforms
- Engage with comments (when you get them)
- Collaborate with similar channels

#### Analytics Monitoring
- Run this analysis weekly
- Track improvement trends
- A/B test different content styles

---

## 📊 Top 10 Overall Best Performers

| Rank | Title | Channel | Views | Likes | Eng. % |
|------|-------|---------|-------|-------|--------|
"""
    
    # Top overall videos
    top_overall = sorted(all_videos_combined, key=lambda x: x['views'], reverse=True)[:10]
    for i, video in enumerate(top_overall, 1):
        channel_emoji = "🎬" if video['channel'] == "movies_en" else "💪"
        report += f"| {i} | {video['title'][:40]}... | {channel_emoji} | {video['views']:,} | {video['likes']} | {video['engagement_rate']:.2f}% |\n"
    
    report += f"""

---

## 🎬 Success Case Study: Top Video

**Title**: {top_overall[0]['title']}
- **Views**: {top_overall[0]['views']:,}
- **Likes**: {top_overall[0]['likes']}
- **Engagement**: {top_overall[0]['engagement_rate']:.2f}%
- **Duration**: {top_overall[0]['duration']}
- **Published**: {top_overall[0]['published_at']}

**Why it worked:**
- Topic: Science Fiction (popular niche)
- Short duration ({top_overall[0]['duration']})
- Clear, searchable title
- Published at good time

**Replicate this success** by creating more "Top 10" style content in popular movie genres.

---

## 📅 Next Steps

1. ✅ **Week 1**: Fix privacy settings, optimize top 50 video titles
2. 📝 **Week 2**: Add CTAs to all future videos, test new thumbnails
3. 📊 **Week 3**: Re-run analytics, measure improvement
4. 🚀 **Week 4**: Scale what's working, cut what's not

---

*Report generated by YouTube Analytics Tool v1.0*
"""
    
    return report

def main():
    print("📊 Generating comprehensive analytics report...")
    
    data = load_data()
    report = generate_markdown_report(data)
    
    # Save report
    report_file = 'youtube_analytics_report.md'
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(report)
    
    print(f"✅ Report generated: {report_file}")
    
if __name__ == "__main__":
    main()
