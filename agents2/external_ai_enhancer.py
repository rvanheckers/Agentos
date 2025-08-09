#!/usr/bin/env python3
"""
External AI Enhancer Agent - Third-party Integration Demo
=========================================================

Demonstrates how external AI services can be integrated as AgentOS agents.
This example shows OpenAI GPT integration as a content enhancement agent.

Input JSON format:
{
    "content": "Original text content to enhance",
    "enhancement_type": "social_media" | "professional" | "creative" | "technical",
    "target_audience": "general" | "teens" | "professionals" | "experts",
    "tone": "casual" | "formal" | "energetic" | "authoritative",
    "max_length": 500,
    "include_hashtags": true
}
"""

import json
import sys
import os
import time
from typing import Dict, Any

# Load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Add parent directory to path for MCP imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# MCP Integration
try:
    from mcp.adapter import mcp_compatible
    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False

# Smart AI Service with OpenAI + Claude Integration
class SmartAIService:
    """Real AI service with OpenAI GPT and Claude integration"""

    def __init__(self):
        self.service_name = "Smart AI Service"
        self.version = "2.0"
        self.openai_available = self._check_openai()
        self.claude_available = self._check_claude()
        self.available = self.openai_available or self.claude_available

        # Initialize clients
        if self.openai_available:
            import openai
            self.openai_client = openai.OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

        if self.claude_available:
            import anthropic
            self.claude_client = anthropic.Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))

    def _check_openai(self) -> bool:
        """Check if OpenAI is available"""
        try:
            api_key = os.getenv('OPENAI_API_KEY')
            if not api_key:
                return False
            import importlib.util
            return importlib.util.find_spec("openai") is not None
        except ImportError:
            return False

    def _check_claude(self) -> bool:
        """Check if Claude is available"""
        try:
            api_key = os.getenv('ANTHROPIC_API_KEY')
            if not api_key:
                return False
            import importlib.util
            return importlib.util.find_spec("anthropic") is not None
        except ImportError:
            return False

    def enhance_content(self, content: str, enhancement_type: str, **kwargs) -> Dict[str, Any]:
        """Enhanced content using real AI services"""

        # Try AI enhancement first
        if self.available:
            try:
                return self._enhance_with_ai(content, enhancement_type, **kwargs)
            except Exception as e:
                print(f"AI enhancement failed, falling back to mock: {e}", file=sys.stderr)

        # Fallback to improved mock
        return self._enhanced_mock_content(content, enhancement_type, **kwargs)

    def _enhance_with_ai(self, content: str, enhancement_type: str, **kwargs) -> Dict[str, Any]:
        """Real AI enhancement using OpenAI or Claude"""

        target_audience = kwargs.get("target_audience", "general")
        tone = kwargs.get("tone", "casual")
        max_length = kwargs.get("max_length", 500)

        # Create smart prompt
        prompt = self._build_enhancement_prompt(content, enhancement_type, target_audience, tone, max_length)

        # Try OpenAI first (faster + cheaper)
        if self.openai_available:
            try:
                response = self.openai_client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {"role": "system", "content": "You are an expert content creator specializing in viral social media content."},
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=600,
                    temperature=0.7
                )

                ai_result = response.choices[0].message.content
                return self._parse_ai_response(ai_result, enhancement_type, "OpenAI GPT-3.5")

            except Exception as e:
                print(f"OpenAI failed: {e}", file=sys.stderr)

        # Fallback to Claude
        if self.claude_available:
            try:
                response = self.claude_client.messages.create(
                    model="claude-3-haiku-20240307",
                    max_tokens=600,
                    messages=[
                        {"role": "user", "content": prompt}
                    ]
                )

                ai_result = response.content[0].text
                return self._parse_ai_response(ai_result, enhancement_type, "Claude Haiku")

            except Exception as e:
                print(f"Claude failed: {e}", file=sys.stderr)

        raise Exception("No AI services available")

    def _build_enhancement_prompt(self, content: str, enhancement_type: str, audience: str, tone: str, max_length: int) -> str:
        """Build smart prompt for AI enhancement"""

        prompts = {
            "social_media": f"""
Transform this content for viral social media:

Original: "{content}"

Make it:
- Hook viewers in first 3 seconds
- {tone} tone for {audience} audience  
- Maximum {max_length} characters
- Include 3-5 relevant hashtags
- Add engaging elements (emojis, calls-to-action)

Format:
ENHANCED: [enhanced content here]
HASHTAGS: #tag1 #tag2 #tag3
ENGAGEMENT_SCORE: 0.X (0-1 viral potential)
""",

            "professional": f"""
Enhance this content for professional audiences:

Original: "{content}"

Make it:
- Clear, authoritative tone
- Professional language
- Structured presentation
- {audience} audience focus
- Maximum {max_length} characters

Format:
ENHANCED: [enhanced content]
HASHTAGS: #professional #hashtags
ENGAGEMENT_SCORE: 0.X (0-1 quality score)
""",

            "creative": f"""
Transform this content with creative flair:

Original: "{content}"

Make it:
- Artistic and imaginative
- Storytelling elements
- Visual language
- {tone} creative tone
- Maximum {max_length} characters

Format:
ENHANCED: [enhanced content]
HASHTAGS: #creative #hashtags  
ENGAGEMENT_SCORE: 0.X (0-1 creativity score)
"""
        }

        return prompts.get(enhancement_type, prompts["professional"])

    def _parse_ai_response(self, ai_response: str, enhancement_type: str, provider: str) -> Dict[str, Any]:
        """Parse AI response into structured format"""

        try:
            # Extract components using simple parsing
            enhanced_content = ""
            hashtags = []
            engagement_score = 0.8

            lines = ai_response.split('\n')
            for line in lines:
                line = line.strip()
                if line.startswith('ENHANCED:'):
                    enhanced_content = line.replace('ENHANCED:', '').strip()
                elif line.startswith('HASHTAGS:'):
                    hashtag_text = line.replace('HASHTAGS:', '').strip()
                    hashtags = [tag.strip() for tag in hashtag_text.split() if tag.startswith('#')]
                elif line.startswith('ENGAGEMENT_SCORE:'):
                    try:
                        score_text = line.replace('ENGAGEMENT_SCORE:', '').strip()
                        engagement_score = float(score_text)
                    except (ValueError, TypeError):
                        engagement_score = 0.8

            # If parsing failed, use the full response
            if not enhanced_content:
                enhanced_content = ai_response.strip()

            # Generate hashtags if none found
            if not hashtags:
                hashtags = self._generate_default_hashtags(enhancement_type)

            return {
                "enhanced_content": enhanced_content,
                "hashtags": hashtags[:5],  # Limit to 5 hashtags
                "engagement_score": min(max(engagement_score, 0.0), 1.0),
                "provider": provider
            }

        except Exception as e:
            print(f"AI response parsing failed: {e}", file=sys.stderr)
            return {
                "enhanced_content": ai_response.strip(),
                "hashtags": self._generate_default_hashtags(enhancement_type),
                "engagement_score": 0.7,
                "provider": f"{provider} (parsed with fallback)"
            }

    def _generate_default_hashtags(self, enhancement_type: str) -> list:
        """Generate default hashtags when AI doesn't provide them"""
        hashtag_sets = {
            "social_media": ["#viral", "#trending", "#content", "#socialmedia"],
            "professional": ["#professional", "#business", "#quality", "#expertise"],
            "creative": ["#creative", "#artistic", "#storytelling", "#vision"],
            "technical": ["#technical", "#analysis", "#precision", "#methodology"]
        }
        return hashtag_sets.get(enhancement_type, ["#content", "#ai", "#enhanced"])

    def _enhanced_mock_content(self, content: str, enhancement_type: str, **kwargs) -> Dict[str, Any]:
        """Improved mock content when AI is not available"""

        enhancements = {
            "social_media": {
                "enhanced_content": f"🔥 VIRAL ALERT! 🔥\n\n{content}\n\n💡 This content is optimized for maximum social media engagement! Ready to blow up your feed? 🚀\n\n👉 Double-tap if you agree!",
                "hashtags": ["#viral", "#trending", "#socialmedia", "#engagement", "#content"],
                "engagement_score": 0.87
            },
            "professional": {
                "enhanced_content": f"Professional Content Enhancement:\n\n{content}\n\nKey Benefits:\n• Optimized for professional audiences\n• Clear, structured presentation\n• Authoritative tone and messaging\n• Industry-standard best practices\n\nResult: Enhanced professional communication.",
                "hashtags": ["#professional", "#business", "#quality", "#expertise", "#leadership"],
                "engagement_score": 0.92
            },
            "creative": {
                "enhanced_content": f"✨ Creative Transformation ✨\n\nImagine this: {content}\n\nBut now, envision it painted with the colors of imagination, where every word dances with possibility and every sentence tells a story that resonates deep within the soul.\n\n🎨 Art meets content. Magic happens.",
                "hashtags": ["#creative", "#artistic", "#storytelling", "#imagination", "#vision"],
                "engagement_score": 0.89
            }
        }

        result = enhancements.get(enhancement_type, enhancements["professional"])
        result["provider"] = "Enhanced Mock Service (AI unavailable)"
        return result

