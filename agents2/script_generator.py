#!/usr/bin/env python3
"""
Script Generator Agent - Atomic Agent
====================================

Generates scripts for video content using AI.
Single responsibility: Create engaging scripts for various formats.
"""

import json
import sys
import time
from typing import Dict, List, Any

# MCP Integration
try:
    from mcp.adapter import mcp_compatible
    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False

class ScriptGenerator:
    """
    Atomic agent for generating video scripts.
    
    Creates engaging scripts for different video formats
    and social media platforms.
    """
    
    def __init__(self):
        self.version = "1.0.0"
    
    def generate_script(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate script for video content.
        
        Args:
            input_data: {
                "topic": str,                # main topic/subject
                "transcript": str,           # optional, original transcript
                "moments": List[dict],       # optional, key moments
                "format": str,               # "tiktok", "youtube", "instagram", "generic"
                "duration": int,             # target duration in seconds
                "tone": str,                 # "casual", "professional", "energetic", "educational"
                "target_audience": str,      # optional, target audience description
                "include_hooks": bool,       # optional, include attention-grabbing hooks
                "include_cta": bool          # optional, include call-to-action
            }
            
        Returns:
            {
                "success": bool,
                "script": {
                    "full_script": str,
                    "sections": List[{
                        "type": str,         # "hook", "intro", "body", "conclusion", "cta"
                        "content": str,
                        "duration": int,     # estimated duration in seconds
                        "notes": str         # optional, delivery notes
                    }],
                    "word_count": int,
                    "estimated_duration": int,
                    "keywords": List[str],
                    "hashtags": List[str]    # for social media
                },
                "format_info": {
                    "platform": str,
                    "optimal_length": int,
                    "style_notes": str
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
            topic = input_data["topic"]
            transcript = input_data.get("transcript", "")
            moments = input_data.get("moments", [])
            format_type = input_data.get("format", "generic")
            duration = input_data.get("duration", 60)
            tone = input_data.get("tone", "casual")
            target_audience = input_data.get("target_audience", "general")
            include_hooks = input_data.get("include_hooks", True)
            include_cta = input_data.get("include_cta", True)
            
            # Generate script based on format
            script = self._generate_script_content(
                topic, transcript, moments, format_type, duration,
                tone, target_audience, include_hooks, include_cta
            )
            
            # Get format information
            format_info = self._get_format_info(format_type, duration)
            
            processing_time = time.time() - start_time
            
            return {
                "success": True,
                "script": script,
                "format_info": format_info,
                "processing_time": processing_time,
                "agent_version": self.version
            }
            
        except Exception as e:
            return self._error(f"Script generation failed: {str(e)}")
    
    def _generate_script_content(self, topic: str, transcript: str, moments: List[dict],
                                format_type: str, duration: int, tone: str,
                                target_audience: str, include_hooks: bool,
                                include_cta: bool) -> Dict[str, Any]:
        """Generate the actual script content"""
        
        sections = []
        full_script_parts = []
        
        # Hook (if requested)
        if include_hooks and duration > 10:
            hook = self._generate_hook(topic, format_type, tone)
            sections.append({
                "type": "hook",
                "content": hook,
                "duration": 3,
                "notes": "Deliver with high energy to grab attention"
            })
            full_script_parts.append(hook)
        
        # Introduction
        intro = self._generate_introduction(topic, format_type, tone, target_audience)
        sections.append({
            "type": "intro",
            "content": intro,
            "duration": 5,
            "notes": "Set the context and establish credibility"
        })
        full_script_parts.append(intro)
        
        # Body content
        body_duration = duration - (3 if include_hooks else 0) - 5 - (5 if include_cta else 0)
        body_content = self._generate_body_content(
            topic, transcript, moments, format_type, tone, body_duration
        )
        
        for i, body_part in enumerate(body_content):
            sections.append({
                "type": "body",
                "content": body_part,
                "duration": body_duration // len(body_content),
                "notes": f"Main point {i+1}"
            })
            full_script_parts.append(body_part)
        
        # Call to action (if requested)
        if include_cta and duration > 15:
            cta = self._generate_cta(topic, format_type, tone)
            sections.append({
                "type": "cta",
                "content": cta,
                "duration": 5,
                "notes": "Encourage engagement and action"
            })
            full_script_parts.append(cta)
        
        # Combine all parts
        full_script = " ".join(full_script_parts)
        
        # Generate keywords and hashtags
        keywords = self._extract_keywords(topic, full_script)
        hashtags = self._generate_hashtags(topic, format_type, keywords)
        
        return {
            "full_script": full_script,
            "sections": sections,
            "word_count": len(full_script.split()),
            "estimated_duration": sum(section["duration"] for section in sections),
            "keywords": keywords,
            "hashtags": hashtags
        }
    
    def _generate_hook(self, topic: str, format_type: str, tone: str) -> str:
        """Generate attention-grabbing hook"""
        
        hooks = {
            "tiktok": [
                f"Wait, did you know that {topic}?",
                f"This {topic} hack will blow your mind!",
                f"POV: You discover {topic}",
                f"Nobody talks about {topic}, but..."
            ],
            "youtube": [
                f"Today we're diving deep into {topic}",
                f"Have you ever wondered about {topic}?",
                f"The truth about {topic} might surprise you",
                f"Let's explore {topic} together"
            ],
            "instagram": [
                f"Quick story about {topic}",
                f"Here's what I learned about {topic}",
                f"The {topic} game-changer you need to know",
                f"Real talk about {topic}"
            ]
        }
        
        hook_options = hooks.get(format_type, hooks["youtube"])
        return hook_options[0]  # Return first option for simplicity
    
    def _generate_introduction(self, topic: str, format_type: str, tone: str, target_audience: str) -> str:
        """Generate introduction section"""
        
        if tone == "professional":
            return f"Welcome to our discussion on {topic}. For {target_audience}, understanding this topic is crucial for success."
        elif tone == "energetic":
            return f"Hey everyone! Today we're talking about {topic} and I'm SO excited to share this with you!"
        elif tone == "educational":
            return f"In this video, we'll explore {topic} and learn how it impacts {target_audience}."
        else:  # casual
            return f"Hey guys! So today I want to talk about {topic} because I think it's something we all need to know about."
    
    def _generate_body_content(self, topic: str, transcript: str, moments: List[dict],
                              format_type: str, tone: str, duration: int) -> List[str]:
        """Generate main body content"""
        
        # If we have transcript moments, use them
        if moments:
            content = []
            for moment in moments:
                description = moment.get("description", f"Key point about {topic}")
                content.append(f"Here's something important: {description}")
            return content
        
        # Generate generic content based on topic
        if duration > 30:
            return [
                f"First, let's understand what {topic} really means.",
                f"The key thing about {topic} is how it affects our daily lives.",
                f"Most people don't realize that {topic} can actually help you achieve your goals."
            ]
        else:
            return [
                f"The most important thing about {topic} is this simple fact.",
                f"Here's how {topic} can make a real difference for you."
            ]
    
    def _generate_cta(self, topic: str, format_type: str, tone: str) -> str:
        """Generate call-to-action"""
        
        ctas = {
            "tiktok": [
                "Drop a comment if you want to see more about this!",
                "Follow for more tips like this!",
                "Share this with someone who needs to see it!",
                "What do you think about this? Let me know below!"
            ],
            "youtube": [
                "If you found this helpful, please like and subscribe for more content!",
                "Let me know in the comments what you think about this topic.",
                "Don't forget to hit that notification bell for more videos like this!",
                "Share your experiences with this in the comments below."
            ],
            "instagram": [
                "Save this post for later!",
                "Tag someone who needs to see this!",
                "What's your take on this? Comment below!",
                "Follow for more content like this!"
            ]
        }
        
        cta_options = ctas.get(format_type, ctas["youtube"])
        return cta_options[0]  # Return first option for simplicity
    
    def _extract_keywords(self, topic: str, script: str) -> List[str]:
        """Extract keywords from topic and script"""
        
        # Simple keyword extraction
        words = (topic + " " + script).lower().split()
        keywords = [word for word in words if len(word) > 3]
        
        # Remove duplicates and return top keywords
        unique_keywords = list(set(keywords))
        return unique_keywords[:10]
    
    def _generate_hashtags(self, topic: str, format_type: str, keywords: List[str]) -> List[str]:
        """Generate relevant hashtags"""
        
        # Platform-specific hashtags
        platform_tags = {
            "tiktok": ["#fyp", "#viral", "#trending", "#foryou"],
            "youtube": ["#youtube", "#video", "#content", "#tutorial"],
            "instagram": ["#instagram", "#reels", "#content", "#creator"]
        }
        
        # Generic hashtags based on topic
        topic_words = topic.lower().split()
        topic_tags = [f"#{word}" for word in topic_words if len(word) > 2]
        
        # Keyword-based hashtags
        keyword_tags = [f"#{word}" for word in keywords[:5] if len(word) > 3]
        
        # Combine all hashtags
        all_tags = platform_tags.get(format_type, []) + topic_tags + keyword_tags
        
        # Remove duplicates and return
        return list(set(all_tags))[:15]
    
    def _get_format_info(self, format_type: str, duration: int) -> Dict[str, Any]:
        """Get format-specific information"""
        
        format_specs = {
            "tiktok": {
                "platform": "TikTok",
                "optimal_length": 30,
                "style_notes": "High energy, quick cuts, trending audio, vertical format"
            },
            "youtube": {
                "platform": "YouTube",
                "optimal_length": 60,
                "style_notes": "Conversational, educational, good pacing, horizontal format"
            },
            "instagram": {
                "platform": "Instagram",
                "optimal_length": 45,
                "style_notes": "Visually appealing, story-driven, hashtag-friendly, square/vertical format"
            },
            "generic": {
                "platform": "Generic",
                "optimal_length": 60,
                "style_notes": "Adaptable to any platform, focus on clear messaging"
            }
        }
        
        return format_specs.get(format_type, format_specs["generic"])
    
    def _error(self, message: str) -> Dict[str, Any]:
        """Return standardized error response"""
        return {
            "success": False,
            "error": message,
            "error_code": "SCRIPT_GENERATION_ERROR",
            "agent_version": self.version
        }

def main():
    """Main entry point for command line usage"""
    if len(sys.argv) != 2:
        print(json.dumps({
            "success": False,
            "error": "Usage: python script_generator.py '<json_input>'",
            "error_code": "INVALID_ARGUMENTS"
        }))
        sys.exit(1)
    
    try:
        input_data = json.loads(sys.argv[1])
        generator = ScriptGenerator()
        result = generator.generate_script(input_data)
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