#!/usr/bin/env python3
"""
YouTube Video Statistics Analyzer

Fetches and analyzes statistics for all uploaded videos across channels.
"""
import os
import sys
import json
from datetime import datetime
from typing import List, Dict, Any
from collections import defaultdict

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.youtube_uploader import YouTubeUploader
from loguru import logger


class YouTubeAnalytics:
    def __init__(self, channel_name: str, credentials_dir: str = "./credentials"):
        self.channel_name = channel_name
        self.uploader = YouTubeUploader(
            credentials_dir=credentials_dir,
            channel_name=channel_name
        )
        self.videos = []
        
    def authenticate(self) -> bool:
        """Authenticate with YouTube API"""
        return self.uploader.authenticate(interactive=False)
    
    def get_channel_id(self) -> str:
        """Get the channel ID"""
        channel_info = self.uploader.get_channel_info()
        if channel_info:
            return channel_info.get('id', '')
        return ''
    
    def fetch_all_videos(self, max_results: int = 500) -> List[Dict[str, Any]]:
        """
        Fetch all videos from the channel
        
        Args:
            max_results: Maximum number of videos to fetch
            
        Returns:
            List of video data dictionaries
        """
        logger.info(f"Fetching videos for channel: {self.channel_name}")
        
        try:
            # Get channel's uploads playlist ID
            channel_info = self.uploader.get_channel_info()
            if not channel_info:
                logger.error("Could not get channel info")
                return []
            
            uploads_playlist_id = channel_info.get('contentDetails', {}).get('relatedPlaylists', {}).get('uploads', '')
            
            if not uploads_playlist_id:
                logger.error("Could not find uploads playlist")
                return []
            
            logger.info(f"Uploads playlist ID: {uploads_playlist_id}")
            
            # Fetch all videos from the uploads playlist
            videos = []
            next_page_token = None
            
            while len(videos) < max_results:
                request = self.uploader.youtube.playlistItems().list(
                    part="snippet,contentDetails",
                    playlistId=uploads_playlist_id,
                    maxResults=min(50, max_results - len(videos)),
                    pageToken=next_page_token
                )
                
                response = request.execute()
                
                for item in response.get('items', []):
                    video_id = item['contentDetails']['videoId']
                    videos.append({
                        'video_id': video_id,
                        'title': item['snippet']['title'],
                        'published_at': item['snippet']['publishedAt'],
                        'description': item['snippet']['description']
                    })
                
                next_page_token = response.get('nextPageToken')
                
                if not next_page_token:
                    break
            
            logger.success(f"Fetched {len(videos)} videos")
            self.videos = videos
            return videos
            
        except Exception as e:
            logger.error(f"Error fetching videos: {e}")
            return []
    
    def fetch_video_statistics(self, video_ids: List[str]) -> List[Dict[str, Any]]:
        """
        Fetch statistics for specific videos
        
        Args:
            video_ids: List of video IDs
            
        Returns:
            List of video statistics
        """
        if not video_ids:
            return []
        
        logger.info(f"Fetching statistics for {len(video_ids)} videos")
        
        try:
            all_stats = []
            
            # API allows max 50 videos per request
            for i in range(0, len(video_ids), 50):
                batch = video_ids[i:i+50]
                
                request = self.uploader.youtube.videos().list(
                    part="statistics,contentDetails,snippet",
                    id=','.join(batch)
                )
                
                response = request.execute()
                
                for item in response.get('items', []):
                    stats = item.get('statistics', {})
                    snippet = item.get('snippet', {})
                    content_details = item.get('contentDetails', {})
                    
                    all_stats.append({
                        'video_id': item['id'],
                        'title': snippet.get('title', ''),
                        'published_at': snippet.get('publishedAt', ''),
                        'duration': content_details.get('duration', ''),
                        'views': int(stats.get('viewCount', 0)),
                        'likes': int(stats.get('likeCount', 0)),
                        'comments': int(stats.get('commentCount', 0)),
                        'favorites': int(stats.get('favoriteCount', 0))
                    })
            
            logger.success(f"Fetched statistics for {len(all_stats)} videos")
            return all_stats
            
        except Exception as e:
            logger.error(f"Error fetching statistics: {e}")
            return []
    
    def analyze(self) -> Dict[str, Any]:
        """
        Analyze fetched videos and return statistics
        
        Returns:
            Dictionary with analysis results
        """
        if not self.videos:
            logger.warning("No videos to analyze")
            return {}
        
        # Get detailed statistics
        video_ids = [v['video_id'] for v in self.videos]
        stats = self.fetch_video_statistics(video_ids)
        
        if not stats:
            logger.error("Could not fetch video statistics")
            return {}
        
        # Calculate aggregate statistics
        total_videos = len(stats)
        total_views = sum(v['views'] for v in stats)
        total_likes = sum(v['likes'] for v in stats)
        total_comments = sum(v['comments'] for v in stats)
        
        avg_views = total_views / total_videos if total_videos > 0 else 0
        avg_likes = total_likes / total_videos if total_videos > 0 else 0
        avg_comments = total_comments / total_videos if total_videos > 0 else 0
        
        # Sort videos by views
        top_videos = sorted(stats, key=lambda x: x['views'], reverse=True)[:10]
        bottom_videos = sorted(stats, key=lambda x: x['views'])[:10]
        
        # Calculate engagement rate (likes / views)
        for video in stats:
            video['engagement_rate'] = (video['likes'] / video['views'] * 100) if video['views'] > 0 else 0
        
        top_engagement = sorted(stats, key=lambda x: x['engagement_rate'], reverse=True)[:10]
        
        analysis = {
            'channel_name': self.channel_name,
            'total_videos': total_videos,
            'total_views': total_views,
            'total_likes': total_likes,
            'total_comments': total_comments,
            'avg_views': round(avg_views, 2),
            'avg_likes': round(avg_likes, 2),
            'avg_comments': round(avg_comments, 2),
            'top_videos': top_videos,
            'bottom_videos': bottom_videos,
            'top_engagement': top_engagement,
            'all_videos': stats
        }
        
        return analysis


