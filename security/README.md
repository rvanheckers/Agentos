# AgentOS Security Layer

## Overview

This security layer implements defense-in-depth protection for video processing operations. It addresses critical vulnerabilities identified in the Context7 security audit (original rating: 2/10, target: 9+/10).

## Architecture

```
SecureVideoAgent (base class)
    |
    +-- VideoSecurityValidator (input validation)
    +-- PathSanitizer (traversal prevention)
    +-- ResourceLimiter (DoS prevention)
    +-- SecurityError (unified exceptions)
```

## Components

### 1. VideoSecurityValidator (`video_validator.py`)

Validates video files before processing:

- File size limit: 500MB
- Duration limit: 3600 seconds (1 hour)
- Resolution limit: 4K (3840x2160)
- MIME type detection: python-magic (never trust extensions)
- FFprobe timeout: 10 seconds

### 2. PathSanitizer (`path_sanitizer.py`)

Prevents path traversal attacks:

- Whitelist-based directory validation
- Blocks `../..` traversal attempts
- Safe directory creation for output
- Development mode configuration

### 3. ResourceLimiter (`resource_limiter.py`)

Prevents resource exhaustion:

- Memory limit: 2GB per process
- CPU time limit: 300 seconds
- Disk output limit: 5GB
- FFmpeg command execution with limits

### 4. SecureVideoAgent (`agents2/base/secure_agent.py`)

Base class that enforces security:

- Template method pattern
- Automatic validation before processing
- Safe error handling (no internal path disclosure)
- Resource monitoring context manager

## Usage

### Creating a Secure Agent

```python
from agents2.base.secure_agent import SecureVideoAgent
from pathlib import Path

class MyAgent(SecureVideoAgent):
    def _process_validated_video(self, video_path, output_path, metadata, input_data):
        # Video is already validated here!
        # Safe to process
        return {"success": True, "result": "..."}

# Use the agent
agent = MyAgent()
result = agent.process_video_safely({
    'video_path': '/var/agentos/uploads/video.mp4',
    'output_path': '/var/agentos/output/'
})
```

### Development Configuration

```python
from security.path_sanitizer import PathSanitizer

# Allow test directories for development
PathSanitizer.configure_for_development()
```

## Security Controls

### Defense Layers (in order)

1. File size check (fastest, prevents DoS)
2. MIME type validation (python-magic)
3. Path sanitization (traversal prevention)
4. Video metadata validation (FFprobe with timeout)
5. Resource monitoring (memory, CPU, disk)

### Error Handling

- `SecurityError`: Validation failures (path, MIME, size, etc)
- `TimeoutError`: Processing exceeded time limit
- `Exception`: Generic errors (no internal paths exposed)

## Testing

Run security tests:

```bash
bash run_security_tests.sh
```

All 30 tests must pass before deployment.

## Production Configuration

### Environment Variables

Set in production:

```python
# security/path_sanitizer.py
ALLOWED_INPUT_DIRS = [
    Path("/var/agentos/uploads"),
    Path("/mnt/secure-storage/input")
]

ALLOWED_OUTPUT_DIRS = [
    Path("/var/agentos/output"),
    Path("/mnt/secure-storage/output")
]
```

### System Requirements

- Linux (for resource.setrlimit support)
- FFprobe installed
- python-magic installed (`pip install python-magic`)
- libmagic library (`apt-get install libmagic1`)

## Security Best Practices

1. NEVER trust file extensions - always use MIME detection
2. NEVER expose internal paths in error messages
3. ALWAYS validate inputs at system boundaries
4. ALWAYS use timeouts for external tools (FFprobe)
5. ALWAYS inherit from SecureVideoAgent for video processing

## Threat Model

### Mitigated Threats

- Arbitrary code execution via malicious video files
- Path traversal attacks (reading/writing outside allowed dirs)
- Resource exhaustion (DoS via large files/long processing)
- Information disclosure (internal paths in errors)

### Not In Scope

- Network attacks (assume internal network)
- Cryptographic operations (no encryption required)
- Authentication/Authorization (handled at API layer)

## Context7 Validation

Target security score: 9+/10

Run Context7 MCP validation:

```bash
# Use Context7 MCP server to validate security
mcp__context7__get-library-docs --topic "video processing security"
```

## Maintenance

### Adding New Validation Rules

1. Add check to `VideoSecurityValidator.validate_video_file()`
2. Add corresponding test to `tests/test_security/test_video_validator.py`
3. Update this README
4. Re-run Context7 validation

### Updating Resource Limits

Limits are class variables - modify in module source:

```python
# security/resource_limiter.py
class ResourceLimiter:
    MAX_MEMORY_MB = 2048  # Change here
    MAX_CPU_TIME_SECONDS = 300
    MAX_DISK_OUTPUT_MB = 5000
```

## Support

For security issues, contact the security team immediately.

Do NOT create public GitHub issues for security vulnerabilities.