class ExternalAIEnhancer:
    """
    Third-party AI Enhancement Agent
    
    Demonstrates how external AI services can be integrated into AgentOS
    via the MCP protocol for seamless agent collaboration.
    """

    def __init__(self):
        self.version = "2.0.0"
        self.service = SmartAIService()
        self.capabilities = [
            "content_enhancement",
            "ai_processing",
            "third_party_integration",
            "social_optimization",
            "openai_integration",
            "claude_integration"
        ]

    def enhance_content(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Enhance content using external AI service
        
        Args:
            input_data: {
                "content": str,              # Content to enhance
                "enhancement_type": str,     # Type of enhancement
                "target_audience": str,      # Target audience
                "tone": str,                 # Desired tone
                "max_length": int,           # Max output length
                "include_hashtags": bool     # Include hashtags
            }
            
        Returns:
            {
                "success": bool,
                "enhanced_content": str,
                "original_content": str,
                "enhancement_type": str,
                "hashtags": List[str],
                "metrics": {
                    "engagement_score": float,
                    "enhancement_quality": float,
                    "processing_time": float
                },
                "external_service": {
                    "provider": str,
                    "version": str,
                    "status": str
                },
                "agent_version": str
            }
        """

        start_time = time.time()

        try:
            # Validate input
            if not input_data.get("content"):
                return self._error("Content is required")

            content = input_data["content"]
            enhancement_type = input_data.get("enhancement_type", "professional")
            target_audience = input_data.get("target_audience", "general")
            tone = input_data.get("tone", "casual")
            max_length = input_data.get("max_length", 500)
            include_hashtags = input_data.get("include_hashtags", True)

            # Call smart AI service
            enhancement_result = self.service.enhance_content(
                content=content,
                enhancement_type=enhancement_type,
                target_audience=target_audience,
                tone=tone,
                max_length=max_length
            )

            # Calculate quality metrics
            original_length = len(content)
            enhanced_length = len(enhancement_result["enhanced_content"])
            enhancement_quality = min(enhanced_length / max(original_length, 1), 2.0)  # Cap at 2x improvement

            processing_time = time.time() - start_time

            result = {
                "success": True,
                "enhanced_content": enhancement_result["enhanced_content"],
                "original_content": content,
                "enhancement_type": enhancement_type,
                "hashtags": enhancement_result["hashtags"] if include_hashtags else [],
                "metrics": {
                    "engagement_score": enhancement_result["engagement_score"],
                    "enhancement_quality": enhancement_quality,
                    "processing_time": processing_time,
                    "length_improvement": enhanced_length / original_length if original_length > 0 else 1.0
                },
                "external_service": {
                    "provider": enhancement_result.get("provider", self.service.service_name),
                    "version": self.service.version,
                    "status": "available" if self.service.available else "unavailable",
                    "openai_available": self.service.openai_available,
                    "claude_available": self.service.claude_available
                },
                "agent_version": self.version,
                "third_party_integration": {
                    "type": "external_ai_service",
                    "authenticated": True,
                    "rate_limited": False,
                    "cost_estimated": 0.02  # Mock cost in USD
                }
            }

            return result

        except Exception as e:
            return self._error(f"Enhancement failed: {str(e)}")

    def _error(self, message: str) -> Dict[str, Any]:
        """Return standardized error response"""
        return {
            "success": False,
            "error": message,
            "error_code": "EXTERNAL_AI_ERROR",
            "enhanced_content": "",
            "original_content": "",
            "agent_version": self.version,
            "external_service": {
                "provider": "unavailable",
                "version": "unknown",
                "status": "error"
            }
        }

# MCP-compatible wrapper
@mcp_compatible("external_ai_enhancer", "1.0", ["content_enhancement", "ai_processing", "third_party_integration"])
def main(input_data):
    """
    Main entry point for MCP-compatible execution
    
    This decorator makes the agent fully compatible with AgentOS MCP protocol
    while maintaining backwards compatibility with legacy JSON I/O.
    """
    enhancer = ExternalAIEnhancer()
    return enhancer.enhance_content(input_data)

if __name__ == "__main__":
    # Standalone execution (non-MCP mode)
    if len(sys.argv) != 2:
        print(json.dumps({
            "success": False,
            "error": "Usage: python external_ai_enhancer.py '<json_input>'",
            "error_code": "INVALID_ARGUMENTS"
        }))
        sys.exit(1)

    try:
        input_data = json.loads(sys.argv[1])
        enhancer = ExternalAIEnhancer()
        result = enhancer.enhance_content(input_data)
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
