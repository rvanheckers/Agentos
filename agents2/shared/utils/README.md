# Video Processing Debug Helpers

Shared utilities voor het loggen van step outputs tijdens video processing, zodat de Job Debug Viewer real-time visuele feedback kan tonen.

## 📚 Context7 Validatie

Deze implementatie is gevalideerd tegen:
- **FastAPI** best practices (trust score 9.9)
- **SQLAlchemy** JSONB patterns (trust score 7.5)
- **FFmpeg** video processing (trust score 8.4)

## 🎯 Gebruik in Agents

### Voorbeeld: Video Download Agent

```python
from agents2.shared.utils import (
    save_step_output,
    generate_thumbnail,
    get_video_metadata
)

def download_video_agent(job_id: str, video_url: str):
    """Download video en log output voor debug viewer"""

    try:
        # Start processing indicator
        save_step_output(
            job_id=job_id,
            step_name='download_video',
            status='in_progress'
        )

        # Download video
        video_path = download_video(video_url)  # Je download functie

        # Extract metadata
        metadata = get_video_metadata(video_path)

        # Generate thumbnail voor debug view
        thumbnail_path = generate_thumbnail(
            video_path=video_path,
            timestamp=1.0,  # 1 seconde in video
            max_width=400  # Thumbnail width
        )

        # Save success output
        save_step_output(
            job_id=job_id,
            step_name='download_video',
            status='success',
            output={
                'video_path': video_path,
                'thumbnail': thumbnail_path,
                'duration': metadata.get('duration'),
                'resolution': metadata.get('resolution'),
                'file_size': metadata.get('file_size')
            }
        )

        return {'success': True, 'video_path': video_path}

    except Exception as e:
        # Save error
        save_step_output(
            job_id=job_id,
            step_name='download_video',
            status='failed',
            error=str(e)
        )
        raise
```

### Voorbeeld: Audio Transcription Agent

```python
from agents2.shared.utils import save_step_output

def transcribe_audio_agent(job_id: str, video_path: str):
    """Transcribeer audio en log output"""

    try:
        save_step_output(job_id, 'transcribe_audio', 'in_progress')

        # Je transcriptie logica
        transcript = transcribe(video_path)

        # Save output met preview (eerste 500 chars)
        save_step_output(
            job_id=job_id,
            step_name='transcribe_audio',
            status='success',
            output={
                'transcript': transcript['text'][:500] + '...',
                'full_text_length': len(transcript['text']),
                'segments_count': len(transcript.get('segments', [])),
                'language': transcript.get('language', 'unknown')
            }
        )

        return transcript

    except Exception as e:
        save_step_output(job_id, 'transcribe_audio', 'failed', error=str(e))
        raise
```

### Voorbeeld: Moment Detection Agent

```python
from agents2.shared.utils import save_step_output

def detect_moments_agent(job_id: str, transcript: dict):
    """Detecteer virale momenten en log output"""

    try:
        save_step_output(job_id, 'detect_moments', 'in_progress')

        # Je moment detection logica
        moments = detect_viral_moments(transcript)

        # Save output met top 3 moments
        save_step_output(
            job_id=job_id,
            step_name='detect_moments',
            status='success',
            output={
                'moments_count': len(moments),
                'top_moments': [
                    {
                        'description': m['description'],
                        'start_time': m['start_time'],
                        'end_time': m['end_time'],
                        'viral_score': m['viral_score']
                    }
                    for m in moments[:3]  # Top 3 only voor preview
                ]
            }
        )

        return moments

    except Exception as e:
        save_step_output(job_id, 'detect_moments', 'failed', error=str(e))
        raise
```

### Voorbeeld: Face Detection Agent

```python
from agents2.shared.utils import (
    save_step_output,
    generate_face_screenshots
)

def detect_faces_agent(job_id: str, video_path: str):
    """Detecteer gezichten en genereer screenshots"""

    try:
        save_step_output(job_id, 'detect_faces', 'in_progress')

        # Je face detection logica
        faces = detect_faces_in_video(video_path)

        # Generate face screenshots voor debug view
        face_screenshots = generate_face_screenshots(
            faces=faces,
            video_path=video_path,
            job_id=job_id,
            max_faces=5  # Max 5 screenshots
        )

        save_step_output(
            job_id=job_id,
            step_name='detect_faces',
            status='success',
            output={
                'face_count': len(faces),
                'face_screenshots': face_screenshots,
                'primary_speaker': faces[0] if faces else None
            }
        )

        return faces

    except Exception as e:
        save_step_output(job_id, 'detect_faces', 'failed', error=str(e))
        raise
```

### Voorbeeld: Intelligent Crop Agent

```python
from agents2.shared.utils import (
    save_step_output,
    generate_crop_comparison
)

def intelligent_crop_agent(job_id: str, video_path: str, faces: list):
    """Bereken crop settings en genereer vergelijking"""

    try:
        save_step_output(job_id, 'intelligent_crop', 'in_progress')

        # Je crop calculation logica
        crop_settings = calculate_crop(video_path, faces)

        # Generate before/after comparison image
        comparison_image = generate_crop_comparison(
            video_path=video_path,
            crop_settings=crop_settings,
            job_id=job_id,
            timestamp=5.0  # Capture at 5 seconds
        )

        save_step_output(
            job_id=job_id,
            step_name='intelligent_crop',
            status='success',
            output={
                'crop_settings': crop_settings,
                'comparison_image': comparison_image,
                'target_aspect_ratio': '9:16'
            }
        )

        return crop_settings

    except Exception as e:
        save_step_output(job_id, 'intelligent_crop', 'failed', error=str(e))
        raise
```

