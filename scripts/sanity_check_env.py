#!/usr/bin/env python3
"""
Environment Sanity Check Script - AgentOS Diagnostiek Tool
===========================================================

🎯 DOEL: Snel controleren of alle environment variabelen correct zijn geladen.
         Super handig voor debugging van configuratie problemen.

📋 GEBRUIK:
    # Van project root:
    python scripts/sanity_check_env.py

    # Als module (van anywhere):
    python -m scripts.sanity_check_env

    # Quick one-liner voor specifieke check:
    python -c "import os; from dotenv import load_dotenv; load_dotenv(override=True); print('USE_UNIFIED_ANALYZER=', os.getenv('USE_UNIFIED_ANALYZER'))"

✅ WANNEER GEBRUIKEN:
    - Environment troubleshooting
    - Pre-deployment checks
    - Nieuwe server setup verification
    - Debug waarom features niet werken (bv. geen viral moments gevonden)
    - Na .env file wijzigingen

🔧 WAT HET CHECKT:
    - API keys (zonder ze te tonen)
    - Feature flags (USE_UNIFIED_ANALYZER, etc.)
    - Moment detection settings (thresholds, topk, etc.)
    - Audio processing (faster-whisper, VAD)
    - Database/Redis connecties
    - Environment info (debug, ports)
"""

import os
from dotenv import load_dotenv

def check_environment():
    """
    Check key environment variables voor AgentOS

    Laadt .env met override (zelfde als production code) en controleert
    alle belangrijke settings voor viral moment detection en AI processing.
    """

    # Load .env with override (same as production code)
    load_dotenv(override=True)

    print("🔍 AgentOS Environment Sanity Check")
    print("=" * 50)

    # Core API Keys
    print("\n📋 API Keys:")
    print(f"  ANTHROPIC_API_KEY set: {bool(os.getenv('ANTHROPIC_API_KEY'))}")
    print(f"  OPENAI_API_KEY set: {bool(os.getenv('OPENAI_API_KEY'))}")

    # Feature Flags
    print("\n🚀 Feature Flags:")
    print(f"  USE_UNIFIED_ANALYZER: {os.getenv('USE_UNIFIED_ANALYZER')}")
    print(f"  UCA_V2_ENABLED: {os.getenv('UCA_V2_ENABLED')}")
    print(f"  USE_FASTER_WHISPER: {os.getenv('USE_FASTER_WHISPER')}")
    print(f"  ENABLE_REAL_AI: {os.getenv('ENABLE_REAL_AI')}")

    # Moment Detection Settings
    print("\n🎯 Moment Detection:")
    print(f"  MOMENTS_MIN_CONF: {os.getenv('MOMENTS_MIN_CONF')}")
    print(f"  MOMENTS_TOPK: {os.getenv('MOMENTS_TOPK')}")
    print(f"  MOMENTS_MIN_GAP_S: {os.getenv('MOMENTS_MIN_GAP_S')}")
    print(f"  MOMENTS_RECALL_RETRY: {os.getenv('MOMENTS_RECALL_RETRY')}")
    print(f"  MOMENTS_RECALL_MIN_CONF: {os.getenv('MOMENTS_RECALL_MIN_CONF')}")

    # Audio Processing
    print("\n🎵 Audio Processing:")
    print(f"  FASTER_WHISPER_MODEL: {os.getenv('FASTER_WHISPER_MODEL')}")
    print(f"  FASTER_WHISPER_DEVICE: {os.getenv('FASTER_WHISPER_DEVICE')}")
    print(f"  VAD_ENABLE: {os.getenv('VAD_ENABLE')}")

    # Database & Redis
    print("\n💾 Storage:")
    print(f"  DATABASE_URL set: {bool(os.getenv('DATABASE_URL'))}")
    print(f"  REDIS_URL set: {bool(os.getenv('REDIS_URL'))}")

    # Environment Info
    print("\n🌍 Environment:")
    print(f"  ENV: {os.getenv('ENV')}")
    print(f"  DEBUG: {os.getenv('DEBUG')}")
    print(f"  API_PORT: {os.getenv('API_PORT')}")

    print("\n" + "=" * 50)

    # Quick validation
    issues = []

    if not os.getenv('ANTHROPIC_API_KEY'):
        issues.append("❌ Missing ANTHROPIC_API_KEY")

    if os.getenv('USE_UNIFIED_ANALYZER') != 'true':
        issues.append("⚠️ USE_UNIFIED_ANALYZER not enabled")

    if not os.getenv('MOMENTS_MIN_CONF'):
        issues.append("⚠️ MOMENTS_MIN_CONF not set (will use default)")

    if issues:
        print("🚨 Issues Found:")
        for issue in issues:
            print(f"  {issue}")
    else:
        print("✅ All key settings look good!")

    print("")

if __name__ == "__main__":
    check_environment()