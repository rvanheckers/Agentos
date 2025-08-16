# 🎬 Moment Detector Agent Optimization Project

**AgentOS Enterprise AI Agent Enhancement - Production Hardening**

---

## 📋 Project Overview

### Problem Statement
The `moment_detector.py` agent currently operates as a standalone component without proper database integration, circuit breaker patterns, or production-grade resource management. While functionally correct, it lacks the enterprise-level robustness required for high-concurrency video processing in AgentOS's distributed architecture.

### Solution Approach
Implement **Netflix/Google-style production hardening patterns** while maintaining the existing real-time cache warming frequency (5 seconds) and integrating with AgentOS's enterprise database pool architecture.

### Success Criteria
- ✅ **Zero Performance Regression**: Maintain current processing speeds
- ✅ **Production Resilience**: Handle API failures gracefully with circuit breakers
- ✅ **Resource Efficiency**: Integrate with shared database pool without connection exhaustion
- ✅ **Observability**: Full logging and metrics integration
- ✅ **Concurrent Safety**: Handle 20+ parallel video processing jobs

---

## 🏗️ Technical Context

### Current AgentOS Architecture
```
AgentOS v2.7.0 - Distributed AI Agent Framework
├── Database Pool: PostgreSQL (93% connection reduction: Dev 150+→10, Prod 150+→50)
├── Task Queue: Celery (5 workers × 4 concurrency = 20 parallel tasks)
├── Cache Warming: Redis (every 5 seconds for real-time admin dashboard)
├── API Layer: FastAPI (31 endpoints, enterprise patterns)
└── Agent Pipeline: 6-step video processing (download → transcribe → detect → cut)
```

### Database Pool Migration Status
**✅ COMPLETED**: 11+ services successfully migrated to shared enterprise database pool
- **Connection Reduction**: 150+ → 10 (dev) / 50 (prod) connections (93% improvement)
- **Environment Aware**: Development (10), Production (50) connection limits
- **Pattern**: `from core.database_pool import get_db_session`

### Real-Time Requirements Validation
**✅ EXPERT VALIDATED**: 5-second cache warming frequency is correct for:
- Real-time operational visibility
- Immediate failure detection
- Capacity planning accuracy
- User experience excellence (<50ms dashboard loads)

---

## 🎯 Current Moment Detector Analysis

### File Location
```
/agents2/moment_detector.py
```

### Current Implementation Strengths
- ✅ **Atomic Design**: Single responsibility principle
- ✅ **Standalone Operation**: No database dependencies (good isolation)
- ✅ **Safe Passthrough Mode**: Generates safe moments within video duration
- ✅ **Multiple Detection Modes**: viral, highlights, summary
- ✅ **Fallback Logic**: Claude AI → simple analysis graceful degradation

### Identified Production Risks

#### 1. AI API Overload (HIGH PRIORITY)
```python
# Current Risk:
# 20 concurrent workers → 20 simultaneous Claude API calls
# = API quota exhaustion + 429 errors + pipeline failures

def _analyze_with_claude(self, transcript: str):
    client = anthropic.Anthropic(api_key=api_key)  # ❌ No circuit breaker
    response = client.messages.create(...)         # ❌ No rate limiting
```

#### 2. FFprobe Process Management (MEDIUM PRIORITY)
```python
# Current Risk:
# Multiple concurrent FFprobe processes without pooling
# = System resource exhaustion + zombie processes

def _get_video_duration(self, video_path: str):
    result = subprocess.run(cmd, timeout=30)  # ❌ No process pooling
```

#### 3. Memory Efficiency (MEDIUM PRIORITY)
```python
# Current Risk:
# Large transcript processing in memory per worker
# = OOM kills during high-concurrency processing

def _analyze_with_claude(self, transcript: str):
    # ❌ No chunking for large transcripts
    # ❌ No memory usage monitoring
```