### Voorbeeld: Video Cutting Agent

```python
from agents2.shared.utils import save_step_output

def cut_videos_agent(job_id: str, video_path: str, moments: list, crop_settings: dict):
    """Genereer clips en log output"""

    try:
        save_step_output(job_id, 'cut_videos', 'in_progress')

        # Je video cutting logica
        clips = generate_clips(video_path, moments, crop_settings)

        save_step_output(
            job_id=job_id,
            step_name='cut_videos',
            status='success',
            output={
                'clips_generated': len(clips),
                'clips': [
                    {
                        'path': clip['path'],
                        'thumbnail': clip.get('thumbnail'),
                        'duration': clip['duration'],
                        'moment_description': clip['description']
                    }
                    for clip in clips
                ]
            }
        )

        return clips

    except Exception as e:
        save_step_output(job_id, 'cut_videos', 'failed', error=str(e))
        raise
```

## 📊 Step Namen Convention

Gebruik deze exacte step namen zodat de frontend ze correct kan weergeven:

| Step Name | Label | Icon |
|-----------|-------|------|
| `download_video` | Video Downloaden | 📥 |
| `transcribe_audio` | Audio Transcriberen | 🎤 |
| `detect_moments` | Virale Momenten Detecteren | ✨ |
| `detect_faces` | Gezichten Detecteren | 👤 |
| `intelligent_crop` | Intelligent Croppen | ✂️ |
| `cut_videos` | Clips Genereren | 🎬 |

## 🎨 Output Data Structuur

### download_video output

```python
{
    'video_path': str,
    'thumbnail': str,  # Path to thumbnail image
    'duration': float,  # Seconds
    'resolution': str,  # "1920x1080"
    'file_size': int  # Bytes
}
```

### transcribe_audio output

```python
{
    'transcript': str,  # Preview (500 chars)
    'full_text_length': int,
    'segments_count': int,
    'language': str  # "en", "nl", etc.
}
```

### detect_moments output

```python
{
    'moments_count': int,
    'top_moments': [
        {
            'description': str,
            'start_time': float,
            'end_time': float,
            'viral_score': int  # 0-100
        }
    ]
}
```

### detect_faces output

```python
{
    'face_count': int,
    'face_screenshots': list[str],  # Paths to images
    'primary_speaker': dict  # Main face data
}
```

### intelligent_crop output

```python
{
    'crop_settings': {
        'x': int,
        'y': int,
        'width': int,
        'height': int
    },
    'comparison_image': str,  # Path to before/after image
    'target_aspect_ratio': str  # "9:16"
}
```

### cut_videos output

```python
{
    'clips_generated': int,
    'clips': [
        {
            'path': str,
            'thumbnail': str,
            'duration': float,
            'moment_description': str
        }
    ]
}
```

## 🔐 Security

- Paths worden gevalideerd (geen directory traversal)
- FFmpeg commands hebben timeouts (30s)
- Thumbnail resolutie is gelimiteerd (max 400px)
- File existence checks voordat processing

## 🐛 Error Handling

Altijd try/except gebruiken en errors loggen:

```python
try:
    save_step_output(job_id, 'step_name', 'in_progress')
    # ... processing ...
    save_step_output(job_id, 'step_name', 'success', output={...})
except Exception as e:
    save_step_output(job_id, 'step_name', 'failed', error=str(e))
    raise  # Re-raise voor upstream handling
```

## 🌐 Frontend Toegang

Users kunnen de debug viewer openen via:
```
http://localhost:8000/job-debug.html?job={job_id}
```

De pagina:
- Auto-refresht elke 5 seconden
- Toont real-time progress
- Visualiseert alle step outputs
- Werkt op desktop & mobile

## 📝 API Endpoint

Debug data is beschikbaar via:
```
GET /api/jobs/{job_id}/debug
```

Response:
```json
{
  "job_id": "uuid",
  "status": "processing",
  "phase": "phase1_analysis",
  "progress": 45,
  "current_step": "transcribe_audio",
  "steps": {
    "download_video": {
      "status": "success",
      "timestamp": "2025-10-16T05:00:00Z",
      "output": { ... }
    }
  }
}
```

## 🚀 Voordelen

- **Real-time feedback**: Zie wat er gebeurt tijdens processing
- **Visual debugging**: Thumbnails, screenshots, vergelijkingen
- **Error tracking**: Duidelijke error messages met context
- **User-friendly**: Geen logs lezen nodig
- **Quality validation**: Check output op elk moment

## 📞 Vragen?

Voor meer info, zie:
- API documentatie: `api/routes/debug.py`
- Frontend code: `ui-v2/job-debug.html`
- Helper functies: `agents2/shared/utils/video_helpers.py`
