#!/usr/bin/env python3
"""
Environment Configuration Health Check
Toont de werkelijke runtime waarden die het systeem gebruikt
"""

import os
from dotenv import load_dotenv
from datetime import datetime

# Load env zoals de app dat doet
load_dotenv(override=False)

def check_env_config():
    """Print effectieve environment configuratie"""

    print("=" * 60)
    print(f"🔍 ENV CONFIG CHECK - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    # Kritieke AI Settings
    print("\n🤖 AI CONFIGURATIE:")
    print(f"  ENABLE_REAL_AI: {os.getenv('ENABLE_REAL_AI')}")
    print(f"  USE_MOCK_AI: {os.getenv('USE_MOCK_AI')}")
    print(f"  USE_FASTER_WHISPER: {os.getenv('USE_FASTER_WHISPER')}")
    print(f"  FASTER_WHISPER_MODEL: {os.getenv('FASTER_WHISPER_MODEL')}")
    print(f"  FASTER_WHISPER_DEVICE: {os.getenv('FASTER_WHISPER_DEVICE')}")
    print(f"  FASTER_WHISPER_COMPUTE: {os.getenv('FASTER_WHISPER_COMPUTE')}")
    print(f"  VAD_ENABLE: {os.getenv('VAD_ENABLE')}")

    # Claude API Status
    anthropic_key = os.getenv('ANTHROPIC_API_KEY')
    if anthropic_key:
        print(f"  ANTHROPIC_API_KEY: ✅ Configured (moment detection will use AI)")
        print(f"  MAX_CLAUDE_CALLS_PER_DAY: {os.getenv('MAX_CLAUDE_CALLS_PER_DAY', 'No limit set')}")
        print(f"  LOG_CLAUDE_USAGE: {os.getenv('LOG_CLAUDE_USAGE', 'false')}")
    else:
        print(f"  ANTHROPIC_API_KEY: ❌ Not configured (fallback to keyword detection)")

    # Timeouts
    print("\n⏰ TIMEOUTS (seconden):")
    print(f"  LOCAL_TIMEOUT_S: {os.getenv('LOCAL_TIMEOUT_S')} ({float(os.getenv('LOCAL_TIMEOUT_S', 0))/3600:.1f} uur)")
    print(f"  WHISPER_TIMEOUT: {os.getenv('WHISPER_TIMEOUT')} ({float(os.getenv('WHISPER_TIMEOUT', 0))/3600:.1f} uur)")
    print(f"  PROCESSING_TIMEOUT: {os.getenv('PROCESSING_TIMEOUT')} ({float(os.getenv('PROCESSING_TIMEOUT', 0))/3600:.1f} uur)")
    print(f"  OPENAI_TIMEOUT_S: {os.getenv('OPENAI_TIMEOUT_S')}")
    print(f"  AUDIO_TIMEOUT_S: {os.getenv('AUDIO_TIMEOUT_S')}")

    # Limieten
    print("\n📏 LIMIETEN:")
    print(f"  MAX_VIDEO_LENGTH: {os.getenv('MAX_VIDEO_LENGTH')} sec ({float(os.getenv('MAX_VIDEO_LENGTH', 0))/3600:.1f} uur)")
    print(f"  MAX_CLIP_LENGTH: {os.getenv('MAX_CLIP_LENGTH')} sec ({float(os.getenv('MAX_CLIP_LENGTH', 0))/60:.1f} min)")

    # Environment Consistency Check
    print("\n🔧 ENVIRONMENT SETTINGS:")
    env_val = os.getenv('ENV')
    environment_val = os.getenv('ENVIRONMENT')
    if env_val and environment_val:
        if env_val == environment_val:
            print(f"  ENV & ENVIRONMENT: ✅ Both set to '{env_val}'")
        else:
            print(f"  ENV & ENVIRONMENT: ⚠️  Mismatch! ENV={env_val}, ENVIRONMENT={environment_val}")
    else:
        print(f"  ENV: {env_val or '❌ Not set'}")
        print(f"  ENVIRONMENT: {environment_val or '❌ Not set'}")

    # Moment Detection
    print("\n🎯 MOMENT DETECTION:")
    print(f"  MOMENTS_CLUSTER_GAP_S: {os.getenv('MOMENTS_CLUSTER_GAP_S')}")
    print(f"  MOMENTS_MIN_GAP: {os.getenv('MOMENTS_MIN_GAP')}")
    print(f"  LONG_FORM_PROCESSING: {os.getenv('LONG_FORM_PROCESSING')}")

    # Check for duplicates in .env file
    print("\n⚠️  DUPLICATE CHECK:")
    duplicates = check_duplicates()
    if duplicates:
        print("  GEVONDEN DUPLICATEN:")
        for key, count in duplicates.items():
            print(f"    - {key}: {count} keer gedefinieerd")
    else:
        print("  ✅ Geen duplicaten gevonden")

    # Worker proces info
    print("\n🔄 PROCES INFO:")
    import subprocess
    try:
        result = subprocess.run(['ps', 'aux'], capture_output=True, text=True)
        celery_count = len([l for l in result.stdout.splitlines() if 'celery' in l and 'grep' not in l])
        print(f"  Celery workers running: {celery_count}")
    except:
        print("  Kon proces info niet ophalen")

    print("\n" + "=" * 60)
    print("💡 TIP: Als waarden niet kloppen:")
    print("  1. Check .env voor duplicaten")
    print("  2. Herstart alle workers: pkill celery && celery worker ...")
    print("  3. Check of er geen host env vars zijn: env | grep FASTER")
    print("=" * 60)

def check_duplicates():
    """Check .env file voor duplicate keys"""
    if not os.path.exists('.env'):
        return {}

    key_counts = {}
    with open('.env', 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key = line.split('=')[0].strip()
                key_counts[key] = key_counts.get(key, 0) + 1

    return {k: v for k, v in key_counts.items() if v > 1}

if __name__ == "__main__":
    check_env_config()