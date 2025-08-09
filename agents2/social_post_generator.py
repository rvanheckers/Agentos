#!/usr/bin/env python3
"""
Social Post Generator Agent - Atomic Agent
==========================================

Generates social media posts for different platforms.
Single responsibility: Create engaging social media content.
"""

import json
import sys
import time
from typing import Dict, List, Any

class SocialPostGenerator:
    """
    Atomic agent for generating social media posts.
    
    Creates platform-specific posts with optimal formatting,
    hashtags, and engagement strategies.
    """
    
    def __init__(self):
        self.version = "1.0.0"
    
    def generate_posts(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate social media posts for multiple platforms.
        
        Args:
            input_data: {
                "video_path": str,           # optional, for video-based posts
                "topic": str,                # main topic/subject
                "script": str,               # optional, video script
                "moments": List[dict],       # optional, key moments
                "platforms": List[str],      # ["tiktok", "instagram", "youtube", "twitter", "linkedin"]
                "tone": str,                 # "casual", "professional", "energetic", "educational"
                "target_audience": str,      # optional, target audience description
                "include_hashtags": bool,    # optional, include hashtags
                "include_mentions": bool,    # optional, include @mentions
                "post_type": str            # "promotion", "educational", "entertainment", "announcement"
            }
            
        Returns:
            {
                "success": bool,
                "posts": {
                    "tiktok": {
                        "text": str,
                        "hashtags": List[str],
                        "mentions": List[str],
                        "character_count": int,
                        "engagement_tips": List[str]
                    },
                    "instagram": {...},
                    "youtube": {...},
                    "twitter": {...},
                    "linkedin": {...}
                },
                "cross_platform_strategy": {
                    "posting_schedule": str,
                    "content_variations": List[str],
                    "engagement_strategy": str
                },
                "processing_time": float,
                "agent_version": str
            }
        """
        
        start_time = time.time()
        
        try:
            # Validate inputs
            if not input_data.get("topic"):
                return self._error("topic is required")
            
            # Get parameters
            input_data.get("video_path", "")
            topic = input_data["topic"]
            script = input_data.get("script", "")
            moments = input_data.get("moments", [])
            platforms = input_data.get("platforms", ["tiktok", "instagram", "youtube"])
            tone = input_data.get("tone", "casual")
            target_audience = input_data.get("target_audience", "general")
            include_hashtags = input_data.get("include_hashtags", True)
            include_mentions = input_data.get("include_mentions", False)
            post_type = input_data.get("post_type", "promotional")
            
            # Generate posts for each platform
            posts = {}
            for platform in platforms:
                posts[platform] = self._generate_platform_post(
                    platform, topic, script, moments, tone, target_audience,
                    include_hashtags, include_mentions, post_type
                )
            
            # Generate cross-platform strategy
            cross_platform_strategy = self._generate_cross_platform_strategy(
                platforms, topic, tone, post_type
            )
            
            processing_time = time.time() - start_time
            
            return {
                "success": True,
                "posts": posts,
                "cross_platform_strategy": cross_platform_strategy,
                "processing_time": processing_time,
                "agent_version": self.version
            }
            
        except Exception as e:
            return self._error(f"Post generation failed: {str(e)}")
    
    def _generate_platform_post(self, platform: str, topic: str, script: str,
                               moments: List[dict], tone: str, target_audience: str,
                               include_hashtags: bool, include_mentions: bool,
                               post_type: str) -> Dict[str, Any]:
        """Generate post for specific platform"""
        
        platform_configs = {
            "tiktok": {
                "max_chars": 2200,
                "style": "casual and energetic",
                "hashtag_limit": 10,
                "hook_required": True
            },
            "instagram": {
                "max_chars": 2200,
                "style": "visual and story-driven",
                "hashtag_limit": 30,
                "hook_required": True
            },
            "youtube": {
                "max_chars": 5000,
                "style": "descriptive and informative",
                "hashtag_limit": 15,
                "hook_required": False
            },
            "twitter": {
                "max_chars": 280,
                "style": "concise and engaging",
                "hashtag_limit": 5,
                "hook_required": True
            },
            "linkedin": {
                "max_chars": 3000,
                "style": "professional and insightful",
                "hashtag_limit": 10,
                "hook_required": False
            }
        }
        
        config = platform_configs.get(platform, platform_configs["instagram"])
        
        # Generate main text
        text = self._generate_post_text(
            platform, topic, script, moments, tone, config, post_type
        )
        
        # Generate hashtags
        hashtags = []
        if include_hashtags:
            hashtags = self._generate_hashtags(
                platform, topic, config["hashtag_limit"]
            )
        
        # Generate mentions
        mentions = []
        if include_mentions:
            mentions = self._generate_mentions(platform, topic)
        
        # Calculate engagement tips
        engagement_tips = self._generate_engagement_tips(platform, post_type)
        
        return {
            "text": text,
            "hashtags": hashtags,
            "mentions": mentions,
            "character_count": len(text),
            "engagement_tips": engagement_tips,
            "platform_config": config
        }
    
    def _generate_post_text(self, platform: str, topic: str, script: str,
                           moments: List[dict], tone: str, config: Dict[str, Any],
                           post_type: str) -> str:
        """Generate main post text"""
        
        # Platform-specific hooks
        hooks = {
            "tiktok": [
                f"POV: You discover {topic} 🤯",
                f"This {topic} hack is everything!",
                f"Wait until you see this {topic} trick!",
                f"Nobody talks about {topic}, but..."
            ],
            "instagram": [
                f"Let's talk about {topic} ✨",
                f"Here's what I learned about {topic}",
                f"The {topic} game-changer you need",
                f"Real talk about {topic}"
            ],
            "youtube": [
                f"New video about {topic} is live!",
                f"Diving deep into {topic} today",
                f"Everything you need to know about {topic}",
                f"My thoughts on {topic}"
            ],
            "twitter": [
                f"Quick thread on {topic}:",
                f"Hot take: {topic}",
                f"Just learned about {topic}",
                f"Thoughts on {topic}?"
            ],
            "linkedin": [
                f"Insights on {topic} for professionals",
                f"Industry perspective on {topic}",
                f"How {topic} impacts our industry",
                f"Professional development: {topic}"
            ]
        }
        
        # Build post content
        post_parts = []
        
        # Add hook if required
        if config.get("hook_required", False):
            hook_options = hooks.get(platform, hooks["instagram"])
            post_parts.append(hook_options[0])
        
        # Add main content based on script or moments
        if script:
            # Use script summary
            script_summary = self._summarize_script(script, config["max_chars"] // 2)
            post_parts.append(script_summary)
        elif moments:
            # Use moments
            for moment in moments[:2]:  # Use first 2 moments
                description = moment.get("description", f"Key insight about {topic}")
                post_parts.append(f"✨ {description}")
        else:
            # Generate generic content
            if post_type == "educational":
                post_parts.append(f"Here's what you need to know about {topic}:")
                post_parts.append(f"The key insight that changed my perspective on {topic}.")
            elif post_type == "entertainment":
                post_parts.append(f"Can we talk about {topic} for a second?")
                post_parts.append(f"This {topic} situation is wild!")
            else:  # promotional
                post_parts.append(f"Just dropped a new video about {topic}!")
                post_parts.append(f"Everything you need to know about {topic} in one place.")
        
        # Add platform-specific CTA
        cta = self._generate_platform_cta(platform, post_type)
        post_parts.append(cta)
        
        # Join parts and ensure character limit
        full_text = "\\n\\n".join(post_parts)
        
        # Truncate if needed
        if len(full_text) > config["max_chars"]:
            full_text = full_text[:config["max_chars"]-3] + "..."
        
        return full_text
    
    def _generate_hashtags(self, platform: str, topic: str, limit: int) -> List[str]:
        """Generate platform-specific hashtags"""
        
        # Platform-specific hashtags
        platform_tags = {
            "tiktok": ["#fyp", "#viral", "#trending", "#foryou", "#tiktok"],
            "instagram": ["#instagram", "#reels", "#content", "#creator", "#viral"],
            "youtube": ["#youtube", "#video", "#content", "#tutorial", "#educational"],
            "twitter": ["#twitter", "#thread", "#trending", "#discussion"],
            "linkedin": ["#linkedin", "#professional", "#industry", "#career", "#business"]
        }
        
        # Topic-based hashtags
        topic_words = topic.lower().replace(" ", "").split()
        topic_tags = [f"#{word}" for word in topic_words if len(word) > 2]
        
        # Generic content hashtags
        content_tags = ["#tips", "#advice", "#learning", "#knowledge", "#insights"]
        
        # Combine and limit
        all_tags = platform_tags.get(platform, []) + topic_tags + content_tags
        return list(set(all_tags))[:limit]
    
    def _generate_mentions(self, platform: str, topic: str) -> List[str]:
        """Generate relevant mentions"""
        
        # This would typically include relevant accounts, but for now return empty
        # In a real implementation, you'd have a database of relevant accounts
        return []
    
    def _generate_engagement_tips(self, platform: str, post_type: str) -> List[str]:
        """Generate engagement tips for the platform"""
        
        tips = {
            "tiktok": [
                "Post during peak hours (6-10 PM)",
                "Use trending sounds and effects",
                "Engage with comments quickly",
                "Post consistently (1-3 times daily)",
                "Use relevant trending hashtags"
            ],
            "instagram": [
                "Post during lunch hours and evenings",
                "Use Instagram Stories for behind-the-scenes",
                "Engage with your audience in comments",
                "Use location tags when relevant",
                "Post consistently (1-2 times daily)"
            ],
            "youtube": [
                "Include timestamps in description",
                "Respond to comments within first hour",
                "Use end screens and cards",
                "Create compelling thumbnails",
                "Post on consistent schedule"
            ],
            "twitter": [
                "Tweet during business hours",
                "Use Twitter threads for longer content",
                "Engage with replies quickly",
                "Retweet relevant content",
                "Use Twitter Spaces for live engagement"
            ],
            "linkedin": [
                "Post during business hours (9 AM - 5 PM)",
                "Share professional insights",
                "Engage with industry peers",
                "Use LinkedIn Stories for updates",
                "Post 2-3 times per week"
            ]
        }
        
        return tips.get(platform, tips["instagram"])[:3]
    
    def _generate_platform_cta(self, platform: str, post_type: str) -> str:
        """Generate platform-specific call-to-action"""
        
        ctas = {
            "tiktok": [
                "Follow for more tips! 🚀",
                "Comment your thoughts below! 💭",
                "Share this with someone who needs it! 📤",
                "Double tap if you found this helpful! ❤️"
            ],
            "instagram": [
                "Save this for later! 📌",
                "Tag someone who needs this! 🏷️",
                "Share your thoughts in the comments! 💬",
                "Follow for more content like this! ✨"
            ],
            "youtube": [
                "Watch the full video for more details! 🎥",
                "Subscribe for more content! 🔔",
                "Let me know your thoughts in the comments! 💭",
                "Share this with someone who'd find it helpful! 📤"
            ],
            "twitter": [
                "What do you think? Reply below! 💭",
                "Retweet if you found this useful! 🔄",
                "Follow for more insights! 🚀",
                "Join the conversation! 💬"
            ],
            "linkedin": [
                "What's your experience with this? 💼",
                "Share your professional insights! 🧠",
                "Connect with me for more content! 🤝",
                "Follow for industry updates! 📈"
            ]
        }
        
        platform_ctas = ctas.get(platform, ctas["instagram"])
        return platform_ctas[0]  # Return first option
    
    def _summarize_script(self, script: str, max_length: int) -> str:
        """Summarize script for social media"""
        
        if len(script) <= max_length:
            return script
        
        # Simple summarization - take first part and add ellipsis
        summary = script[:max_length-3] + "..."
        return summary
    
    def _generate_cross_platform_strategy(self, platforms: List[str], topic: str,
                                         tone: str, post_type: str) -> Dict[str, Any]:
        """Generate cross-platform posting strategy"""
        
        return {
            "posting_schedule": "Stagger posts 1-2 hours apart to maximize reach",
            "content_variations": [
                "Customize hashtags for each platform",
                "Adjust tone based on platform audience",
                "Use platform-specific features (Stories, Reels, etc.)",
                "Tailor CTAs to platform norms"
            ],
            "engagement_strategy": "Monitor all platforms for first 2 hours after posting"
        }
    
    def _error(self, message: str) -> Dict[str, Any]:
        """Return standardized error response"""
        return {
            "success": False,
            "error": message,
            "error_code": "POST_GENERATION_ERROR",
            "agent_version": self.version
        }

def main():
    """Main entry point for command line usage"""
    if len(sys.argv) != 2:
        print(json.dumps({
            "success": False,
            "error": "Usage: python social_post_generator.py '<json_input>'",
            "error_code": "INVALID_ARGUMENTS"
        }))
        sys.exit(1)
    
    try:
        input_data = json.loads(sys.argv[1])
        generator = SocialPostGenerator()
        result = generator.generate_posts(input_data)
        print(json.dumps(result, indent=2))
        
    except json.JSONDecodeError:
        print(json.dumps({
            "success": False,
            "error": "Invalid JSON input",
            "error_code": "JSON_DECODE_ERROR"
        }))
        sys.exit(1)
    except Exception as e:
        print(json.dumps({
            "success": False,
            "error": f"Unexpected error: {str(e)}",
            "error_code": "UNEXPECTED_ERROR"
        }))
        sys.exit(1)

if __name__ == "__main__":
    main()