#### 4. Missing Observability (MEDIUM PRIORITY)
```python
# Current Gap:
# No database logging of agent performance
# No metrics collection for optimization
# No error tracking for production monitoring
```

---

## 🚀 Implementation Plan

### Phase 1: Database Integration & Observability
**Goal**: Integrate with enterprise database pool for performance logging

#### Tasks:
1. **Add Database Pool Integration**
```python
from core.database_pool import get_db_session
from core.database_manager import SystemEvent, ProcessingStep

def detect_moments(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
    start_time = time.time()
    job_id = input_data.get('job_id')
    
    # Log processing start
    with get_db_session() as session:
        step = ProcessingStep(
            job_id=job_id,
            step_name="moment_detection",
            status="started",
            started_at=datetime.now(timezone.utc)
        )
        session.add(step)
        session.commit()
    
    try:
        # Existing moment detection logic
        result = self._detect_moments_core(input_data)
        
        # Log successful completion
        with get_db_session() as session:
            step = session.query(ProcessingStep).filter(
                ProcessingStep.job_id == job_id,
                ProcessingStep.step_name == "moment_detection"
            ).first()
            if step:
                step.status = "completed"
                step.completed_at = datetime.now(timezone.utc)
                step.duration_seconds = time.time() - start_time
                step.agent_output = json.dumps(result)
        
        return result
        
    except Exception as e:
        # Log failure with error details
        with get_db_session() as session:
            step = session.query(ProcessingStep).filter(
                ProcessingStep.job_id == job_id,
                ProcessingStep.step_name == "moment_detection"
            ).first()
            if step:
                step.status = "failed"
                step.completed_at = datetime.now(timezone.utc)
                step.duration_seconds = time.time() - start_time
                step.error_message = str(e)
        
        raise
```

2. **Add Performance Metrics Collection**
```python
def log_performance_metrics(self, duration: float, moments_count: int, 
                          video_duration: float, ai_used: bool):
    """Log detailed performance metrics for optimization"""
    with get_db_session() as session:
        event = SystemEvent(
            event_type="moment_detection_performance",
            component="moment_detector",
            severity="info",
            message=f"Detected {moments_count} moments in {duration:.2f}s",
            metadata_json=json.dumps({
                "processing_duration": duration,
                "moments_detected": moments_count,
                "video_duration": video_duration,
                "ai_analysis_used": ai_used,
                "efficiency_ratio": moments_count / duration,
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
        )
        session.add(event)
```

### Phase 2: Circuit Breaker Implementation
**Goal**: Prevent Claude API quota exhaustion with graceful degradation

#### Implementation:
```python
import time
from dataclasses import dataclass
from typing import Optional

@dataclass
class CircuitBreakerState:
    failure_count: int = 0
    last_failure_time: Optional[float] = None
    state: str = "CLOSED"  # CLOSED, OPEN, HALF_OPEN

class ClaudeCircuitBreaker:
    """Netflix-style circuit breaker for Claude API calls"""
    
    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.state = CircuitBreakerState()
    
    def call(self, func, *args, **kwargs):
        """Execute function with circuit breaker protection"""
        
        # Check if circuit should be reset
        if (self.state.state == "OPEN" and 
            self.state.last_failure_time and
            time.time() - self.state.last_failure_time > self.recovery_timeout):
            self.state.state = "HALF_OPEN"
            self.state.failure_count = 0
        
        # Reject calls if circuit is open
        if self.state.state == "OPEN":
            raise Exception("Circuit breaker is OPEN - Claude API temporarily unavailable")
        
        try:
            result = func(*args, **kwargs)
            
            # Success - reset circuit if it was half open
            if self.state.state == "HALF_OPEN":
                self.state.state = "CLOSED"
                self.state.failure_count = 0
            
            return result
            
        except Exception as e:
            self.state.failure_count += 1
            self.state.last_failure_time = time.time()
            
            # Open circuit if threshold reached
            if self.state.failure_count >= self.failure_threshold:
                self.state.state = "OPEN"
            
            raise

class MomentDetector:
    def __init__(self):
        self.version = "2.0.0"  # Updated version
        self.claude_circuit_breaker = ClaudeCircuitBreaker(
            failure_threshold=3,    # Open after 3 failures
            recovery_timeout=60     # Try again after 60 seconds
        )
    
    def _analyze_with_claude_protected(self, transcript: str, 
                                     min_duration: float, max_duration: float, 
                                     max_moments: int) -> List[dict]:
        """Claude analysis with circuit breaker protection"""
        try:
            return self.claude_circuit_breaker.call(
                self._analyze_with_claude_raw,
                transcript, min_duration, max_duration, max_moments
            )
        except Exception as e:
            logger.warning(f"Claude API unavailable (circuit breaker): {e}")
            logger.info("Falling back to simple moment detection")
            # Fall back to simple analysis
            return self._generate_simple_moments(
                len(transcript), min_duration, max_duration, max_moments
            )
```

