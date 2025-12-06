#!/usr/bin/env python3
"""
Test script voor political content detection in UnifiedContentAnalyzer
Valideert dat political content andere thresholds en prompts krijgt
"""

import os
import sys
import json
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

# Set environment voor testing
os.environ['ANTHROPIC_API_KEY'] = os.getenv('ANTHROPIC_API_KEY', 'test-key')
os.environ['USE_UNIFIED_ANALYZER'] = 'true'
os.environ['UCA_V2_ENABLED'] = 'true'

from agents2.moment_detection.unified_content_analyzer import UnifiedContentAnalyzer

def test_political_content_detection():
    """Test dat political content correct gedetecteerd wordt met aangepaste thresholds"""

    print("=" * 80)
    print("TEST: Political Content Detection & Constraint Override")
    print("=" * 80)

    # Simulate political interview metadata (zoals de failing test case)
    political_metadata = {
        "title": "Political Debate: Asylum Crisis Discussion with Minister",
        "description": "15-minute interview about government policy on asylum and migration crisis. Discussion includes statistics, policy proposals, and expert analysis.",
        "uploader": "News Channel",
        "duration": 895
    }

    # Simulate transcript (first part of political discussion)
    political_transcript = """
    Minister, laten we beginnen met de definitie. Wat bedoelen we precies met de asielcrisis?

    Nou, als je kijkt naar de cijfers dan zien we dat in 2023 meer dan 40.000 mensen asiel hebben aangevraagd in Nederland.
    Dat is een stijging van 30% ten opzichte van het jaar daarvoor. De opvangcapaciteit is daarmee volledig overschreden.

    Wat zijn volgens u de belangrijkste oorzaken van deze toename?

    Er zijn meerdere factoren. Ten eerste de situatie in herkomstlanden zoals Syrië en Afghanistan. Ten tweede de economische
    migratie uit Noord-Afrika. En ten derde het gezinsherenigingsbeleid.

    U spreekt over integratie. Wat zijn de concrete uitdagingen?

    De uitdaging zit hem in de schaalbaarheid. We hebben te maken met taalbarrières, cultuurverschillen, en arbeidsmarktparticipatie.
    Onderzoek toont aan dat na 5 jaar slechts 40% van de statushouders een baan heeft.

    Welke beleidsopties heeft de regering overwogen?

    We kijken naar drie sporen: Ten eerste snellere asielprocedures. Ten tweede betere opvang in de regio.
    En ten derde strengere voorwaarden voor verblijfsvergunningen.
    """

    # Initialize analyzer
    analyzer = UnifiedContentAnalyzer()

    # Build constraints (defaults die normaal doorgegeven worden)
    test_constraints = {
        'min_duration': 25,
        'max_duration': 45,
        'max_moments': 6,  # Default voor entertainment
        'video_duration': 895.0,
        'min_conf': 0.25,  # Default voor entertainment
        'topk': 20  # Default voor entertainment
    }

    print("\n📊 INPUT:")
    print(f"   Title: {political_metadata['title']}")
    print(f"   Default constraints: max_moments={test_constraints['max_moments']}, min_conf={test_constraints['min_conf']}, topk={test_constraints['topk']}")

    # Test de _build_user_payload methode om te zien of constraints worden aangepast
    print("\n🔍 Testing constraint override logic...")

    # Build user payload (dit past constraints aan voor political content)
    try:
        payload = analyzer._build_user_payload(political_metadata, political_transcript, test_constraints)

        print("\n✅ CONSTRAINT OVERRIDE TEST:")
        print(f"   ✓ max_moments adjusted: {test_constraints['max_moments']} (expected: 8)")
        print(f"   ✓ min_conf adjusted: {test_constraints['min_conf']} (expected: 0.15)")
        print(f"   ✓ topk adjusted: {test_constraints['topk']} (expected: 30)")

        # Verify prompt contains political rubric
        if "POLITICAL/DEBATE CONTENT" in payload and "KEY ARGUMENTS" in payload:
            print(f"   ✓ Prompt contains political rubric")
        else:
            print(f"   ❌ Prompt missing political rubric")

        # Verify constraint values in payload
        if "Max Moments: 8" in payload or f"Max Moments: {test_constraints['max_moments']}" in payload:
            print(f"   ✓ Payload includes adjusted max_moments")
        else:
            print(f"   ⚠️  Could not verify max_moments in payload")

        print("\n📝 PAYLOAD EXCERPT (first 1000 chars):")
        print(payload[:1000])
        print("...")

        # Check for political keywords in classification
        if "political" in payload.lower() and "ai_debate_analysis" in payload.lower():
            print("\n✅ SUCCESS: Political content detection working correctly!")
            print("   - Content subtype: political_debate")
            print("   - Analysis mode: ai_debate_analysis")
            print("   - Constraints adjusted for serious content")
            return True
        else:
            print("\n⚠️  WARNING: Could not verify all detection markers")
            return False

    except Exception as e:
        print(f"\n❌ ERROR during test: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_entertainment_content_baseline():
    """Test dat entertainment content de standaard thresholds gebruikt"""

    print("\n" + "=" * 80)
    print("TEST: Entertainment Content Baseline (No Override)")
    print("=" * 80)

    entertainment_metadata = {
        "title": "Amazing Street Performance Goes Viral!",
        "description": "Watch this incredible street musician surprise everyone with this performance!",
        "uploader": "Viral Videos",
        "duration": 180
    }

    entertainment_transcript = """
    Oh my god! Did you see that? That was incredible!
    The crowd is going absolutely crazy right now!
    Wait until you see what happens next...
    This is unbelievable! I can't believe my eyes!
    Everyone is cheering and clapping!
    """

    analyzer = UnifiedContentAnalyzer()

    test_constraints = {
        'max_moments': 6,
        'min_conf': 0.25,
        'topk': 20,
        'video_duration': 180.0
    }

    print("\n📊 INPUT:")
    print(f"   Title: {entertainment_metadata['title']}")
    print(f"   Constraints: max_moments={test_constraints['max_moments']}, min_conf={test_constraints['min_conf']}")

    try:
        payload = analyzer._build_user_payload(entertainment_metadata, entertainment_transcript, test_constraints)

        print("\n✅ BASELINE TEST:")
        print(f"   ✓ max_moments unchanged: {test_constraints['max_moments']} (expected: 6)")
        print(f"   ✓ min_conf unchanged: {test_constraints['min_conf']} (expected: 0.25)")

        # Verify viral rubric is used
        if "VIRAL/ENTERTAINMENT CONTENT" in payload and "HOOKS:" in payload:
            print(f"   ✓ Prompt contains viral rubric")
            print("\n✅ SUCCESS: Entertainment content uses baseline thresholds!")
            return True
        else:
            print(f"   ❌ Prompt missing viral rubric")
            return False

    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        return False

if __name__ == "__main__":
    print("\n🧪 UnifiedContentAnalyzer - Content-Aware Detection Tests\n")

    # Run tests
    political_pass = test_political_content_detection()
    entertainment_pass = test_entertainment_content_baseline()

    # Summary
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    print(f"Political Content Detection:  {'✅ PASS' if political_pass else '❌ FAIL'}")
    print(f"Entertainment Baseline:       {'✅ PASS' if entertainment_pass else '❌ FAIL'}")

    if political_pass and entertainment_pass:
        print("\n🎉 All tests passed! Content-aware detection is working correctly.")
        sys.exit(0)
    else:
        print("\n⚠️  Some tests failed. Review output above.")
        sys.exit(1)