def main():
    """Main function to analyze both channels"""
    channels = ['movies_en', 'motivation_en']
    all_analyses = {}
    
    for channel in channels:
        logger.info(f"\n{'='*60}")
        logger.info(f"Analyzing channel: {channel}")
        logger.info(f"{'='*60}\n")
        
        analyzer = YouTubeAnalytics(channel)
        
        # Authenticate
        if not analyzer.authenticate():
            logger.error(f"Authentication failed for {channel}")
            continue
        
        # Fetch videos
        videos = analyzer.fetch_all_videos(max_results=500)
        
        if not videos:
            logger.warning(f"No videos found for {channel}")
            continue
        
        # Analyze
        analysis = analyzer.analyze()
        all_analyses[channel] = analysis
        
        # Print summary
        print(f"\n📊 Summary for {channel}:")
        print(f"  Total Videos: {analysis['total_videos']}")
        print(f"  Total Views: {analysis['total_views']:,}")
        print(f"  Total Likes: {analysis['total_likes']:,}")
        print(f"  Total Comments: {analysis['total_comments']:,}")
        print(f"  Avg Views per Video: {analysis['avg_views']:,.2f}")
        print(f"  Avg Likes per Video: {analysis['avg_likes']:,.2f}")
        print(f"  Avg Comments per Video: {analysis['avg_comments']:,.2f}")
    
    # Save results to JSON
    output_file = 'youtube_analytics_results.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(all_analyses, f, indent=2, ensure_ascii=False)
    
    logger.success(f"\n✅ Analysis complete! Results saved to: {output_file}")
    
    return all_analyses


if __name__ == "__main__":
    main()
