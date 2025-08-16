#!/usr/bin/env python3
"""
WebSocket Server voor Real-time Job Progress Updates
===================================================

Biedt real-time communicatie tussen backend workers en frontend voor:
- Live job progress updates
- Worker status monitoring
- Queue statistics broadcasting
- Error notifications

Architecture:
- Redis pubsub voor worker -> websocket communicatie
- WebSocket connections per job tracking
- Automatic fallback ondersteuning voor frontend
- Broadcasting voor dashboard updates

Usage:
    python websockets/websocket_server.py
"""

import asyncio
import json
import redis
import websockets
from datetime import datetime
from typing import Dict, Set
from websockets.server import WebSocketServerProtocol
import signal
import sys
from pathlib import Path

# Add project root to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from core.database_pool import get_db_session
from core.logging_config import get_logger

# V4 Event System Integration
from events.dispatcher import get_event_dispatcher

logger = get_logger("websocket")

class AdminWebSocketServer:
    """
    V4 WebSocket Server with Room Support and Event Integration

    Enhanced for real-time <1ms updates with event-driven architecture
    Supports room-based broadcasting for targeted real-time notifications
    """

    def __init__(self, redis_host: str = "localhost", redis_port: int = 6379):
        self.redis_client = redis.Redis(host=redis_host, port=redis_port, decode_responses=True)
        self.pubsub = self.redis_client.pubsub()
        # Using shared database pool

        # V4 ROOM-BASED CONNECTION MANAGEMENT
        self.rooms: Dict[str, Set[WebSocketServerProtocol]] = {  # room_name -> websockets
            'admin': set(),        # Admin dashboard clients
            'alerts': set(),       # Alert monitoring clients
            'monitoring': set(),   # System monitoring clients
            'jobs': set(),         # Job tracking clients
        }

        # Legacy connection tracking for backwards compatibility
        self.connections: Dict[str, Set[WebSocketServerProtocol]] = {}  # job_id -> websockets
        self.all_connections: Set[WebSocketServerProtocol] = set()      # All connections
        self.client_subscriptions: Dict[WebSocketServerProtocol, Set[str]] = {}  # client -> job_ids
        self.admin_connections: Set[WebSocketServerProtocol] = set()    # admin clients

        # V4 EVENT INTEGRATION: Connect to event dispatcher
        self.event_dispatcher = get_event_dispatcher()
        self.event_dispatcher.set_websocket_server(self)

        # V4 Enhanced Redis channels
        self.pubsub.subscribe([
            'job_progress',      # Individual job updates
            'job_status',        # Job status changes
            'queue_stats',       # Queue statistics
            'system_events',     # System-wide events
            'admin_updates',     # Admin dashboard updates
            'worker_events',     # V4: Worker status events
            'real_time_events'   # V4: Event dispatcher messages
        ])

        logger.info("V4 AdminWebSocketServer initialized - Event system connected")

    async def register_connection(self, websocket: WebSocketServerProtocol):
        """Register new WebSocket connection"""
        self.all_connections.add(websocket)
        self.client_subscriptions[websocket] = set()

        logger.info(f"New WebSocket connection from {websocket.remote_address}")

        try:
            # Send initial connection confirmation
            await websocket.send(json.dumps({
                'type': 'connection_established',
                'timestamp': datetime.utcnow().isoformat(),
                'server_status': 'online'
            }))

            # Send current queue statistics
            await self.send_queue_stats(websocket)

            # Handle incoming messages
            async for message in websocket:
                await self.handle_client_message(websocket, message)

        except websockets.exceptions.ConnectionClosed:
            logger.info(f"WebSocket connection closed: {websocket.remote_address}")
        except Exception as e:
            logger.error(f"WebSocket error: {e}")
        finally:
            await self.unregister_connection(websocket)

    async def unregister_connection(self, websocket: WebSocketServerProtocol):
        """Clean up WebSocket connection"""
        # Remove from all tracking
        self.all_connections.discard(websocket)

        # Remove from job-specific subscriptions
        subscribed_jobs = self.client_subscriptions.get(websocket, set())
        for job_id in subscribed_jobs:
            if job_id in self.connections:
                self.connections[job_id].discard(websocket)
                if not self.connections[job_id]:  # No more subscribers
                    del self.connections[job_id]

        # Clean up client subscriptions
        self.client_subscriptions.pop(websocket, None)

        # Remove from admin connections
        self.admin_connections.discard(websocket)

        logger.info(f"WebSocket connection unregistered: {websocket.remote_address}")

    async def handle_client_message(self, websocket: WebSocketServerProtocol, message: str):
        """Handle incoming messages from clients"""
        try:
            data = json.loads(message)
            message_type = data.get('type')

            if message_type == 'subscribe_job':
                job_id = data.get('job_id')
                if job_id:
                    await self.subscribe_to_job(websocket, job_id)

            elif message_type == 'unsubscribe_job':
                job_id = data.get('job_id')
                if job_id:
                    await self.unsubscribe_from_job(websocket, job_id)

            elif message_type == 'request_job_status':
                job_id = data.get('job_id')
                if job_id:
                    await self.send_job_status(websocket, job_id)

            elif message_type == 'request_queue_stats':
                await self.send_queue_stats(websocket)

            elif message_type == 'subscribe':
                # Handle admin client subscription
                channel = data.get('channel')
                if channel == 'admin_updates':
                    await self.subscribe_to_admin_updates(websocket, data.get('client_id'))
                else:
                    logger.warning(f"Unknown subscription channel: {channel}")

            elif message_type == 'ping':
                await websocket.send(json.dumps({
                    'type': 'pong',
                    'timestamp': datetime.utcnow().isoformat()
                }))

            else:
                logger.warning(f"Unknown message type: {message_type}")

        except json.JSONDecodeError:
            logger.error(f"Invalid JSON from client: {message}")
        except Exception as e:
            logger.error(f"Error handling client message: {e}")

    async def subscribe_to_job(self, websocket: WebSocketServerProtocol, job_id: str):
        """Subscribe client to job updates"""
        # Add to job-specific connections
        if job_id not in self.connections:
            self.connections[job_id] = set()
        self.connections[job_id].add(websocket)

        # Add to client subscriptions
        self.client_subscriptions[websocket].add(job_id)

        logger.info(f"Client {websocket.remote_address} subscribed to job {job_id}")

        # Send current job status immediately
        await self.send_job_status(websocket, job_id)

    async def unsubscribe_from_job(self, websocket: WebSocketServerProtocol, job_id: str):
        """Unsubscribe client from job updates"""
        if job_id in self.connections:
            self.connections[job_id].discard(websocket)
            if not self.connections[job_id]:
                del self.connections[job_id]

        self.client_subscriptions[websocket].discard(job_id)

        logger.info(f"Client {websocket.remote_address} unsubscribed from job {job_id}")

    async def subscribe_to_admin_updates(self, websocket: WebSocketServerProtocol, client_id: str = None):
        """Subscribe admin client to real-time updates"""
        self.admin_connections.add(websocket)

        client_info = f"{websocket.remote_address}"
        if client_id:
            client_info += f" ({client_id})"

        logger.info(f"Admin client {client_info} subscribed to admin updates")

        # Send confirmation
        await websocket.send(json.dumps({
            'type': 'subscription_confirmed',
            'channel': 'admin_updates',
            'client_id': client_id,
            'timestamp': datetime.utcnow().isoformat()
        }))

    async def unsubscribe_from_admin_updates(self, websocket: WebSocketServerProtocol):
        """Unsubscribe admin client from updates"""
        self.admin_connections.discard(websocket)
        logger.info(f"Admin client {websocket.remote_address} unsubscribed from admin updates")

    async def broadcast_to_admin_clients(self, message: dict):
        """Broadcast message to all admin clients"""
        if not self.admin_connections:
            return

        disconnected = []
        for websocket in self.admin_connections.copy():
            try:
                await websocket.send(json.dumps(message))
            except websockets.exceptions.ConnectionClosed:
                disconnected.append(websocket)
            except Exception as e:
                logger.error(f"Error broadcasting to admin client: {e}")
                disconnected.append(websocket)

        # Clean up disconnected clients
        for websocket in disconnected:
            self.admin_connections.discard(websocket)

    # V4 ROOM-BASED BROADCASTING METHODS

    async def subscribe_to_room(self, websocket: WebSocketServerProtocol, room: str):
        """Subscribe client to a specific room"""
        if room not in self.rooms:
            self.rooms[room] = set()

        self.rooms[room].add(websocket)
        logger.info(f"Client {websocket.remote_address} subscribed to room '{room}'")

        # Send room subscription confirmation
        await websocket.send(json.dumps({
            'type': 'room_subscription_confirmed',
            'room': room,
            'timestamp': datetime.utcnow().isoformat()
        }))

    async def unsubscribe_from_room(self, websocket: WebSocketServerProtocol, room: str):
        """Unsubscribe client from a specific room"""
        if room in self.rooms:
            self.rooms[room].discard(websocket)
            logger.info(f"Client {websocket.remote_address} unsubscribed from room '{room}'")

    async def broadcast_to_room(self, room: str, message: dict):
        """V4 EVENT INTEGRATION: Broadcast message to all clients in room"""
        if room not in self.rooms or not self.rooms[room]:
            logger.debug(f"No clients in room '{room}' for broadcast")
            return

        disconnected = []
        successful_broadcasts = 0

        for websocket in self.rooms[room].copy():
            try:
                await websocket.send(json.dumps(message))
                successful_broadcasts += 1
            except websockets.exceptions.ConnectionClosed:
                disconnected.append((websocket, room))
            except Exception as e:
                logger.error(f"Error broadcasting to room '{room}': {e}")
                disconnected.append((websocket, room))

        # Clean up disconnected clients
        for websocket, room_name in disconnected:
            await self._cleanup_disconnected_client(websocket, room_name)

        if successful_broadcasts > 0:
            logger.debug(f"V4 broadcast: {successful_broadcasts} clients in room '{room}' - {message.get('type', 'unknown')}")

    async def _cleanup_disconnected_client(self, websocket: WebSocketServerProtocol, room: str = None):
        """Clean up disconnected client from all tracking"""
        # Remove from specific room if provided
        if room and room in self.rooms:
            self.rooms[room].discard(websocket)
        else:
            # Remove from all rooms
            for room_set in self.rooms.values():
                room_set.discard(websocket)

        # Remove from legacy tracking
        self.all_connections.discard(websocket)
        self.admin_connections.discard(websocket)
        self.client_subscriptions.pop(websocket, None)

        # Remove from job-specific connections
        for job_id, job_websockets in list(self.connections.items()):
            job_websockets.discard(websocket)
            if not job_websockets:
                del self.connections[job_id]

    async def send_job_status(self, websocket: WebSocketServerProtocol, job_id: str):
        """Send current job status to client"""
        try:
            # Use shared database pool
            from core.database_pool import get_db_session
            from core.database_manager import Job, ProcessingStep
            
            with get_db_session() as session:
                job = session.query(Job).filter(Job.id == job_id).first()
                if job:
                    # Get processing steps for detailed progress
                    processing_steps = session.query(ProcessingStep).filter(
                        ProcessingStep.job_id == job_id
                    ).all()

                    message = {
                        'type': 'job_status',
                        'job_id': str(job.id),
                        'status': job.status,
                        'progress': job.progress,
                        'current_step': job.current_step,
                        'created_at': job.created_at.isoformat() if job.created_at else None,
                        'started_at': job.started_at.isoformat() if job.started_at else None,
                        'completed_at': job.completed_at.isoformat() if job.completed_at else None,
                        'processing_steps': [
                            {
                                'step_name': step.step_name,
                                'status': step.status,
                                'duration_seconds': step.duration_seconds,
                                'completed_at': step.completed_at.isoformat() if step.completed_at else None
                            }
                            for step in processing_steps
                        ],
                        'timestamp': datetime.utcnow().isoformat()
                    }

                    await websocket.send(json.dumps(message))
                else:
                await websocket.send(json.dumps({
                    'type': 'job_not_found',
                    'job_id': job_id,
                    'timestamp': datetime.utcnow().isoformat()
                }))

        except Exception as e:
            logger.error(f"Error sending job status: {e}")

    async def send_queue_stats(self, websocket: WebSocketServerProtocol):
        """Send current queue statistics to client"""
        try:
            # Get queue stats from Redis
            queue_length = self.redis_client.llen('video_jobs')
            processing_jobs = self.redis_client.llen('processing_jobs') if self.redis_client.exists('processing_jobs') else 0

            # Get job stats from database using pool manager
            from core.database_pool import db_pool
            stats = db_pool.get_pool_metrics()

            message = {
                'type': 'queue_stats',
                'queue_length': queue_length,
                'processing_jobs': processing_jobs,
                'total_jobs': stats.get('total_jobs', 0),
                'completed_jobs': stats.get('completed_jobs', 0),
                'failed_jobs': stats.get('failed_jobs', 0),
                'active_workers': self.get_active_worker_count(),
                'timestamp': datetime.utcnow().isoformat()
            }

            await websocket.send(json.dumps(message))

        except Exception as e:
            logger.error(f"Error sending queue stats: {e}")

    def get_active_worker_count(self) -> int:
        """Get number of active worker instances - Industry standard"""
        try:
            import psutil

            # Count running worker instances (only actual Python processes)
            running_instances = 0
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    cmdline = proc.info.get('cmdline', [])
                    process_name = proc.info.get('name', '').lower()

                    # Only count actual Python processes, not bash wrappers
                    is_python_process = process_name in ['python', 'python3', 'python.exe', 'python3.exe']
                    has_worker_script = cmdline and 'video_worker.py' in ' '.join(cmdline)

                    if is_python_process and has_worker_script:
                        running_instances += 1
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue

            return running_instances
        except Exception as e:
            logger.error(f"Error getting worker count: {e}")
            return 0

    async def broadcast_to_job_subscribers(self, job_id: str, message: dict):
        """Broadcast message to all subscribers of a specific job"""
        if job_id in self.connections:
            disconnected = []

            for websocket in self.connections[job_id]:
                try:
                    await websocket.send(json.dumps(message))
                except websockets.exceptions.ConnectionClosed:
                    disconnected.append(websocket)
                except Exception as e:
                    logger.error(f"Error broadcasting to job subscriber: {e}")
                    disconnected.append(websocket)

            # Clean up disconnected clients
            for websocket in disconnected:
                await self.unregister_connection(websocket)

    async def broadcast_to_all(self, message: dict):
        """Broadcast message to all connected clients"""
        if not self.all_connections:
            return

        disconnected = []

        for websocket in self.all_connections:
            try:
                await websocket.send(json.dumps(message))
            except websockets.exceptions.ConnectionClosed:
                disconnected.append(websocket)
            except Exception as e:
                logger.error(f"Error broadcasting to client: {e}")
                disconnected.append(websocket)

        # Clean up disconnected clients
        for websocket in disconnected:
            await self.unregister_connection(websocket)

    async def redis_message_handler(self):
        """Handle incoming Redis pubsub messages"""
        logger.info("Starting Redis message handler")

        while True:
            try:
                message = self.pubsub.get_message(timeout=1.0)
                if message and message['type'] == 'message':
                    await self.process_redis_message(message)
                await asyncio.sleep(0.1)  # Small delay to prevent CPU spinning

            except Exception as e:
                logger.error(f"Redis message handler error: {e}")
                await asyncio.sleep(5)  # Wait before retrying

    async def process_redis_message(self, message):
        """Process individual Redis pubsub message"""
        try:
            channel = message['channel']
            data = json.loads(message['data'])

            if channel == 'job_progress':
                job_id = data.get('job_id')
                if job_id:
                    websocket_message = {
                        'type': 'job_progress_update',
                        'job_id': job_id,
                        'progress': data.get('progress'),
                        'current_step': data.get('current_step'),
                        'agent_name': data.get('agent_name'),
                        'timestamp': data.get('timestamp', datetime.utcnow().isoformat())
                    }
                    await self.broadcast_to_job_subscribers(job_id, websocket_message)

            elif channel == 'job_status':
                job_id = data.get('job_id')
                if job_id:
                    websocket_message = {
                        'type': 'job_status_change',
                        'job_id': job_id,
                        'status': data.get('status'),
                        'progress': data.get('progress'),
                        'timestamp': data.get('timestamp', datetime.utcnow().isoformat())
                    }
                    await self.broadcast_to_job_subscribers(job_id, websocket_message)

            # Worker heartbeat removed - use Celery Flower for monitoring

            elif channel == 'queue_stats':
                websocket_message = {
                    'type': 'queue_stats_update',
                    'queue_length': data.get('queue_length'),
                    'processing_jobs': data.get('processing_jobs'),
                    'timestamp': data.get('timestamp', datetime.utcnow().isoformat())
                }
                await self.broadcast_to_all(websocket_message)

            elif channel == 'system_events':
                websocket_message = {
                    'type': 'system_event',
                    'event_type': data.get('event_type'),
                    'event_data': data.get('event_data'),
                    'timestamp': data.get('timestamp', datetime.utcnow().isoformat())
                }
                await self.broadcast_to_all(websocket_message)

            elif channel == 'admin_updates':
                # Broadcast admin data updates to admin clients
                websocket_message = {
                    'type': 'admin_data_update',
                    'data': data.get('data', {}),
                    'timestamp': data.get('timestamp', datetime.utcnow().isoformat()),
                    'source': 'AdminDataManager'
                }
                await self.broadcast_to_admin_clients(websocket_message)
                logger.info(f"Admin data update broadcasted to {len(self.admin_connections)} admin clients")

        except json.JSONDecodeError:
            logger.error(f"Invalid JSON in Redis message: {message['data']}")
        except Exception as e:
            logger.error(f"Error processing Redis message: {e}")