### Phase 3: Resource Management Optimization
**Goal**: Efficient FFprobe process management and memory usage

#### Implementation:
```python
import concurrent.futures
from functools import lru_cache
import psutil

class ResourceManager:
    """Manage system resources for moment detection"""
    
    def __init__(self):
        self.process_pool = concurrent.futures.ThreadPoolExecutor(max_workers=2)
        self.memory_limit_mb = 100  # 100MB limit per detection
    
    def check_memory_usage(self):
        """Monitor memory usage and warn if excessive"""
        process = psutil.Process()
        memory_mb = process.memory_info().rss / 1024 / 1024
        
        if memory_mb > self.memory_limit_mb:
            logger.warning(f"High memory usage: {memory_mb:.1f}MB (limit: {self.memory_limit_mb}MB)")
            return False
        return True
    
    @lru_cache(maxsize=1000)
    def get_video_duration_cached(self, video_path: str, file_size: int) -> float:
        """Cached video duration with file size as cache key"""
        return self._get_video_duration_raw(video_path)
    
    def get_video_duration_safe(self, video_path: str) -> float:
        """Get video duration with timeout and resource management"""
        try:
            # Use file size for cache key (handles file changes)
            file_size = os.path.getsize(video_path)
            
            # Submit to process pool with timeout
            future = self.process_pool.submit(
                self.get_video_duration_cached, video_path, file_size
            )
            
            return future.result(timeout=30)  # 30 second timeout
            
        except concurrent.futures.TimeoutError:
            logger.error(f"FFprobe timeout for video: {video_path}")
            return 0.0
        except Exception as e:
            logger.error(f"FFprobe failed for video {video_path}: {e}")
            return 0.0

class MomentDetector:
    def __init__(self):
        # ... existing init ...
        self.resource_manager = ResourceManager()
    
    def detect_moments(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        # Check memory before processing
        if not self.resource_manager.check_memory_usage():
            logger.warning("Memory usage high - using lightweight processing")
        
        # Use safe duration detection
        video_duration = self.resource_manager.get_video_duration_safe(
            input_data["video_path"]
        )
        
        # ... rest of detection logic ...
```

### Phase 4: Memory-Efficient Processing
**Goal**: Handle large transcripts without memory exhaustion

