"""
Realistic Mock Data Generator for AI Agents
==========================================

Generates realistic mock responses for development without API costs.
"""

import random
from typing import List, Dict, Any

class MockDataGenerator:
    """Generate realistic mock data for different AI services"""
    
    def __init__(self):
        self.video_topics = [
            "tech review", "gaming", "cooking tutorial", "vlog", "music video",
            "sports highlights", "educational content", "comedy sketch", "travel vlog"
        ]
        
        self.viral_phrases = [
            "This is insane!", "You won't believe what happens next",
            "Wait for it...", "The most amazing thing I've ever seen",
            "This changed my life", "Mind = blown", "Epic fail incoming",
            "Plot twist!", "No way this is real", "Watch till the end"
        ]
        
    def generate_transcript(self, duration_seconds: int) -> Dict[str, Any]:
        """Generate realistic transcript with timestamps"""
        segments = []
        current_time = 0.0
        segment_count = int(duration_seconds / 10)  # ~10 second segments
        
        for i in range(segment_count):
            # Generate segment duration (8-15 seconds)
            segment_duration = random.uniform(8, 15)
            if current_time + segment_duration > duration_seconds:
                segment_duration = duration_seconds - current_time
            
            # Generate text based on video topic
            topic = random.choice(self.video_topics)
            text = self._generate_segment_text(topic, i, segment_count)
            
            segment = {
                "start": round(current_time, 2),
                "end": round(current_time + segment_duration, 2),
                "text": text,
                "confidence": round(random.uniform(0.85, 0.99), 3)
            }
            segments.append(segment)
            current_time += segment_duration
            
            if current_time >= duration_seconds:
                break
        
        # Full transcript
        full_text = " ".join([s["text"] for s in segments])
        
        return {
            "success": True,
            "transcript": full_text,
            "segments": segments,
            "language": "en",
            "duration": duration_seconds,
            "word_count": len(full_text.split()),
            "processing_time": round(random.uniform(2.5, 5.0), 2),
            "method_used": "mock_whisper"
        }
    
    def detect_viral_moments(self, transcript: str, duration: int) -> List[Dict[str, Any]]:
        """Generate realistic viral moment detections"""
        moments = []
        
        # Generate 3-7 potential viral moments
        moment_count = random.randint(3, 7)
        used_timestamps = []
        
        for i in range(moment_count):
            # Generate unique timestamp with proper bounds checking
            while True:
                # Ensure we have enough video left for at least a 15-second clip
                max_start = max(5, duration - 15)  # At least 15 seconds for clip
                if max_start <= 5:  # Video too short for multiple clips
                    start_time = random.uniform(0, max(1, duration - 15))
                else:
                    start_time = random.uniform(5, max_start)
                    
                if not any(abs(start_time - t) < 10 for t in used_timestamps):  # Reduced overlap from 20 to 10
                    used_timestamps.append(start_time)
                    break
            
            # Moment duration (15 seconds or remaining video, whichever is less)
            max_clip_duration = duration - start_time - 1  # Leave 1 second buffer
            clip_duration = min(15, max_clip_duration)  # Fixed 15-second clips or remaining video
            
            moment = {
                "start_time": round(start_time, 2),
                "end_time": round(start_time + clip_duration, 2),
                "duration": round(clip_duration, 2),
                "score": round(random.uniform(0.7, 0.95), 3),
                "type": random.choice(["emotional", "funny", "surprising", "educational", "action"]),
                "description": self._generate_moment_description(),
                "tags": self._generate_tags(),
                "platform_scores": {
                    "tiktok": round(random.uniform(0.6, 0.95), 2),
                    "instagram": round(random.uniform(0.6, 0.95), 2),
                    "youtube_shorts": round(random.uniform(0.6, 0.95), 2)
                }
            }
            moments.append(moment)
        
        # Sort by score
        moments.sort(key=lambda x: x["score"], reverse=True)
        return moments
    
    def generate_face_detections(self, duration: int) -> List[Dict[str, Any]]:
        """Generate realistic face detection data"""
        # Randomly decide number of faces (1-3)
        face_count = random.randint(1, 3)
        faces = []
        
        for i in range(face_count):
            # Generate face appearances throughout video
            appearances = []
            current_time = 0
            
            while current_time < duration:
                # Face appears for 5-30 seconds
                appearance_duration = random.uniform(5, 30)
                if current_time + appearance_duration > duration:
                    appearance_duration = duration - current_time
                
                if random.random() > 0.3:  # 70% chance face is visible
                    appearance = {
                        "start": round(current_time, 2),
                        "end": round(current_time + appearance_duration, 2),
                        "confidence": round(random.uniform(0.85, 0.99), 3),
                        "bbox": self._generate_bbox()
                    }
                    appearances.append(appearance)
                
                current_time += appearance_duration + random.uniform(0, 5)
            
            face = {
                "face_id": f"face_{i+1}",
                "appearances": appearances,
                "total_screen_time": sum(a["end"] - a["start"] for a in appearances),
                "average_confidence": round(sum(a["confidence"] for a in appearances) / len(appearances) if appearances else 0, 3)
            }
            faces.append(face)
        
        return faces
    
    def _generate_segment_text(self, topic: str, index: int, total: int) -> str:
        """Generate text for a transcript segment"""
        if index == 0:
            return f"Hey everyone, welcome back to my channel! Today we're talking about {topic}."
        elif index == total - 1:
            return "Thanks for watching! Don't forget to like and subscribe for more content like this."
        else:
            templates = [
                f"So the interesting thing about {topic} is that it's constantly evolving.",
                "Let me show you something really cool about this.",
                "This is where it gets really interesting.",
                "Now, you might be wondering why this matters.",
                "Here's a pro tip that not many people know about.",
                random.choice(self.viral_phrases)
            ]
            return random.choice(templates)
    
    def _generate_moment_description(self) -> str:
        """Generate description for a viral moment"""
        templates = [
            "High-energy moment with strong emotional impact",
            "Unexpected twist that viewers won't see coming",
            "Relatable content that resonates with audience",
            "Visually stunning sequence with great production value",
            "Funny moment that's highly shareable",
            "Educational insight presented in engaging way",
            "Action-packed sequence that keeps viewers hooked"
        ]
        return random.choice(templates)
    
    def _generate_tags(self) -> List[str]:
        """Generate relevant tags for a moment"""
        all_tags = [
            "viral", "trending", "mustwatch", "epic", "funny", "amazing",
            "mindblowing", "satisfying", "wholesome", "unexpected", "wow",
            "omg", "skills", "talent", "creative", "inspiring"
        ]
        return random.sample(all_tags, k=random.randint(3, 6))
    
    def _generate_bbox(self) -> Dict[str, float]:
        """Generate a bounding box for face detection"""
        # Generate reasonable face position (center-ish)
        x = random.uniform(0.2, 0.6)
        y = random.uniform(0.1, 0.4)
        width = random.uniform(0.15, 0.3)
        height = random.uniform(0.2, 0.35)
        
        return {
            "x": round(x, 3),
            "y": round(y, 3),
            "width": round(width, 3),
            "height": round(height, 3)
        }
    
    def generate_crop_suggestions(self, moments: List[Dict], faces: List[Dict]) -> List[Dict[str, Any]]:
        """Generate intelligent crop suggestions for different platforms"""
        suggestions = []
        
        platforms = [
            {"name": "tiktok", "aspect_ratio": "9:16", "resolution": "1080x1920"},
            {"name": "instagram_reels", "aspect_ratio": "9:16", "resolution": "1080x1920"},
            {"name": "youtube_shorts", "aspect_ratio": "9:16", "resolution": "1080x1920"},
            {"name": "instagram_square", "aspect_ratio": "1:1", "resolution": "1080x1080"}
        ]
        
        for moment in moments[:5]:  # Top 5 moments
            for platform in platforms:
                suggestion = {
                    "moment_id": f"moment_{moments.index(moment)+1}",
                    "platform": platform["name"],
                    "aspect_ratio": platform["aspect_ratio"],
                    "resolution": platform["resolution"],
                    "crop_region": self._generate_crop_region(platform["aspect_ratio"]),
                    "face_tracking": len(faces) > 0,
                    "optimization_score": round(random.uniform(0.8, 0.95), 3)
                }
                suggestions.append(suggestion)
        
        return suggestions
    
    def _generate_crop_region(self, aspect_ratio: str) -> Dict[str, float]:
        """Generate crop region based on aspect ratio"""
        if aspect_ratio == "9:16":  # Vertical
            return {
                "x": round(random.uniform(0.2, 0.4), 3),
                "y": 0.0,
                "width": 0.33,
                "height": 1.0
            }
        elif aspect_ratio == "1:1":  # Square
            return {
                "x": round(random.uniform(0.1, 0.3), 3),
                "y": round(random.uniform(0.1, 0.2), 3),
                "width": 0.6,
                "height": 0.6
            }
        else:  # Default
            return {"x": 0.0, "y": 0.0, "width": 1.0, "height": 1.0}