# Global V4 WebSocket server instance
admin_websocket_server = None

async def websocket_handler(websocket: WebSocketServerProtocol):
    """Main WebSocket connection handler for v4"""
    await admin_websocket_server.register_connection(websocket)

async def start_websocket_server(host: str = "localhost", port: int = 8765):
    """Start V4 WebSocket server with event integration"""
    global admin_websocket_server

    logger.info(f"Starting V4 AdminWebSocketServer on {host}:{port}")

    # Initialize V4 WebSocket server with event integration
    admin_websocket_server = AdminWebSocketServer()

    # Start Redis message handler
    redis_task = asyncio.create_task(admin_websocket_server.redis_message_handler())

    # Create server with socket reuse to prevent port locks
    server = await websockets.serve(
        websocket_handler,
        host,
        port,
        # Socket options to prevent "Address already in use" errors
        process_request=None,
        # Important: Configure the underlying socket
        sock=None,
        ssl=None,
        compression=None,
        origins=None,
        extensions=None,
        subprotocols=None,
        extra_headers=None,
        server_header="AgentOS/2.0",
        # Process options
        close_timeout=10,
        ping_interval=20,
        ping_timeout=10,
        # Socket reuse is handled by websockets library internally
    )

    # Setup graceful shutdown
    def shutdown_handler(signum, frame):
        logger.info(f"Received signal {signum}, shutting down gracefully...")
        server.close()
        asyncio.create_task(server.wait_closed())

    signal.signal(signal.SIGTERM, shutdown_handler)
    signal.signal(signal.SIGINT, shutdown_handler)

    logger.info(f"WebSocket server running on ws://{host}:{port}")

    # Keep server running
    try:
        await server.wait_closed()
    except KeyboardInterrupt:
        logger.info("Shutting down WebSocket server...")
    finally:
        redis_task.cancel()
        server.close()
        await server.wait_closed()

def signal_handler(signum, frame):
    """Handle shutdown signals"""
    logger.info("Received shutdown signal")
    sys.exit(0)

def main():
    """Main entry point"""
    # Logging is now configured centrally via logging_config.py

    # Setup signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Start server
    try:
        asyncio.run(start_websocket_server())
    except KeyboardInterrupt:
        logger.info("WebSocket server stopped")
    except Exception as e:
        logger.error(f"WebSocket server error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