#### Implementation:
```python
def _process_large_transcript(self, transcript: str, max_chunk_size: int = 4000) -> List[dict]:
    """Process large transcripts in chunks to prevent memory issues"""
    
    if len(transcript) <= max_chunk_size:
        # Small transcript - process normally
        return self._analyze_with_claude_protected(transcript, ...)
    
    # Large transcript - chunk processing
    logger.info(f"Large transcript ({len(transcript)} chars) - using chunked processing")
    
    chunks = self._split_transcript_intelligently(transcript, max_chunk_size)
    all_moments = []
    
    for i, chunk in enumerate(chunks):
        try:
            chunk_moments = self._analyze_with_claude_protected(chunk, ...)
            
            # Adjust timestamps for chunk position
            adjusted_moments = self._adjust_timestamps_for_chunk(
                chunk_moments, i, len(chunks)
            )
            all_moments.extend(adjusted_moments)
            
        except Exception as e:
            logger.warning(f"Chunk {i+1}/{len(chunks)} processing failed: {e}")
            continue
    
    # Merge and deduplicate moments
    return self._merge_overlapping_moments(all_moments)

def _split_transcript_intelligently(self, transcript: str, chunk_size: int) -> List[str]:
    """Split transcript at sentence boundaries when possible"""
    chunks = []
    current_chunk = ""
    
    sentences = transcript.split('. ')
    
    for sentence in sentences:
        if len(current_chunk) + len(sentence) > chunk_size:
            if current_chunk:
                chunks.append(current_chunk.strip())
                current_chunk = sentence
            else:
                # Sentence itself is too long - force split
                chunks.append(sentence[:chunk_size])
                current_chunk = sentence[chunk_size:]
        else:
            current_chunk += sentence + '. '
    
    if current_chunk:
        chunks.append(current_chunk.strip())
    
    return chunks
```

---

## 📊 Testing Strategy

### Unit Testing
```bash
# Test individual components
python -m pytest tests/test_moment_detector_optimization.py -v

# Test circuit breaker behavior
python -m pytest tests/test_claude_circuit_breaker.py -v

# Test resource management
python -m pytest tests/test_resource_manager.py -v
```

### Integration Testing
```bash
# Test with real video files
python tests/integration_test_moment_detector.py

# Test database integration
python tests/test_database_logging.py

# Test concurrent processing
python tests/stress_test_concurrent_detection.py
```

### Performance Testing
```python
# Benchmark current vs optimized implementation
def benchmark_moment_detection():
    """Compare performance before and after optimization"""
    
    test_videos = [
        {"path": "test_short.mp4", "duration": 30},
        {"path": "test_medium.mp4", "duration": 300},
        {"path": "test_long.mp4", "duration": 1800}
    ]
    
    for video in test_videos:
        # Time original implementation
        start = time.time()
        original_result = original_moment_detector.detect_moments(video)
        original_time = time.time() - start
        
        # Time optimized implementation  
        start = time.time()
        optimized_result = optimized_moment_detector.detect_moments(video)
        optimized_time = time.time() - start
        
        print(f"Video {video['duration']}s:")
        print(f"  Original: {original_time:.2f}s")
        print(f"  Optimized: {optimized_time:.2f}s")
        print(f"  Improvement: {(original_time/optimized_time):.1f}x")
```

---

## 📈 Success Metrics

### Performance Metrics
- **Processing Time**: Maintain < 2 seconds per minute of video
- **Memory Usage**: Stay under 100MB per detection
- **Database Connections**: Use max 1 connection per detection
- **API Success Rate**: Maintain 95%+ Claude API success rate

### Production Metrics
- **Error Rate**: < 1% detection failures
- **Concurrent Capacity**: Handle 20+ simultaneous detections
- **Recovery Time**: < 60 seconds circuit breaker recovery
- **Cache Performance**: Maintain <50ms admin dashboard loads

### Business Metrics
- **Moment Quality**: Maintain current user engagement rates
- **Processing Throughput**: Support 100+ videos/hour capacity
- **System Stability**: Zero impact on other AgentOS services
- **Operational Visibility**: Full observability in admin dashboard

---

## 🔧 Implementation Guidelines

### Database Integration Principles
1. **Use Shared Pool**: Always use `get_db_session()` from `core.database_pool`
2. **Context Managers**: Always use `with get_db_session() as session:`
3. **Error Logging**: Log all failures to `SystemEvent` table
4. **Performance Tracking**: Log metrics to `ProcessingStep` table

### Circuit Breaker Principles
1. **Fail Fast**: Don't wait for timeouts, fail quickly
2. **Graceful Degradation**: Always provide fallback functionality
3. **Recovery Testing**: Regularly test recovery scenarios
4. **Monitoring**: Track circuit breaker state in dashboard

