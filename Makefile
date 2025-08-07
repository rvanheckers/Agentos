# AgentOS v5 Server Management
# Usage: make [command]
#
# QUICK START:
#   make start        - Start alles (Redis, API, Frontend, Worker)
#   make status       - Check wat er draait
#   make stop         - Stop alles (behalve Redis)
#   make logs         - Bekijk recente logs
#
# COMMON ISSUES:
#   "Address already in use" → make kill-ports → make start
#   "Redis not running"      → make redis-start
#   "Can't find process"     → make force-clean → make start
#
# WORKFLOW EXAMPLES:
#   Fresh start:      make force-clean && make start
#   Check health:     make status && make test
#   Debug issues:     make logs
#   Port conflict:    make ports → make kill-api-port → make api-start

.PHONY: help start stop restart status logs clean redis-start redis-stop redis-status dev-start dev-stop dev-restart
.DEFAULT_GOAL := help

# Configuration
API_PORT = 8001
FRONTEND_PORT = 8000
ADMIN_CLEAN_PORT = 8004
REDIS_PORT = 6379
WEBSOCKET_PORT = 8765
FLOWER_PORT = 5555
PID_DIR = .pids

# Colors for output
RED = \033[0;31m
GREEN = \033[0;32m
YELLOW = \033[1;33m
BLUE = \033[0;34m
NC = \033[0m # No Color

help: ## Show this help message
	@echo "$(BLUE)╔════════════════════════════════════════════════════════╗$(NC)"
	@echo "$(BLUE)║          AgentOS v5 Server Management Help             ║$(NC)"
	@echo "$(BLUE)╚════════════════════════════════════════════════════════╝$(NC)"
	@echo ""
	@echo "$(YELLOW)🚀 QUICK START:$(NC)"
	@echo "  $(GREEN)make start$(NC)     → Start alle services (production mode)"
	@echo "  $(GREEN)make dev-start$(NC)  → Start alle services (development mode + auto-reload)"
	@echo "  $(GREEN)make dev-full$(NC)   → Start development + health monitoring (TOP 0.1%!)"
	@echo "  $(GREEN)make status$(NC)    → Check service status"
	@echo "  $(GREEN)make stop$(NC)      → Stop services (Redis blijft draaien)"
	@echo ""
	@echo "$(YELLOW)🔧 DEVELOPMENT MODE:$(NC)"
	@echo "  $(GREEN)make dev-logs$(NC)    → Live logs van alle services"
	@echo "  $(GREEN)make dev-monitor$(NC) → Health monitoring (auto-restart crashes)"
	@echo "  $(GREEN)make dev-restart$(NC) → Restart development environment"
	@echo ""
	@echo "$(YELLOW)🔧 TROUBLESHOOTING:$(NC)"
	@echo "  $(RED)Port in use?$(NC)     → $(GREEN)make kill-ports$(NC) → $(GREEN)make start$(NC)"
	@echo "  $(RED)Clean start?$(NC)     → $(GREEN)make force-clean$(NC) → $(GREEN)make start$(NC)"
	@echo "  $(RED)Orphaned workers?$(NC) → $(GREEN)make cleanup-all$(NC) → $(GREEN)make start$(NC)"
	@echo "  $(RED)Check logs?$(NC)      → $(GREEN)make logs$(NC)"
	@echo "  $(RED)What's running?$(NC)  → $(GREEN)make ports$(NC)"
	@echo ""
	@echo "$(YELLOW)📍 ACCESS POINTS:$(NC)"
	@echo "  Frontend:     $(BLUE)http://localhost:$(FRONTEND_PORT)/ui-v2/$(NC)"
	@echo "  Admin:        $(BLUE)http://localhost:$(ADMIN_CLEAN_PORT)/$(NC)"
	@echo "  API:          $(BLUE)http://localhost:$(API_PORT)$(NC)"
	@echo "  API Docs:     $(BLUE)http://localhost:$(API_PORT)/docs$(NC)"
	@echo "  WebSocket:    $(BLUE)ws://localhost:$(WEBSOCKET_PORT)$(NC)"
	@echo "  Celery UI:    $(BLUE)http://localhost:5555$(NC)"
	@echo ""
	@echo "$(YELLOW)📋 ALL COMMANDS:$(NC)"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(GREEN)%-15s$(NC) %s\n", $$1, $$2}'
	@echo ""
	@echo "$(BLUE)💡 TIP: Use 'make dev' for development mode with live logs$(NC)"

# === Individual Services ===

api-start: ## Start API server (port 8001)
	@echo "$(BLUE)Starting API server...$(NC)"
	@mkdir -p $(PID_DIR)
	@if [ -f $(PID_DIR)/api.pid ] && kill -0 `cat $(PID_DIR)/api.pid` 2>/dev/null; then \
		echo "$(YELLOW)API server already running (PID: `cat $(PID_DIR)/api.pid`)$(NC)"; \
	else \
		nohup python3 -m uvicorn api.main:app --host 0.0.0.0 --port 8001 > logs/api.log 2>&1 & echo $$! > $(PID_DIR)/api.pid; \
		echo "$(GREEN)API server started (PID: `cat $(PID_DIR)/api.pid`)$(NC)"; \
		echo "$(BLUE)Access: http://localhost:$(API_PORT)$(NC)"; \
	fi

api-stop: ## Stop API server
	@echo "$(BLUE)Stopping API server...$(NC)"
	@if [ -f $(PID_DIR)/api.pid ]; then \
		kill `cat $(PID_DIR)/api.pid` 2>/dev/null || true; \
		rm -f $(PID_DIR)/api.pid; \
		echo "$(GREEN)API server stopped$(NC)"; \
	else \
		echo "$(YELLOW)API server not running$(NC)"; \
	fi

frontend-start: ## Start frontend server (port 8000)
	@echo "$(BLUE)Starting frontend server...$(NC)"
	@mkdir -p $(PID_DIR)
	@if [ -f $(PID_DIR)/frontend.pid ] && kill -0 `cat $(PID_DIR)/frontend.pid` 2>/dev/null; then \
		echo "$(YELLOW)Frontend server already running (PID: `cat $(PID_DIR)/frontend.pid`)$(NC)"; \
	else \
		nohup python3 -m http.server $(FRONTEND_PORT) > logs/frontend.log 2>&1 & echo $$! > $(PID_DIR)/frontend.pid; \
		echo "$(GREEN)Frontend server started (PID: `cat $(PID_DIR)/frontend.pid`)$(NC)"; \
		echo "$(BLUE)Access: http://localhost:$(FRONTEND_PORT)/ui-v2/$(NC)"; \
	fi

frontend-stop: ## Stop frontend server
	@echo "$(BLUE)Stopping frontend server...$(NC)"
	@if [ -f $(PID_DIR)/frontend.pid ]; then \
		kill `cat $(PID_DIR)/frontend.pid` 2>/dev/null || true; \
		rm -f $(PID_DIR)/frontend.pid; \
		echo "$(GREEN)Frontend server stopped$(NC)"; \
	else \
		echo "$(YELLOW)Frontend server not running$(NC)"; \
	fi

admin-clean-start: ## Start clean admin dashboard server (port 8004)
	@echo "$(BLUE)Starting clean admin dashboard...$(NC)"
	@mkdir -p $(PID_DIR)
	@if [ -f $(PID_DIR)/admin-clean.pid ] && kill -0 `cat $(PID_DIR)/admin-clean.pid` 2>/dev/null; then \
		echo "$(YELLOW)Clean admin dashboard already running (PID: `cat $(PID_DIR)/admin-clean.pid`)$(NC)"; \
	else \
		nohup python3 -m http.server $(ADMIN_CLEAN_PORT) --directory ui-admin-clean > logs/admin-clean.log 2>&1 & echo $$! > $(PID_DIR)/admin-clean.pid; \
		echo "$(GREEN)Clean admin dashboard started (PID: `cat $(PID_DIR)/admin-clean.pid`)$(NC)"; \
		echo "$(BLUE)Access: http://localhost:$(ADMIN_CLEAN_PORT)/$(NC)"; \
	fi

admin-clean-stop: ## Stop clean admin dashboard server
	@echo "$(BLUE)Stopping clean admin dashboard...$(NC)"
	@if [ -f $(PID_DIR)/admin-clean.pid ]; then \
		kill `cat $(PID_DIR)/admin-clean.pid` 2>/dev/null || true; \
		rm -f $(PID_DIR)/admin-clean.pid; \
		echo "$(GREEN)Clean admin dashboard stopped$(NC)"; \
	else \
		echo "$(YELLOW)Clean admin dashboard not running$(NC)"; \
	fi

# ==== DEPRECATED WORKER COMMANDS - Use Celery instead ====
# worker-start: DEPRECATED - use 'make celery-start'
# worker-stop: DEPRECATED - use 'make celery-stop'

# ==== ALL MULTI-WORKER COMMANDS DEPRECATED ====
# multi-workers-*: DEPRECATED - use 'make celery-production-start' for multiple workers
# The old worker system has been completely replaced by Celery
# For monitoring use: http://localhost:5555 (Flower UI)

# ===================================================================
# 🏭 CELERY INDUSTRY STANDARD COMMANDS (Netflix/YouTube Architecture)
# ===================================================================

celery-worker-start: ## Start Celery worker (industry standard)
	@echo "$(BLUE)Starting Celery worker (industry standard)...$(NC)"
	@mkdir -p $(PID_DIR) logs/celery
	@if [ -f $(PID_DIR)/celery-worker.pid ] && kill -0 `cat $(PID_DIR)/celery-worker.pid` 2>/dev/null; then \
		echo "$(YELLOW)Celery worker already running (PID: `cat $(PID_DIR)/celery-worker.pid`)$(NC)"; \
	else \
		nohup celery -A core.celery_app:celery_app worker --loglevel=info --concurrency=4 --logfile=logs/celery/worker.log > logs/celery/worker-output.log 2>&1 & echo $$! > $(PID_DIR)/celery-worker.pid; \
		echo "$(GREEN)Celery worker started (PID: `cat $(PID_DIR)/celery-worker.pid`)$(NC)"; \
		echo "$(BLUE)Queue processing: video_processing, transcription, ai_analysis, file_operations$(NC)"; \
		echo "$(BLUE)Logs: logs/celery/worker.log$(NC)"; \
	fi

celery-worker-start-multi: ## Start multiple Celery workers (high concurrency)
	@echo "$(BLUE)Starting multiple Celery workers...$(NC)"
	@mkdir -p $(PID_DIR) logs/celery
	@for i in 1 2 3 4 5; do \
		if [ -f $(PID_DIR)/celery-worker-$$i.pid ] && kill -0 `cat $(PID_DIR)/celery-worker-$$i.pid` 2>/dev/null; then \
			echo "$(YELLOW)Celery worker $$i already running$(NC)"; \
		else \
			nohup celery -A core.celery_app:celery_app worker --loglevel=info --concurrency=4 --hostname=worker$$i@%h --logfile=logs/celery/worker-$$i.log > logs/celery/worker-$$i-output.log 2>&1 & echo $$! > $(PID_DIR)/celery-worker-$$i.pid; \
			echo "$(GREEN)Celery worker $$i started (PID: `cat $(PID_DIR)/celery-worker-$$i.pid`)$(NC)"; \
		fi; \
	done
	@echo "$(GREEN)5 Celery workers started with 4 concurrency each = 20 parallel tasks$(NC)"

celery-worker-stop: ## Stop Celery workers
	@echo "$(BLUE)Stopping Celery workers...$(NC)"
	@for pid_file in $(PID_DIR)/celery-worker*.pid; do \
		if [ -f "$$pid_file" ]; then \
			pid=`cat "$$pid_file"`; \
			if kill -0 "$$pid" 2>/dev/null; then \
				kill "$$pid" && echo "$(GREEN)Stopped worker (PID: $$pid)$(NC)"; \
			fi; \
			rm -f "$$pid_file"; \
		fi; \
	done
	@echo "$(GREEN)All Celery workers stopped$(NC)"

celery-beat-start: ## Start Celery Beat scheduler (for periodic tasks)
	@echo "$(BLUE)Starting Celery Beat scheduler...$(NC)"
	@mkdir -p $(PID_DIR) logs/celery
	@if [ -f $(PID_DIR)/celery-beat.pid ] && kill -0 `cat $(PID_DIR)/celery-beat.pid` 2>/dev/null; then \
		echo "$(YELLOW)Celery Beat already running (PID: `cat $(PID_DIR)/celery-beat.pid`)$(NC)"; \
	else \
		nohup celery -A core.celery_app:celery_app beat --loglevel=info --logfile=logs/celery/beat.log > logs/celery/beat-output.log 2>&1 & echo $$! > $(PID_DIR)/celery-beat.pid; \
		echo "$(GREEN)Celery Beat started (PID: `cat $(PID_DIR)/celery-beat.pid`)$(NC)"; \
		echo "$(BLUE)Periodic tasks: cleanup, health checks, metrics$(NC)"; \
	fi

celery-beat-stop: ## Stop Celery Beat scheduler
	@echo "$(BLUE)Stopping Celery Beat...$(NC)"
	@if [ -f $(PID_DIR)/celery-beat.pid ]; then \
		kill `cat $(PID_DIR)/celery-beat.pid` 2>/dev/null || true; \
		rm -f $(PID_DIR)/celery-beat.pid; \
		echo "$(GREEN)Celery Beat stopped$(NC)"; \
	else \
		echo "$(YELLOW)Celery Beat not running$(NC)"; \
	fi

celery-flower-start: ## Start Celery Flower monitoring (Web UI)
	@echo "$(BLUE)Starting Celery Flower monitoring...$(NC)"
	@mkdir -p $(PID_DIR) logs/celery
	@if [ -f $(PID_DIR)/celery-flower.pid ] && kill -0 `cat $(PID_DIR)/celery-flower.pid` 2>/dev/null; then \
		echo "$(YELLOW)Celery Flower already running (PID: `cat $(PID_DIR)/celery-flower.pid`)$(NC)"; \
	else \
		nohup celery -A core.celery_app:celery_app flower --port=5555 --logfile=logs/celery/flower.log > logs/celery/flower-output.log 2>&1 & echo $$! > $(PID_DIR)/celery-flower.pid; \
		echo "$(GREEN)Celery Flower started (PID: `cat $(PID_DIR)/celery-flower.pid`)$(NC)"; \
		echo "$(BLUE)Monitoring UI: http://localhost:5555$(NC)"; \
	fi

celery-flower-stop: ## Stop Celery Flower monitoring
	@echo "$(BLUE)Stopping Celery Flower...$(NC)"
	@if [ -f $(PID_DIR)/celery-flower.pid ]; then \
		kill `cat $(PID_DIR)/celery-flower.pid` 2>/dev/null || true; \
		rm -f $(PID_DIR)/celery-flower.pid; \
		echo "$(GREEN)Celery Flower stopped$(NC)"; \
	else \
		echo "$(YELLOW)Celery Flower not running$(NC)"; \
	fi

celery-status: ## Show Celery system status
	@echo "$(BLUE)Celery System Status:$(NC)"
	@echo "$(YELLOW)Workers:$(NC)"
	@celery -A core.celery_app:celery_app inspect active 2>/dev/null || echo "  $(RED)No workers responding$(NC)"
	@echo "$(YELLOW)Queues:$(NC)"
	@celery -A core.celery_app:celery_app inspect active_queues 2>/dev/null || echo "  $(RED)No queue info available$(NC)"
	@echo "$(YELLOW)Registered tasks:$(NC)"
	@celery -A core.celery_app:celery_app inspect registered 2>/dev/null | head -20 || echo "  $(RED)No registered tasks$(NC)"

celery-purge: ## Purge all tasks from queues (⚠️ DESTRUCTIVE)
	@echo "$(RED)⚠️  WARNING: This will delete all queued tasks!$(NC)"
	@read -p "Are you sure? (y/N): " confirm && [ "$$confirm" = "y" ] || exit 1
	@celery -A core.celery_app:celery_app purge -f
	@echo "$(GREEN)All queues purged$(NC)"

celery-logs: ## Show Celery logs
	@echo "$(BLUE)Celery System Logs:$(NC)"
	@echo "$(YELLOW)=== Worker Log ===$(NC)"
	@tail -20 logs/celery/worker.log 2>/dev/null || echo "No worker logs found"
	@echo ""
	@echo "$(YELLOW)=== Beat Log ===$(NC)"
	@tail -10 logs/celery/beat.log 2>/dev/null || echo "No beat logs found"
	@echo ""
	@echo "$(YELLOW)=== Flower Log ===$(NC)"
	@tail -10 logs/celery/flower.log 2>/dev/null || echo "No flower logs found"

# Combined commands for easy management
celery-start: redis-start celery-worker-start celery-beat-start celery-flower-start ## Start complete Celery system
	@echo "$(GREEN)🏭 Complete Celery system started!$(NC)"
	@echo "$(BLUE)Worker:    Processing video jobs$(NC)"
	@echo "$(BLUE)Beat:      Running periodic tasks$(NC)"
	@echo "$(BLUE)Flower:    http://localhost:5555$(NC)"
	@echo "$(BLUE)Redis:     localhost:6379$(NC)"

celery-stop: celery-flower-stop celery-beat-stop celery-worker-stop ## Stop complete Celery system
	@echo "$(GREEN)Celery system stopped$(NC)"

celery-restart: celery-stop celery-start ## Restart complete Celery system
	@echo "$(GREEN)Celery system restarted$(NC)"

# Production-ready start (multiple workers)
celery-production-start: redis-start celery-worker-start-multi celery-beat-start celery-flower-start ## Start production Celery (multiple workers)
	@echo "$(GREEN)🏭 Production Celery system started!$(NC)"
	@echo "$(BLUE)Workers:   5 workers x 4 concurrency = 20 parallel tasks$(NC)"
	@echo "$(BLUE)Beat:      Periodic maintenance tasks$(NC)"
	@echo "$(BLUE)Flower:    http://localhost:5555$(NC)"
	@echo "$(BLUE)Queues:    video_processing, transcription, ai_analysis, file_operations$(NC)"

websocket-start: ## Start WebSocket server (port 8765)
	@echo "$(BLUE)Starting WebSocket server...$(NC)"
	@mkdir -p $(PID_DIR)
	@if [ -f $(PID_DIR)/websocket.pid ] && kill -0 `cat $(PID_DIR)/websocket.pid` 2>/dev/null; then \
		echo "$(YELLOW)WebSocket server already running (PID: `cat $(PID_DIR)/websocket.pid`)$(NC)"; \
	else \
		nohup python3 websockets/websocket_server.py > logs/websocket.log 2>&1 & echo $$! > $(PID_DIR)/websocket.pid; \
		echo "$(GREEN)WebSocket server started (PID: `cat $(PID_DIR)/websocket.pid`)$(NC)"; \
		echo "$(BLUE)Real-time updates: ws://localhost:$(WEBSOCKET_PORT)$(NC)"; \
	fi

websocket-stop: ## Stop WebSocket server
	@echo "$(BLUE)Stopping WebSocket server...$(NC)"
	@if [ -f $(PID_DIR)/websocket.pid ]; then \
		kill `cat $(PID_DIR)/websocket.pid` 2>/dev/null || true; \
		rm -f $(PID_DIR)/websocket.pid; \
		echo "$(GREEN)WebSocket server stopped$(NC)"; \
	else \
		echo "$(YELLOW)WebSocket server not running$(NC)"; \
	fi

websocket-test: ## Test WebSocket system
	@echo "$(BLUE)Testing WebSocket system...$(NC)"
	@python test_websocket_system.py

# === Redis Management ===

redis-start: ## Start Redis server
	@echo "$(BLUE)Starting Redis server...$(NC)"
	@if pgrep redis-server > /dev/null; then \
		echo "$(YELLOW)Redis already running$(NC)"; \
	else \
		redis-server --daemonize yes --port $(REDIS_PORT); \
		echo "$(GREEN)Redis server started on port $(REDIS_PORT)$(NC)"; \
	fi

redis-stop: ## Stop Redis server
	@echo "$(BLUE)Stopping Redis server...$(NC)"
	@redis-cli shutdown 2>/dev/null || true
	@echo "$(GREEN)Redis server stopped$(NC)"

redis-status: ## Check Redis status
	@echo "$(BLUE)Checking Redis status...$(NC)"
	@if redis-cli ping 2>/dev/null | grep -q PONG; then \
		echo "$(GREEN)Redis is running and responding$(NC)"; \
	else \
		echo "$(RED)Redis is not running$(NC)"; \
	fi

# === Combined Commands ===

quickstart: ## 🚀 First time? Run this! (setup + start everything)
	@echo "$(BLUE)╔════════════════════════════════════════════════════════╗$(NC)"
	@echo "$(BLUE)║               AgentOS Quick Start                      ║$(NC)"
	@echo "$(BLUE)╚════════════════════════════════════════════════════════╝$(NC)"
	@echo ""
	@echo "$(YELLOW)Setting up AgentOS for first time use...$(NC)"
	@make setup
	@echo ""
	@echo "$(YELLOW)Cleaning any existing processes...$(NC)"
	@make force-clean
	@echo ""
	@echo "$(YELLOW)Starting all services...$(NC)"
	@make start
	@echo ""
	@echo "$(GREEN)✨ AgentOS is ready!$(NC)"
	@echo ""
	@echo "$(YELLOW)📍 Open your browser to:$(NC)"
	@echo "   $(BLUE)Frontend: http://localhost:$(FRONTEND_PORT)/ui-v2/$(NC)"
	@echo "   $(BLUE)Admin:    http://localhost:$(ADMIN_CLEAN_PORT)/$(NC)"
	@echo ""
	@echo "$(YELLOW)📚 Next steps:$(NC)"
	@echo "   - Upload a video in the UI"
	@echo "   - Check logs: $(GREEN)make logs$(NC)"
	@echo "   - Check status: $(GREEN)make status$(NC)"
	@echo "   - Stop everything: $(GREEN)make stop-all$(NC)"

start: redis-start websocket-start api-start frontend-start admin-clean-start celery-start ## Start all services with Celery
	@echo "$(GREEN)All services started!$(NC)"
	@echo "$(BLUE)Frontend:     http://localhost:$(FRONTEND_PORT)/ui-v2/$(NC)"
	@echo "$(BLUE)Admin:        http://localhost:$(ADMIN_CLEAN_PORT)/$(NC)"
	@echo "$(BLUE)API:          http://localhost:$(API_PORT)$(NC)"
	@echo "$(BLUE)WebSocket:    ws://localhost:$(WEBSOCKET_PORT)$(NC)"
	@make status

stop: websocket-stop api-stop frontend-stop admin-clean-stop celery-stop ## Stop all services (keeps Redis running)
	@echo "$(GREEN)All AgentOS services stopped$(NC)"
	@echo "$(YELLOW)Redis left running (use 'make redis-stop' to stop)$(NC)"

stop-all: stop redis-stop ## Stop all services including Redis
	@echo "$(GREEN)All services stopped completely$(NC)"

restart: stop start ## Restart all services
	@echo "$(GREEN)All services restarted$(NC)"

# === Status & Monitoring ===

status: ## Show status of all services
	@echo "$(BLUE)AgentOS Service Status:$(NC)"
	@echo "$(YELLOW)Redis:$(NC)"
	@if redis-cli ping 2>/dev/null | grep -q PONG; then \
		echo "  $(GREEN)✓ Running$(NC)"; \
	else \
		echo "  $(RED)✗ Not running$(NC)"; \
	fi
	@echo "$(YELLOW)API Server:$(NC)"
	@if [ -f $(PID_DIR)/api.pid ] && kill -0 `cat $(PID_DIR)/api.pid` 2>/dev/null; then \
		echo "  $(GREEN)✓ Running (PID: `cat $(PID_DIR)/api.pid`)$(NC)"; \
	else \
		echo "  $(RED)✗ Not running$(NC)"; \
	fi
	@echo "$(YELLOW)Frontend Server:$(NC)"
	@if [ -f $(PID_DIR)/frontend.pid ] && kill -0 `cat $(PID_DIR)/frontend.pid` 2>/dev/null; then \
		echo "  $(GREEN)✓ Running (PID: `cat $(PID_DIR)/frontend.pid`)$(NC)"; \
	else \
		echo "  $(RED)✗ Not running$(NC)"; \
	fi
	@echo "$(YELLOW)Admin Dashboard:$(NC)"
	@if [ -f $(PID_DIR)/admin-clean.pid ] && kill -0 `cat $(PID_DIR)/admin-clean.pid` 2>/dev/null; then \
		echo "  $(GREEN)✓ Running (PID: `cat $(PID_DIR)/admin-clean.pid`)$(NC)"; \
	else \
		echo "  $(RED)✗ Not running$(NC)"; \
	fi
	@echo "$(YELLOW)Celery Workers:$(NC)"
	@if ls $(PID_DIR)/celery-worker*.pid 1> /dev/null 2>&1; then \
		worker_count=`ls $(PID_DIR)/celery-worker*.pid 2>/dev/null | wc -l`; \
		echo "  $(GREEN)✓ Running ($$worker_count worker(s))$(NC)"; \
	else \
		echo "  $(RED)✗ Not running$(NC)"; \
	fi
	@echo "$(YELLOW)Celery Beat:$(NC)"
	@if [ -f $(PID_DIR)/celery-beat.pid ] && kill -0 `cat $(PID_DIR)/celery-beat.pid` 2>/dev/null; then \
		echo "  $(GREEN)✓ Running (PID: `cat $(PID_DIR)/celery-beat.pid`)$(NC)"; \
	else \
		echo "  $(RED)✗ Not running$(NC)"; \
	fi
	@echo "$(YELLOW)Celery Flower:$(NC)"
	@if [ -f $(PID_DIR)/celery-flower.pid ] && kill -0 `cat $(PID_DIR)/celery-flower.pid` 2>/dev/null; then \
		echo "  $(GREEN)✓ Running (PID: `cat $(PID_DIR)/celery-flower.pid`)$(NC)"; \
	else \
		echo "  $(RED)✗ Not running$(NC)"; \
	fi
	@echo "$(YELLOW)WebSocket Server:$(NC)"
	@if [ -f $(PID_DIR)/websocket.pid ] && kill -0 `cat $(PID_DIR)/websocket.pid` 2>/dev/null; then \
		echo "  $(GREEN)✓ Running (PID: `cat $(PID_DIR)/websocket.pid`)$(NC)"; \
	else \
		echo "  $(RED)✗ Not running$(NC)"; \
	fi

logs: ## Show recent logs from all services
	@echo "$(BLUE)Recent logs from all services:$(NC)"
	@echo "$(YELLOW)=== API Server ===$(NC)"
	@tail -10 logs/api.log 2>/dev/null || echo "No API logs found"
	@echo "$(YELLOW)=== Frontend Server ===$(NC)"
	@tail -10 logs/frontend.log 2>/dev/null || echo "No frontend logs found"
	@echo "$(YELLOW)=== Admin Dashboard ===$(NC)"
	@tail -10 logs/admin.log 2>/dev/null || echo "No admin logs found"
	@echo "$(YELLOW)=== Video Worker ===$(NC)"
	@tail -10 logs/worker.log 2>/dev/null || echo "No worker logs found"
	@echo "$(YELLOW)=== WebSocket Server ===$(NC)"
	@tail -10 logs/websocket.log 2>/dev/null || echo "No websocket logs found"
	@echo "$(YELLOW)=== Main Application ===$(NC)"
	@tail -10 logs/agentos.log 2>/dev/null || echo "No main logs found"

# === Port Management ===

ports: ## Show what's running on AgentOS ports
	@echo "$(BLUE)Checking AgentOS ports...$(NC)"
	@echo "$(YELLOW)Port $(API_PORT) (API):$(NC)"
	@lsof -i :$(API_PORT) 2>/dev/null || echo "  Nothing running on port $(API_PORT)"
	@echo "$(YELLOW)Port $(FRONTEND_PORT) (Frontend):$(NC)"
	@lsof -i :$(FRONTEND_PORT) 2>/dev/null || echo "  Nothing running on port $(FRONTEND_PORT)"
	@echo "$(YELLOW)Port $(ADMIN_CLEAN_PORT) (Admin):$(NC)"
	@lsof -i :$(ADMIN_CLEAN_PORT) 2>/dev/null || echo "  Nothing running on port $(ADMIN_CLEAN_PORT)"
	@echo "$(YELLOW)Port $(FLOWER_PORT) (Celery Flower):$(NC)"
	@lsof -i :$(FLOWER_PORT) 2>/dev/null || echo "  Nothing running on port $(FLOWER_PORT)"
	@echo "$(YELLOW)Port $(REDIS_PORT) (Redis):$(NC)"
	@lsof -i :$(REDIS_PORT) 2>/dev/null || echo "  Nothing running on port $(REDIS_PORT)"
	@echo "$(YELLOW)Port $(WEBSOCKET_PORT) (WebSocket):$(NC)"
	@lsof -i :$(WEBSOCKET_PORT) 2>/dev/null || echo "  Nothing running on port $(WEBSOCKET_PORT)"

kill-ports: ## Kill all processes on AgentOS ports
	@echo "$(BLUE)Killing processes on AgentOS ports...$(NC)"
	@echo "$(YELLOW)Killing processes on port $(API_PORT)...$(NC)"
	@lsof -ti :$(API_PORT) | xargs -r kill -9 2>/dev/null || echo "  No process found on port $(API_PORT)"
	@echo "$(YELLOW)Killing processes on port $(FRONTEND_PORT)...$(NC)"
	@lsof -ti :$(FRONTEND_PORT) | xargs -r kill -9 2>/dev/null || echo "  No process found on port $(FRONTEND_PORT)"
	@echo "$(YELLOW)Killing processes on port $(ADMIN_CLEAN_PORT)...$(NC)"
	@lsof -ti :$(ADMIN_CLEAN_PORT) | xargs -r kill -9 2>/dev/null || echo "  No process found on port $(ADMIN_CLEAN_PORT)"
	@echo "$(YELLOW)Killing processes on port $(FLOWER_PORT)...$(NC)"
	@lsof -ti :$(FLOWER_PORT) | xargs -r kill -9 2>/dev/null || echo "  No process found on port $(FLOWER_PORT)"
	@echo "$(YELLOW)Killing processes on port $(WEBSOCKET_PORT)...$(NC)"
	@lsof -ti :$(WEBSOCKET_PORT) | xargs -r kill -9 2>/dev/null || echo "  No process found on port $(WEBSOCKET_PORT)"
	@echo "$(GREEN)Port cleanup completed$(NC)"

kill-api-port: ## Kill processes on API port (8001)
	@echo "$(BLUE)Killing processes on API port $(API_PORT)...$(NC)"
	@lsof -ti :$(API_PORT) | xargs -r kill -9 2>/dev/null || echo "  No process found on port $(API_PORT)"
	@echo "$(GREEN)API port cleared$(NC)"

# === Utilities ===

clean: ## Clean PID files and stop orphaned processes
	@echo "$(BLUE)Cleaning up...$(NC)"
	@rm -rf $(PID_DIR)
	@pkill -f "uvicorn api.main:app" 2>/dev/null || true
	@pkill -f "python3 -m http.server $(FRONTEND_PORT)" 2>/dev/null || true
	@pkill -f "python3 -m http.server $(ADMIN_CLEAN_PORT)" 2>/dev/null || true
	@pkill -f "python3 workers/video_worker.py" 2>/dev/null || true
	@pkill -f "python3 websockets/websocket_server.py" 2>/dev/null || true
	@echo "$(GREEN)Cleanup completed$(NC)"

cleanup-all: ## Clean up ALL AgentOS processes (including orphaned development workers)
	@echo "$(BLUE)╔════════════════════════════════════════════════════════╗$(NC)"
	@echo "$(BLUE)║              Deep Cleanup - All Processes             ║$(NC)"
	@echo "$(BLUE)╚════════════════════════════════════════════════════════╝$(NC)"
	@echo ""
	@echo "$(YELLOW)Stopping all AgentOS processes...$(NC)"
	@make stop 2>/dev/null || true
	@echo ""
	@echo "$(YELLOW)Cleaning PID files...$(NC)"
	@rm -rf $(PID_DIR)
	@echo ""
	@echo "$(YELLOW)Killing orphaned processes...$(NC)"
	@echo "  - API servers..."
	@pkill -f "uvicorn.*api.main:app" 2>/dev/null || true
	@echo "  - HTTP servers..."
	@pkill -f "python3 -m http.server" 2>/dev/null || true
	@pkill -f "http.server.*800" 2>/dev/null || true
	@echo "  - All video workers (including test workers)..."
	@pkill -f "python3.*video_worker.py" 2>/dev/null || true
	@echo "  - WebSocket servers..."
	@pkill -f "python3.*websocket_server.py" 2>/dev/null || true
	@echo "  - Development monitors..."
	@pkill -f "python3.*dev-monitor.py" 2>/dev/null || true
	@echo ""
	@echo "$(YELLOW)Checking for remaining AgentOS processes...$(NC)"
	@ps aux | grep -E "(video_worker|api\.main|websocket_server|http\.server.*800)" | grep -v grep || echo "  $(GREEN)No remaining processes found$(NC)"
	@echo ""
	@echo "$(GREEN)✅ Deep cleanup completed!$(NC)"
	@echo "$(BLUE)Ready for fresh start with 'make start'$(NC)"

force-clean: kill-ports clean ## Force clean all processes and ports
	@echo "$(GREEN)Force cleanup completed$(NC)"

test: ## Test if all services are responding
	@echo "$(BLUE)Testing services...$(NC)"
	@echo "$(YELLOW)Redis:$(NC)"
	@if redis-cli ping 2>/dev/null | grep -q PONG; then \
		echo "  $(GREEN)✓ Redis responding$(NC)"; \
	else \
		echo "  $(RED)✗ Redis not responding$(NC)"; \
	fi
	@echo "$(YELLOW)API Server:$(NC)"
	@if curl -s http://localhost:$(API_PORT)/health >/dev/null 2>&1; then \
		echo "  $(GREEN)✓ API responding$(NC)"; \
	else \
		echo "  $(RED)✗ API not responding$(NC)"; \
	fi
	@echo "$(YELLOW)Frontend Server:$(NC)"
	@if curl -s http://localhost:$(FRONTEND_PORT)/ui-v2/ >/dev/null 2>&1; then \
		echo "  $(GREEN)✓ Frontend responding$(NC)"; \
	else \
		echo "  $(RED)✗ Frontend not responding$(NC)"; \
	fi
	@echo "$(YELLOW)Admin Dashboard:$(NC)"
	@if curl -s http://localhost:$(ADMIN_CLEAN_PORT)/ >/dev/null 2>&1; then \
		echo "  $(GREEN)✓ Admin responding$(NC)"; \
	else \
		echo "  $(RED)✗ Admin not responding$(NC)"; \
	fi
	@echo "$(YELLOW)WebSocket Server:$(NC)"
	@python -c "import asyncio, websockets; asyncio.run(websockets.connect('ws://localhost:$(WEBSOCKET_PORT)'))" 2>/dev/null && echo "  $(GREEN)✓ WebSocket responding$(NC)" || echo "  $(RED)✗ WebSocket not responding$(NC)"

# === Development ===

dev: ## Start development environment (with logs)
	@echo "$(BLUE)Starting development environment...$(NC)"
	@make start
	@echo "$(YELLOW)Following logs (Ctrl+C to stop):$(NC)"
	@tail -f logs/agentos.log

setup: ## Setup directories and dependencies
	@echo "$(BLUE)Setting up AgentOS...$(NC)"
	@mkdir -p logs $(PID_DIR)
	@touch logs/api.log logs/frontend.log logs/worker.log logs/websocket.log logs/agentos.log
	@echo "$(GREEN)Setup completed$(NC)"

# === Production Commands ===

production-start: ## Start services for production (with proper error handling)
	@echo "$(BLUE)Starting AgentOS in production mode...$(NC)"
	@make redis-start
	@sleep 2
	@make websocket-start
	@sleep 2
	@make api-start
	@sleep 2
	@make worker-start
	@make status
	@echo "$(GREEN)Production services started!$(NC)"
	@echo "$(YELLOW)Note: Frontend served separately in production$(NC)"

production-stop: ## Stop production services
	@echo "$(BLUE)Stopping production services...$(NC)"
	@make websocket-stop
	@make api-stop
	@make worker-stop
	@echo "$(GREEN)Production services stopped$(NC)"
	@echo "$(YELLOW)Redis left running (use 'make redis-stop' if needed)$(NC)"

realtime: websocket-start websocket-test ## Start and test real-time WebSocket system
	@echo "$(GREEN)Real-time system ready!$(NC)"

# ===================================
# 🚀 DEVELOPMENT MODE TARGETS
# ===================================

dev-start: ## Start all services in development mode (auto-reload + monitoring)
	@echo "$(BLUE)🚀 Starting AgentOS Development Environment...$(NC)"
	@echo "$(YELLOW)Features: Auto-reload, Health monitoring, Crash recovery$(NC)"
	@echo ""
	@make redis-start
	@sleep 1
	@make dev-websocket-start
	@sleep 2
	@make dev-api-start
	@sleep 2
	@make dev-frontend-start
	@sleep 1
	@sleep 1
	@make worker-start
	@sleep 2
	@echo ""
	@echo "$(GREEN)🎉 Development environment ready!$(NC)"
	@echo "$(BLUE)Frontend:  http://localhost:$(FRONTEND_PORT)/ui-v2/$(NC)"
	@echo "$(BLUE)Admin:     http://localhost:$(ADMIN_CLEAN_PORT)/$(NC)"
	@echo "$(BLUE)API:       http://localhost:$(API_PORT)$(NC)"
	@echo "$(BLUE)WebSocket: ws://localhost:$(WEBSOCKET_PORT)$(NC)"
	@echo ""
	@echo "$(YELLOW)💡 Services will auto-reload on file changes$(NC)"
	@echo "$(YELLOW)💡 Use 'make dev-logs' to monitor all logs$(NC)"

dev-stop: ## Stop all development services
	@echo "$(BLUE)Stopping development environment...$(NC)"
	@if [ -f $(PID_DIR)/monitor.pid ]; then \
		echo "$(BLUE)Stopping health monitor...$(NC)"; \
		kill `cat $(PID_DIR)/monitor.pid` 2>/dev/null || true; \
		rm -f $(PID_DIR)/monitor.pid; \
		echo "$(GREEN)Health monitor stopped$(NC)"; \
	fi
	@make stop
	@echo "$(GREEN)Development environment stopped$(NC)"

dev-restart: ## Restart all development services
	@make dev-stop
	@sleep 2
	@make dev-start

dev-api-start: ## Start API server with auto-reload
	@echo "$(BLUE)Starting API server (development mode)...$(NC)"
	@mkdir -p $(PID_DIR)
	@if [ -f $(PID_DIR)/api.pid ] && kill -0 `cat $(PID_DIR)/api.pid` 2>/dev/null; then \
		echo "$(YELLOW)API server already running (PID: `cat $(PID_DIR)/api.pid`)$(NC)"; \
	else \
		nohup python3 -m uvicorn api.main:app --host 0.0.0.0 --port $(API_PORT) --reload --reload-dir . > logs/api.log 2>&1 & echo $$! > $(PID_DIR)/api.pid; \
		echo "$(GREEN)API server started with auto-reload (PID: `cat $(PID_DIR)/api.pid`)$(NC)"; \
		echo "$(BLUE)Access: http://localhost:$(API_PORT)$(NC)"; \
		echo "$(YELLOW)Auto-reload: Enabled for all Python files$(NC)"; \
	fi

dev-websocket-start: ## Start WebSocket server with auto-reload
	@echo "$(BLUE)Starting WebSocket server (development mode)...$(NC)"
	@mkdir -p $(PID_DIR)
	@if [ -f $(PID_DIR)/websocket.pid ] && kill -0 `cat $(PID_DIR)/websocket.pid` 2>/dev/null; then \
		echo "$(YELLOW)WebSocket server already running (PID: `cat $(PID_DIR)/websocket.pid`)$(NC)"; \
	else \
		nohup python3 websockets/websocket_server.py > logs/websocket.log 2>&1 & echo $$! > $(PID_DIR)/websocket.pid; \
		echo "$(GREEN)WebSocket server started (PID: `cat $(PID_DIR)/websocket.pid`)$(NC)"; \
		echo "$(BLUE)Real-time updates: ws://localhost:$(WEBSOCKET_PORT)$(NC)"; \
	fi

dev-frontend-start: ## Start frontend with file watching
	@echo "$(BLUE)Starting frontend server (development mode)...$(NC)"
	@mkdir -p $(PID_DIR)
	@if [ -f $(PID_DIR)/frontend.pid ] && kill -0 `cat $(PID_DIR)/frontend.pid` 2>/dev/null; then \
		echo "$(YELLOW)Frontend server already running (PID: `cat $(PID_DIR)/frontend.pid`)$(NC)"; \
	else \
		nohup python3 -m http.server $(FRONTEND_PORT) --directory ui-v2 > logs/frontend.log 2>&1 & echo $$! > $(PID_DIR)/frontend.pid; \
		echo "$(GREEN)Frontend server started (PID: `cat $(PID_DIR)/frontend.pid`)$(NC)"; \
		echo "$(BLUE)Access: http://localhost:$(FRONTEND_PORT)/ui-v2/$(NC)"; \
	fi

	@echo "$(BLUE)Starting admin dashboard (development mode)...$(NC)"
	@mkdir -p $(PID_DIR)
	@if [ -f $(PID_DIR)/admin.pid ] && kill -0 `cat $(PID_DIR)/admin.pid` 2>/dev/null; then \
		echo "$(YELLOW)Admin dashboard already running (PID: `cat $(PID_DIR)/admin.pid`)$(NC)"; \
	else \
		nohup python3 -m http.server $(ADMIN_PORT) --directory ui-admin > logs/admin.log 2>&1 & echo $$! > $(PID_DIR)/admin.pid; \
		echo "$(GREEN)Admin dashboard started (PID: `cat $(PID_DIR)/admin.pid`)$(NC)"; \
		echo "$(BLUE)Access: http://localhost:$(ADMIN_PORT)/$(NC)"; \
	fi

dev-logs: ## Show live logs from all development services
	@echo "$(BLUE)Showing live logs from all services...$(NC)"
	@echo "$(YELLOW)Press Ctrl+C to stop$(NC)"
	@echo ""
	@tail -f logs/*.log

dev-monitor: ## Start health monitor for crash recovery
	@echo "$(BLUE)Starting development health monitor...$(NC)"
	@echo "$(YELLOW)Monitor will auto-restart crashed services$(NC)"
	@echo "$(YELLOW)Press Ctrl+C to stop$(NC)"
	@echo ""
	@python3 scripts/dev-monitor.py

dev-full: ## Start development environment with health monitoring
	@echo "$(BLUE)🚀 Starting FULL Development Environment...$(NC)"
	@echo "$(YELLOW)Features: Auto-reload + Health monitoring + Crash recovery$(NC)"
	@echo ""
	@make dev-start
	@echo ""
	@echo "$(GREEN)🎉 Starting health monitor in background...$(NC)"
	@nohup python3 scripts/dev-monitor.py > logs/monitor.log 2>&1 & echo $$! > $(PID_DIR)/monitor.pid
	@echo "$(GREEN)✅ Full development environment ready!$(NC)"
	@echo ""
	@echo "$(YELLOW)💡 Health monitor running - check 'logs/monitor.log'$(NC)"
	@echo "$(YELLOW)💡 Use 'make dev-stop' to stop everything$(NC)"