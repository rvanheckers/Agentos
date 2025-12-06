#!/usr/bin/env python3
"""
MD to JSON Converter voor AgentOS Roadmap
=========================================

Converteert ROADMAP_VALIDATED.md naar roadmap_validated.json
MD file is de source of truth, JSON wordt auto-gegenereerd.

Usage:
    python md_to_json_converter.py [--input ROADMAP_VALIDATED.md] [--output roadmap_validated.json]
"""

import json
import re
import sys
import argparse
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional

class RoadmapConverter:
    def __init__(self):
        self.current_dir = Path(__file__).parent

    # -------- Sanitizers --------
    def _normalize_token(self, s: str) -> str:
        """Trim, collapse inner whitespace to single space; strip control chars."""
        if s is None:
            return ""
        s = s.replace("\r", " ").replace("\n", " ").strip()
        # collapse multiple spaces/tabs
        s = re.sub(r"\s+", " ", s)
        return s

    def _normalize_path(self, s: str) -> str:
        """Normalize a path captured from MD: trim, remove newlines, collapse spaces around slashes, forbid backticks."""
        s = self._normalize_token(s)
        s = s.replace("`", "")
        # remove spaces around path separators
        s = re.sub(r"\s*/\s*", "/", s)
        # no accidental double slashes (except protocol-like, which we don't use here)
        s = re.sub(r"//+", "/", s)
        return s

    def parse_markdown(self, md_content: str) -> Dict[str, Any]:
        """Parse markdown content en converteer naar JSON structuur"""

        # Basis metadata
        metadata = self._extract_metadata(md_content)
        disclaimer = self._extract_disclaimer(md_content)
        current_status = self._extract_current_status(md_content)
        phases = self._extract_phases(md_content)
        testing = self._extract_testing(md_content)
        success_metrics = self._extract_success_metrics(md_content)
        risks_and_mitigations = self._extract_risks(md_content)
        execution_order = self._extract_execution_order(md_content)
        unique_selling_point = self._extract_usp(md_content)
        validation = self._extract_validation(md_content)

        technical_specs = self._extract_technical_spec_references(md_content)

        # NEW: Extract extended data from technical spec files
        enriched_phases = self._enrich_phases_with_technical_specs(phases, technical_specs)
        business_context = self._extract_business_context_from_specs(technical_specs)
        execution_framework = self._extract_execution_framework_from_specs(technical_specs)
        comprehensive_testing = self._extract_comprehensive_testing_from_specs(technical_specs)
        pre_flight_checks = self._extract_pre_flight_checks_from_specs(technical_specs)

        data = {
            "metadata": metadata,
            "disclaimer": disclaimer,
            "current_status": current_status,
            "phases": enriched_phases,  # Use enriched phases instead of basic ones
            "technical_specs": technical_specs,
            "business_context": business_context,  # NEW: Business context from technical specs
            "execution_framework": execution_framework,  # NEW: Execution framework
            "pre_flight_checks": pre_flight_checks,  # NEW: Pre-flight validation
            "comprehensive_testing": comprehensive_testing,  # NEW: Comprehensive test scenarios
            "testing": testing,
            "success_metrics": success_metrics,
            "risks_and_mitigations": risks_and_mitigations,
            "execution_order": execution_order,
            "unique_selling_point": unique_selling_point,
            "validation": validation
        }
        # Post-validate en warnings toevoegen
        self._post_validate(data)
        return data

    def _post_validate(self, data: Dict[str, Any]) -> None:
        """Voeg lichte validatie/warnings toe aan de JSON-output (niet failen, wel signaleren)."""
        warnings: List[str] = []
        # Check referenced spec files existence
        refs = data.get("technical_specs", {}).get("references", {})
        missing = []
        for _id, ref in refs.items():
            if not ref.get("exists", False):
                missing.append(ref.get("absolute_path"))
        if missing:
            warnings.append(f"Missing spec files: {', '.join(missing)}")
        # Bewaar warnings
        data.setdefault("validation", {})
        data["validation"]["warnings"] = warnings

    def _extract_metadata(self, content: str) -> Dict[str, Any]:
        """Extract metadata from header"""
        title_match = re.search(r'^# (.+)', content, re.MULTILINE)
        validation_match = re.search(r'\*Laatste validatie: (.+?)\*', content)

        return {
            "title": title_match.group(1) if title_match else "AgentOS Complete Roadmap - GEVALIDEERD",
            "last_validated": validation_match.group(1) if validation_match else datetime.utcnow().isoformat(timespec="seconds") + "Z",
            "version": "1.0.1",
            "schema_version": "roadmap-json/1",
            "language": "nl"
        }

    def _extract_disclaimer(self, content: str) -> Dict[str, Any]:
        """Extract disclaimer section"""
        disclaimer_section = re.search(
            r'## ⚠️ BELANGRIJKE DISCLAIMER(.*?)---',
            content,
            re.DOTALL
        )

        if not disclaimer_section:
            return {}

        warnings = []
        warning_matches = re.findall(r'- ✅ \*\*(.+?)\*\*', disclaimer_section.group(1))
        for match in warning_matches:
            warnings.append(match.replace('VALIDEER EERST', 'VALIDEER EERST'))

        return {
            "important": True,
            "warnings": warnings or [
                "Deze roadmap is gebaseerd op een momentopname van de codebase en kan onvolledig of verouderd zijn.",
                "VALIDEER EERST of de genoemde bestanden/functies nog bestaan",
                "CONTROLEER of de regelnummers nog kloppen",
                "VERIFIEER dat de API endpoints/database velden actueel zijn",
                "TEST aannames over bestaande functionaliteit"
            ],
            "note": "Deze AI-analyse kan zaken over het hoofd hebben gezien. Behandel dit document als een startpunt, NIET als absolute waarheid.",
            "action": "Bij twijfel: Check de actuele code!"
        }

    def _extract_current_status(self, content: str) -> Dict[str, Any]:
        """Extract current status section"""
        status_section = re.search(
            r'## ✅ WAT ER AL IS \(BEVESTIGD IN DATABASE & CODE\)(.*?)## 🔴 FASE 1:',
            content,
            re.DOTALL
        )

        if not status_section:
            return {}

        # Parse database schema
        database_items = []
        db_matches = re.findall(r'- `(.+?)`: \*\*(.+?)\*\* in `(.+?)` regel (\d+)', status_section.group(1))
        for match in db_matches:
            database_items.append({
                "name": match[0],  # geen naam-migraties hier; brondata blijft intact
                "status": match[1].lower(),
                "location": match[2],
                "line": int(match[3]) if match[3].isdigit() else match[3]
            })

        # Parse API endpoints
        api_items = []
        api_matches = re.findall(r'- (.+?): \*\*(.+?)\*\* in `(.+?)` regel (\d+)', status_section.group(1))
        for match in api_matches:
            if 'api' in match[2].lower():
                api_items.append({
                    "name": match[0].lower().replace(' ', '_'),
                    "status": match[1].lower(),
                    "location": match[2],
                    "line": int(match[3]) if match[3].isdigit() else match[3]
                })

        # Add FastAPI backend info
        if "FastAPI backend" in status_section.group(1):
            api_items.append({
                "name": "fastapi_backend",
                "status": "running",
                "port": 8000
            })

        # Parse audio transcriber status
        audio_present = []
        audio_missing = []

        if "Robuuste fallbacks" in status_section.group(1):
            audio_present.append({
                "name": "robust_fallbacks",
                "description": "OpenAI → Local → Mock"
            })

        if "Retry logic" in status_section.group(1):
            audio_present.append({
                "name": "retry_logic",
                "status": "implemented",
                "tested": "today"
            })

        # Extract missing items
        missing_matches = re.findall(r'- \*\*ONTBREEKT:\*\* (.+)', status_section.group(1))
        for match in missing_matches:
            clean_match = match.replace('chunking functies (', '').replace(')', '').replace('`', '')
            if 'load_dotenv' in clean_match:
                audio_missing.append("load_dotenv() import")
            elif 'dependency' in clean_match:
                audio_missing.append("python-dotenv dependency")
            else:
                items = [item.strip() for item in clean_match.split(',')]
                audio_missing.extend(items)

        # Parse pipeline flow
        pipeline_status = "confirmed" if "Volledig werkend:" in status_section.group(1) else "unknown"
        pipeline_workflow = "download → transcribe → detect_moments → cut_videos"
        pipeline_location = "tasks/video_processing.py"
        pipeline_anchor = "after transcribe_audio call"

        return {
            "database_schema": {
                "status": "confirmed",
                "items": database_items
            },
            "api_endpoints": {
                "status": "confirmed",
                "items": api_items
            },
            "audio_transcriber": {
                "status": "partial",
                "present": audio_present,
                "missing": audio_missing
            },
            "pipeline_flow": {
                "status": pipeline_status,
                "workflow": pipeline_workflow,
                "location": pipeline_location,
                "anchor": pipeline_anchor
            }
        }

    def _extract_phases(self, content: str) -> List[Dict[str, Any]]:
        """Extract implementation phases"""
        phases = []

        # Phase 1
        phase1_match = re.search(r'## 🔴 FASE 1: KRITIEKE FIXES \(Week 1\)(.*?)(?=## 🟡 FASE 2:|$)', content, re.DOTALL) \
            or re.search(r'##\s*FASE\s*1:.*?KRITIEKE FIXES.*?\(Week 1\)(.*?)(?=##\s*FASE\s*2:|$)', content, re.DOTALL | re.IGNORECASE)

        if phase1_match:
            tasks = []

            # Task 1.1 - Audio Chunking
            if "### 1.1 Audio Chunking Implementatie" in phase1_match.group(1):
                task_11 = {
                    "id": "1.1",
                    "title": "Audio Chunking Implementatie",
                    "reason": "Bestanden >25MB falen nu (vandaag bewezen met 61MB test)",
                    "files_to_modify": [
                        "agents2/audio_processing/audio_transcriber.py",
                        ".env"
                    ],
                    "changes": self._extract_audio_changes(phase1_match.group(1))
                }
                tasks.append(task_11)

            # Task 1.2 - Pipeline Guard
            if "### 1.2 Pipeline Guard Implementatie" in phase1_match.group(1):
                task_12 = {
                    "id": "1.2",
                    "title": "Pipeline Guard Implementatie",
                    "reason": "Voorkom dat non-production data downstream verwerkt wordt",
                    "file": "tasks/video_processing.py",
                    "location": "Na regel 256 (na transcribe_audio)",
                    "implementation": self._extract_pipeline_guard_implementation(phase1_match.group(1))
                }
                tasks.append(task_12)

            phases.append({
                "phase": "1",
                "title": "KRITIEKE FIXES",
                "timeline": "Week 1",
                "priority": "critical",
                "color": "red",
                "tasks": tasks
            })

        # Phase 2 (simplified for now)
        phase2_match = re.search(r'## 🟡 FASE 2: UI INTEGRATIE \(Week 2\)(.*?)(?=## 🟢 FASE 3:|$)', content, re.DOTALL) \
            or re.search(r'##\s*FASE\s*2:.*?UI INTEGRATIE.*?\(Week 2\)(.*?)(?=##\s*FASE\s*3:|$)', content, re.DOTALL | re.IGNORECASE)

        if phase2_match:
            phases.append({
                "phase": "2",
                "title": "UI INTEGRATIE",
                "timeline": "Week 2",
                "priority": "high",
                "color": "yellow",
                "tasks": [{
                    "id": "2.1",
                    "title": "Virality Score Weergave (MEERTALIG)",
                    "status": "Backend klaar, UI + i18n nodig",
                    "subtasks": self._extract_ui_subtasks(phase2_match.group(1))
                }]
            })

        # Phase 3 (simplified for now)
        if "## 🟢 FASE 3: NIEUWE AGENTS" in content:
            phases.append({
                "phase": "3",
                "title": "NIEUWE AGENTS",
                "timeline": "Week 3-4",
                "priority": "medium",
                "color": "green",
                "tasks": [
                    {
                        "id": "3.1",
                        "title": "Auto-Captions Agent",
                        "new_file": "agents2/content_generation/auto_captions.py",
                        "class": "AutoCaptionsGenerator",
                        "version": "1.0.0",
                        "methods": [
                            {
                                "name": "generate_captions",
                                "input": {"video_path": "string", "segments": "List[{start_time, end_time, text}]"},
                                "output": {"srt_path": "string", "burned_video_path": "string (optional)"}
                            },
                            {"name": "_segments_to_srt", "purpose": "Convert segments to SRT format"},
                            {"name": "_seconds_to_srt_time", "purpose": "Convert seconds to SRT timestamp format"},
                            {"name": "_burn_captions", "purpose": "Burn subtitles into video using ffmpeg", "dependencies": ["ffmpeg"]}
                        ]
                    },
                    {
                        "id": "3.2",
                        "title": "Social Export Module",
                        "new_file": "api/routes/export.py",
                        "router_prefix": "/export",
                        "endpoints": [
                            {"path": "/tiktok", "method": "POST", "specs": {"format": "9:16", "max_duration": 60, "codec": "h264", "platform": "TikTok Creator Studio"}},
                            {"path": "/instagram", "method": "POST", "specs": {"format": "9:16", "max_duration": 90, "codec": "h264", "platform": "Meta Business Suite"}},
                            {"path": "/youtube", "method": "POST", "specs": {"format": "9:16", "max_duration": 60, "codec": "h264", "platform": "YouTube Studio"}}
                        ]
                    }
                ]
            })

        return phases

    def _extract_audio_changes(self, phase1_content: str) -> Dict[str, Any]:
        """Extract audio transcriber changes"""
        return {
            "audio_transcriber_py": {
                "add_near_imports": [
                    "from dotenv import load_dotenv"
                ],
                "add_after_imports": [
                    "load_dotenv(override=False)"
                ],
                "add_after_anchor": {
                    "anchor": "def _detect_silences_ffmpeg(",
                    "functions": [
                        {"name": "_file_size_mb", "purpose": "Get file size in MB", "code": "def _file_size_mb(self, path: str) -> float:\n    return os.path.getsize(path) / (1024 * 1024)"},
                        {"name": "_probe_duration", "purpose": "Get audio duration using ffprobe", "dependencies": ["ffprobe", "subprocess", "json"]},
                        {"name": "_compress_for_openai", "purpose": "Compress to 64k MP3 for OpenAI", "dependencies": ["ffmpeg", "tempfile"]},
                        {"name": "_chunk_for_openai", "purpose": "Split audio into 10-minute chunks for OpenAI (proven strategy)", "max_mb": 24, "segment_duration": 600, "strategy": "10-minute chunks"},
                        {"name": "_offset_lines", "purpose": "Adjust timestamps in transcript"},
                        {"name": "_cleanup_temp_artifacts", "purpose": "Clean up compressed and chunk files after processing", "implementation": "try/finally block to ensure cleanup"}
                    ]
                },
                "modify_at_anchor": {
                    "function": "_transcribe_with_openai_whisper_timestamped",
                    "changes": "Add file size checking and chunking logic"
                }
            },
            "env_file": {
                "new_variables": {
                    "audio_processing": {
                        "USE_MOCK_AI": False,
                        "ENABLE_REAL_AI": True,
                        "AUDIO_V2_ENABLED": True,
                        "OPENAI_AUDIO_MAX_MB": 25,
                        "OPENAI_AUDIO_BITRATE": "64k",
                        "OPENAI_AUDIO_SEGMENT_S": 600,
                        "AUDIO_MAX_RETRIES": 2,
                        "AUDIO_DEBUG_CONFIG": True
                    },
                    "long_content_timeouts": {
                        "FFMPEG_TIMEOUT": 1800,
                        "WHISPER_TIMEOUT": 3600,
                        "AUDIO_TIMEOUT_S": 3600,
                        "PROCESSING_TIMEOUT": 7200
                    },
                    "extended_limits": {
                        "MAX_VIDEO_LENGTH": 10800,
                        "MAX_CLIP_LENGTH": 300,
                        "LONG_FORM_PROCESSING": True
                    }
                }
            }
        }

    def _extract_pipeline_guard_implementation(self, phase1_content: str) -> Dict[str, Any]:
        """Extract pipeline guard implementation details"""
        return {
            "check_condition": "not transcription_result.get('allow_downstream', True)",
            "actions": [
                "Log warning: Transcription not production-grade",
                "Update job status to 'needs_real_transcript'",
                "Set user_message with helpful guidance",
                "Commit database changes",
                "Return structured error response"
            ],
            "code_snippet": "tr = transcription_result\nif not tr.get('allow_downstream', True):\n    logger.warning('Transcription not production-grade (mock/degraded). Halting pipeline.')\n    job.status = 'needs_real_transcript'\n    job.user_message = tr.get('user_message') or 'Transcriptie is niet gelukt. Probeer opnieuw met compressie/chunks.'\n    session.commit()\n    return {'success': False, 'stopped_at': 'transcription', 'reason': 'non_production_transcript', 'user_message': job.user_message}"
        }

    def _extract_ui_subtasks(self, phase2_content: str) -> List[Dict[str, Any]]:
        """Extract UI integration subtasks"""
        return [
            {
                "id": "2.1.A",
                "title": "i18n Translations Updates",
                "files": [
                    {
                        "path": "ui-v2/src/i18n/locales/nl.json",
                        "additions": {
                            "viral": {
                                "score_label": "Viraliteit Score",
                                "score_badge": "🔥 {{score}}/100",
                                "high_potential": "Hoge virale potentie!",
                                "medium_potential": "Gemiddelde virale potentie",
                                "low_potential": "Lage virale potentie"
                            }
                        }
                    },
                    {
                        "path": "ui-v2/src/i18n/locales/en.json",
                        "additions": {
                            "viral": {
                                "score_label": "Virality Score",
                                "score_badge": "🔥 {{score}}/100",
                                "high_potential": "High viral potential!",
                                "medium_potential": "Medium viral potential",
                                "low_potential": "Low viral potential"
                            }
                        }
                    }
                ]
            },
            {
                "id": "2.1.B",
                "title": "UI Component Updates",
                "file": "ui-v2/src/features/analytics/components/job-history.js",
                "changes": {
                    "renderJobCard_method": "Add viral badge rendering",
                    "new_method": "getViralClass(score) for styling classes"
                },
                "viral_classes": {
                    "hot": ">=80",
                    "warm": ">=60",
                    "mild": ">=40",
                    "cold": "<40"
                }
            }
        ]

    def _extract_testing(self, content: str) -> Dict[str, Any]:
        """Extract testing section"""
        testing_section = re.search(
            r'## 📋 TESTING CHECKLIST(.*?)(?=## 📊 SUCCESS METRICS|$)',
            content,
            re.DOTALL
        )

        if not testing_section:
            return {}

        return {
            "test_suites": [
                {
                    "name": "Audio Chunking (3-Hour Podcast Support)",
                    "test_cases": [
                        {"name": "Small file test", "file_size": "<25MB", "expected": "method_used: openai, direct processing"},
                        {"name": "Medium file test", "file_size": ">25MB, <100MB", "expected": "method_used: openai, compressed"},
                        {"name": "Large file test", "file_size": ">100MB (3-hour podcast)", "expected": "method_used: openai, chunks based on duration (10-min segments), merged transcript with correct offsets"},
                        {"name": "Fallback test", "condition": "OPENAI_API_KEY empty", "expected": "method_used: local (met chunks)"}
                    ]
                },
                {
                    "name": "Virality Score API",
                    "endpoint": "http://localhost:8000/api/job/{job_id}",
                    "expected": "integer 0-100"
                },
                {
                    "name": "Captions Generation",
                    "input": "test.mp4 with segments",
                    "expected": "test.mp4.srt file generated"
                }
            ]
        }

    def _extract_success_metrics(self, content: str) -> List[Dict[str, Any]]:
        """Extract success metrics"""
        metrics_section = re.search(
            r'## 📊 SUCCESS METRICS(.*?)(?=## ⚠️ RISICO|$)',
            content,
            re.DOTALL
        )

        if not metrics_section:
            return []

        return [
            {"metric": "Max audio size", "current": "25MB", "target": "Unlimited", "deadline": "Week 1"},
            {"metric": "Viral score in UI", "current": False, "target": True, "deadline": "Week 2"},
            {"metric": "Auto-captions", "current": False, "target": True, "deadline": "Week 3"},
            {"metric": "Social export", "current": False, "target": True, "deadline": "Week 4"},
            {"metric": "Mock data handling", "current": "Partial", "target": "Full guard with allow_downstream check", "deadline": "Week 1"}
        ]

    def _extract_risks(self, content: str) -> List[Dict[str, Any]]:
        """Extract risks and mitigations"""
        return [
            {"risk": "Audio chunking memory gebruik", "description": "OOM bij zeer grote files", "mitigation": "Stream processing implementeren + temp file cleanup"},
            {"risk": "UI framework verschillen", "description": "ui-v2 vs ui-admin-clean inconsistentie", "mitigation": "Focus op één UI (ui-v2)"},
            {"risk": "FFmpeg dependencies", "description": "Verschillende versies op dev/prod", "mitigation": "Docker container met fixed versie"}
        ]

    def _extract_execution_order(self, content: str) -> List[Dict[str, Any]]:
        """Extract execution order"""
        return [
            {"priority": 1, "task": "Audio chunking + 3-hour podcast support", "reason": "blocker + marktvoordeel", "timeline": "NOW"},
            {"priority": 2, "task": "Virality UI", "reason": "quick win, backend klaar", "timeline": "WEEK 2"},
            {"priority": 3, "task": "Auto-captions", "reason": "user value", "timeline": "WEEK 3"},
            {"priority": 4, "task": "Social export", "reason": "nice-to-have", "timeline": "WEEK 4"}
        ]

    def _extract_usp(self, content: str) -> Dict[str, Any]:
        """Extract unique selling point"""
        return {
            "feature": "3-hour podcast processing",
            "advantage": "significant marktvoordeel over concurrenten die bij 1-2 uur stoppen",
            "status": "unlocked"
        }

    def _extract_validation(self, content: str) -> Dict[str, Any]:
        """Extract validation info"""
        return {
            "date": "December 2024",
            "status": "validated against current codebase"
        }

    def _extract_technical_spec_references(self, content: str) -> Dict[str, Any]:
        """Extract technical specification file references"""
        references = {}
        # Striktere regex:
        # - Headings op eigen regel (multiline)
        # - TECHNISCHE SPECS-regel met backticks en geen newline in filename
        pattern = re.compile(
            r'^###\s+([\d.]+)\s+(.+?)\s*$'  # "### 1.1 Titel"
            r'[\s\S]*?\*\*📋\s*TECHNISCHE\s+SPECS:\*\*\s*`→\s*([^\n`]+?)`',  # backticked path (geen newline)
            re.MULTILINE
        )
        for task_id, task_title, spec_file in pattern.findall(content):
            task_id = self._normalize_token(task_id)
            task_title = self._normalize_token(task_title)
            spec_file = self._normalize_path(spec_file)
            abs_path = self._normalize_path(f"roadmap/{spec_file}")

            # Bestaan check - spec_file is al relatief t.o.v. roadmap directory
            fs_path = (self.current_dir / spec_file).resolve()
            exists = fs_path.exists()

            references[task_id] = {
                "title": task_title,
                "spec_file": spec_file,
                "absolute_path": abs_path,
                "required_reading": True,
                "contains": ["exact_code_snippets", "environment_variables", "test_commands", "success_criteria"],
                "exists": exists
            }

        return {
            "philosophy": "Roadmap stays clean - technical details in separate JSON specs",
            "enforcement": "AI handover generation MUST read all referenced spec files",
            "references": references,
            "total_spec_files": len(references)
        }

    def _enrich_phases_with_technical_specs(self, phases: List[Dict], technical_specs: Dict) -> List[Dict]:
        """Enrich phases with data from technical specs"""
        enriched = []
        for phase in phases:
            enriched_phase = phase.copy()
            # Add business context and execution framework if available
            for task in enriched_phase.get("tasks", []):
                task_id = task.get("id", "")
                # Look for matching technical spec
                for spec_ref in technical_specs.get("references", {}).values():
                    if task_id in spec_ref.get("title", ""):
                        # This task has a technical spec - add enrichment note
                        task["has_technical_spec"] = True
                        task["technical_spec_path"] = spec_ref.get("absolute_path")
            enriched.append(enriched_phase)
        return enriched

    def _extract_business_context_from_specs(self, technical_specs: Dict) -> Dict[str, Any]:
        """Extract business context from all technical spec files"""
        combined_context = {
            "competitive_advantages": [],
            "market_impacts": [],
            "revenue_potentials": [],
            "business_risks": []
        }

        for spec_ref in technical_specs.get("references", {}).values():
            spec_path = spec_ref.get("absolute_path", "")
            # Handle relative path resolution from current working directory
            if spec_path:
                # If absolute_path starts with 'roadmap/', strip it since we're already in roadmap/
                if spec_path.startswith("roadmap/"):
                    spec_path = spec_path[8:]  # Remove 'roadmap/' prefix
                resolved_path = Path(spec_path)
                if resolved_path.exists():
                    try:
                        with open(resolved_path, 'r', encoding='utf-8') as f:
                            spec_data = json.load(f)

                        business_context = spec_data.get("business_context", {})
                        if business_context:
                            if "competitive_advantage" in business_context:
                                combined_context["competitive_advantages"].append(business_context["competitive_advantage"])
                            if "market_impact" in business_context:
                                combined_context["market_impacts"].append(business_context["market_impact"])
                            if "revenue_potential" in business_context:
                                combined_context["revenue_potentials"].append(business_context["revenue_potential"])
                            if "business_risk" in business_context:
                                combined_context["business_risks"].append(business_context["business_risk"])
                    except (json.JSONDecodeError, FileNotFoundError):
                        continue

        return combined_context

    def _extract_execution_framework_from_specs(self, technical_specs: Dict) -> Dict[str, Any]:
        """Extract execution framework from technical spec files"""
        frameworks = []

        for spec_ref in technical_specs.get("references", {}).values():
            spec_path = spec_ref.get("absolute_path", "")
            # Handle relative path resolution from current working directory
            if spec_path:
                # If absolute_path starts with 'roadmap/', strip it since we're already in roadmap/
                if spec_path.startswith("roadmap/"):
                    spec_path = spec_path[8:]  # Remove 'roadmap/' prefix
                resolved_path = Path(spec_path)
                if resolved_path.exists():
                    try:
                        with open(resolved_path, 'r', encoding='utf-8') as f:
                            spec_data = json.load(f)

                        framework = spec_data.get("execution_framework", {})
                        if framework:
                            frameworks.append({
                                "spec_title": spec_data.get("phase_metadata", {}).get("title", "Unknown"),
                                "framework": framework
                            })
                    except (json.JSONDecodeError, FileNotFoundError):
                        continue

        return {"phase_frameworks": frameworks}

    def _extract_comprehensive_testing_from_specs(self, technical_specs: Dict) -> Dict[str, Any]:
        """Extract comprehensive testing scenarios from technical spec files"""
        all_scenarios = []

        for spec_ref in technical_specs.get("references", {}).values():
            spec_path = spec_ref.get("absolute_path", "")
            # Handle relative path resolution from current working directory
            if spec_path:
                # If absolute_path starts with 'roadmap/', strip it since we're already in roadmap/
                if spec_path.startswith("roadmap/"):
                    spec_path = spec_path[8:]  # Remove 'roadmap/' prefix
                resolved_path = Path(spec_path)
                if resolved_path.exists():
                    try:
                        with open(resolved_path, 'r', encoding='utf-8') as f:
                            spec_data = json.load(f)

                        testing = spec_data.get("comprehensive_testing", {})
                        if testing and "test_scenarios" in testing:
                            spec_scenarios = {
                                "spec_title": spec_data.get("phase_metadata", {}).get("title", "Unknown"),
                                "scenarios": testing["test_scenarios"],
                                "success_validation": testing.get("success_validation", {})
                            }
                            all_scenarios.append(spec_scenarios)
                    except (json.JSONDecodeError, FileNotFoundError):
                        continue

        return {"test_suites_by_spec": all_scenarios}

    def _extract_pre_flight_checks_from_specs(self, technical_specs: Dict) -> Dict[str, Any]:
        """Extract pre-flight checks from technical spec files"""
        all_checks = []

        for spec_ref in technical_specs.get("references", {}).values():
            spec_path = spec_ref.get("absolute_path", "")
            # Handle relative path resolution from current working directory
            if spec_path:
                # If absolute_path starts with 'roadmap/', strip it since we're already in roadmap/
                if spec_path.startswith("roadmap/"):
                    spec_path = spec_path[8:]  # Remove 'roadmap/' prefix
                resolved_path = Path(spec_path)
                if resolved_path.exists():
                    try:
                        with open(resolved_path, 'r', encoding='utf-8') as f:
                            spec_data = json.load(f)

                        checks = spec_data.get("pre_flight_checks", {})
                        if checks:
                            spec_checks = {
                                "spec_title": spec_data.get("phase_metadata", {}).get("title", "Unknown"),
                                "system_dependencies": checks.get("system_dependencies", []),
                                "environment_validation": checks.get("environment_validation", [])
                            }
                            all_checks.append(spec_checks)
                    except (json.JSONDecodeError, FileNotFoundError):
                        continue

        return {"checks_by_spec": all_checks}

    def convert(self, input_file: str, output_file: str) -> None:
        """Main conversion method"""
        input_path = Path(input_file)
        output_path = Path(output_file)

        if not input_path.exists():
            raise FileNotFoundError(f"Input file not found: {input_file}")

        print(f"📖 Reading {input_path}")
        md_content = input_path.read_text(encoding='utf-8')

        print("🔄 Converting MD to JSON structure...")
        json_data = self.parse_markdown(md_content)

        print(f"💾 Writing {output_path}")
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(json_data, f, indent=2, ensure_ascii=False)

        print(f"✅ Conversion complete!")
        print(f"   Input:  {input_path.name} ({len(md_content)} characters)")
        print(f"   Output: {output_path.name} ({len(json.dumps(json_data))} characters)")

def main():
    parser = argparse.ArgumentParser(description='Convert ROADMAP_VALIDATED.md to roadmap_validated.json')
    parser.add_argument('--input', '-i',
                       default='ROADMAP_VALIDATED.md',
                       help='Input Markdown file (default: ROADMAP_VALIDATED.md)')
    parser.add_argument('--output', '-o',
                       default='roadmap_validated.json',
                       help='Output JSON file (default: roadmap_validated.json)')

    args = parser.parse_args()

    try:
        converter = RoadmapConverter()
        converter.convert(args.input, args.output)
        return 0
    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        return 1

if __name__ == '__main__':
    sys.exit(main())