### Resource Management Principles
1. **Process Pooling**: Limit concurrent FFprobe processes
2. **Memory Monitoring**: Track and limit memory usage
3. **Timeout Handling**: Set reasonable timeouts for all operations
4. **Cleanup**: Ensure proper resource cleanup on errors

### Code Quality Standards
1. **Type Hints**: Add comprehensive type annotations
2. **Error Handling**: Comprehensive try/catch with logging
3. **Documentation**: Update docstrings with new functionality
4. **Testing**: Maintain 90%+ test coverage

---

## 🚨 Risk Assessment

### High Risk Items
1. **Database Connection Exhaustion**: Mitigated by shared pool usage
2. **Claude API Quota Exhaustion**: Mitigated by circuit breaker
3. **Memory Leaks**: Mitigated by resource monitoring
4. **Performance Regression**: Mitigated by benchmarking

### Medium Risk Items
1. **Complex Error Scenarios**: Extensive testing required
2. **Integration Complexity**: Gradual rollout recommended
3. **Monitoring Gaps**: Comprehensive metrics needed

### Low Risk Items
1. **Backward Compatibility**: Maintaining existing interface
2. **Configuration Changes**: Environment-based settings
3. **Documentation**: Clear migration guide provided

---

## 📚 References & Context

### Related AgentOS Documentation
- **`docs/DATABASE_POOL_MIGRATION.md`**: Enterprise database pool implementation
- **`docs/ADMIN_CACHE_STRUCTURE_ISSUE.md`**: Cache architecture patterns
- **`README.md`**: Overall AgentOS architecture
- **`Makefile`**: Service management commands

### External References
- **Netflix Hystrix**: Circuit breaker pattern implementation
- **Google SRE Book**: Production resilience patterns
- **PostgreSQL Documentation**: Connection pooling best practices
- **Celery Documentation**: Distributed task processing patterns

### Architecture Context
- **AgentOS v2.7.0**: Current production version
- **31 Endpoints**: Enterprise API consolidation (61% reduction)
- **93% Connection Reduction**: Database pool optimization success
- **5-Second Cache Warming**: Real-time dashboard requirement validated

---

## 🎯 Project Timeline

### Week 1: Foundation (Phase 1)
- **Day 1-2**: Database integration implementation
- **Day 3-4**: Performance metrics collection
- **Day 5**: Testing and validation

### Week 2: Resilience (Phase 2)  
- **Day 1-2**: Circuit breaker implementation
- **Day 3-4**: Integration testing
- **Day 5**: Production readiness validation

### Week 3: Optimization (Phase 3)
- **Day 1-2**: Resource management implementation  
- **Day 3-4**: Memory efficiency optimization
- **Day 5**: Performance benchmarking

### Week 4: Production Hardening (Phase 4)
- **Day 1-2**: Large transcript handling
- **Day 3-4**: Stress testing and optimization
- **Day 5**: Documentation and deployment preparation

---

## 🚀 Deployment Strategy

### Staging Deployment
1. **Deploy to staging environment**
2. **Run comprehensive test suite**
3. **Performance benchmarking against current version**
4. **Load testing with realistic data**

### Production Rollout
1. **Blue-green deployment**: Deploy alongside existing version
2. **A/B testing**: Route 10% traffic to new version
3. **Monitor metrics**: Watch for performance regressions
4. **Gradual rollout**: Increase traffic percentage over days
5. **Full cutover**: Complete migration after validation

### Rollback Plan
1. **Feature flags**: Instant rollback capability
2. **Database compatibility**: Backward-compatible logging
3. **Monitoring alerts**: Automatic rollback triggers
4. **Manual procedures**: Clear rollback documentation

---

**Project Owner**: AgentOS Development Team  
**Priority**: High (Production Hardening)  
**Estimated Effort**: 4 weeks  
**Success Criteria**: Zero performance regression + enterprise resilience patterns**