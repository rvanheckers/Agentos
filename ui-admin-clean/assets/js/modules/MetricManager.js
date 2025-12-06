import { MetricCard } from '../components/MetricCard.js';

export class MetricManager {
  constructor() {
    this.metricCards = new Map();
  }

  setupMetricCards() {
    const systemHealthCard = new MetricCard(
      document.getElementById('system-health-card'), 
      {
        title: 'System Health',
        value: '0%',
        description: 'System uptime percentage',
        status: 'good',
        icon: '❤️',
        helpId: 'system_health'
      }
    );
    this.metricCards.set('systemHealth', systemHealthCard);

    const workersCard = new MetricCard(
      document.getElementById('workers-card'),
      {
        title: 'Celery Workers',
        value: '0',
        description: 'Processing nodes online',
        status: 'good',
        icon: '👷',
        helpId: 'workers_status'
      }
    );
    this.metricCards.set('workers', workersCard);

    const queueCard = new MetricCard(
      document.getElementById('queue-card'),
      {
        title: 'Queue Status',
        value: '0',
        description: 'Jobs pending in queue',
        status: 'good',
        icon: '📋',
        helpId: 'queue_status'
      }
    );
    this.metricCards.set('queue', queueCard);

    const jobsCard = new MetricCard(
      document.getElementById('jobs-card'),
      {
        title: 'Active Jobs',
        value: '0',
        description: 'Currently processing',
        status: 'good',
        icon: '⚡',
        helpId: 'jobs_today'
      }
    );
    this.metricCards.set('jobs', jobsCard);

    const activeAgentsCard = new MetricCard(
      document.getElementById('active-agents-card'),
      {
        title: 'Active Agents',
        value: '0',
        description: 'AI agents available',
        status: 'good',
        icon: '🤖',
        helpId: 'active_agents'
      }
    );
    this.metricCards.set('activeAgents', activeAgentsCard);
  }

  updateSystemHealth(data) {
    const card = this.metricCards.get('systemHealth');
    const status = data.status === 'healthy' ? 'good' : 'warning';
    
    // Show CPU usage if available, otherwise uptime, otherwise status
    const cpuUsage = data.cpu_usage;
    const memoryUsage = data.memory_usage;
    const uptime = data.uptime;
    
    let displayValue, description;
    
    if (cpuUsage !== undefined && cpuUsage !== 0) {
      displayValue = `${Math.round(cpuUsage)}%`;
      description = `CPU: ${Math.round(cpuUsage)}%, Memory: ${Math.round(memoryUsage || 0)}%`;
    } else if (uptime && uptime !== 'N/A') {
      displayValue = uptime;
      description = `System status: ${data.status || 'unknown'}`;
    } else {
      displayValue = data.status || 'unknown';
      description = `System status: ${data.status || 'unknown'}`;
    }
    
    card.update({
      value: displayValue,
      status: status,
      description: description
    });
  }

  updateWorkers(data) {
    const card = this.metricCards.get('workers');
    
    // Check if this is mock data (fixed data paths should provide real data)
    const isMockData = data.is_mock_data === true;
    
    // Handle different data structures
    let active = 0;
    let total = 0;
    
    if (data.workers && Array.isArray(data.workers)) {
      // New format: {workers: [...], metrics: {...}}
      total = data.workers.length;
      // FIX: Only count workers with 'active' status, not idle ones
      active = data.workers.filter(w => w.status === 'active').length;
      
      // If data object has pre-calculated active/total, prefer that over array filtering
      if (typeof data.active === 'number' && typeof data.total === 'number') {
        active = data.active;
        total = data.total;
      }
    } else if (data.metrics && data.metrics.instances) {
      // Alternative format with metrics
      total = data.metrics.instances.total || 0;
      active = data.metrics.instances.running || 0;
    } else {
      // Fallback to old format
      active = data.active || 0;
      total = data.total || 0;
    }
    
    // Update card with clear mock indicator
    if (isMockData) {
      card.update({
        value: `🎭 ${active}/${total}`,
        status: 'warning',
        description: '⚠️ MOCK DATA - Start Celery workers!',
        title: 'Workers (MOCK)'
      });
    } else {
      // Description based on whether this is derived data or real worker data
      let capacityDesc;
      if (data.derived) {
        // This is derived from job analysis
        const idle = data.idle || (total - active);
        capacityDesc = total > 0 
          ? `${total} worker${total > 1 ? 's' : ''} from job analysis (${active} active, ${idle} idle)`
          : 'No workers detected in recent jobs';
      } else {
        // This is real worker data from Celery
        const concurrency = total > 0 ? 4 : 0; // Hardcoded for now, should come from API
        capacityDesc = total > 0 
          ? `${total} node${total > 1 ? 's' : ''} (${total * concurrency} concurrent jobs)`
          : 'No processing capacity';
      }
        
      card.update({
        value: `${active}/${total}`,
        status: total > 0 ? 'good' : 'warning',
        description: capacityDesc,
        title: data.derived ? 'Workers (derived)' : 'Celery Workers'
      });
    }
  }

  updateQueue(data) {
    const card = this.metricCards.get('queue');
    
    const pending = data.pending || 0;
    const processing = data.processing || 0;
    const completed = data.completed || 0;
    const total = data.total || 0;
    const isMockData = data.is_mock_data === true;
    
    let status = 'good';
    if (pending > 100) status = 'danger';
    else if (pending > 25) status = 'warning';
    
    if (isMockData) {
      card.update({
        value: `🎭 ${pending}`,
        status: 'warning',
        description: '⚠️ MOCK DATA - Not real queue status',
        title: 'Queue (MOCK)'
      });
    } else {
      // Show total active queue items: pending + processing
      const displayValue = pending + processing;
      
      // Update status based on what we're showing
      if (processing > 0 && pending === 0) {
        status = 'good'; // Processing jobs is good
      }
      
      card.update({
        value: displayValue.toString(),
        status: status,
        description: `${pending} queued, ${processing} processing`
      });
    }
  }

  updateJobs(data) {
    const card = this.metricCards.get('jobs');
    const completed = data.completed || 0;  // Now correctly passed from Dashboard.js
    const failed = data.failed || 0;
    const processing = data.processing || 0;
    const pending = data.pending || 0;
    const total = data.total || 0;
    
    // Active jobs = only processing jobs (not queued/pending)
    const activeJobs = processing;
    
    // Active Jobs status based on operational health, not historical performance
    let status = 'good';
    let description = '';
    
    console.log('🔍 MetricManager jobs data:', { completed, failed, processing, pending, total, activeJobs });
    
    // Operational status logic for active jobs
    if (activeJobs === 0 && pending > 0) {
      status = 'warning'; // Jobs stuck in queue
      description = 'Jobs queued but not processing';
    } else if (activeJobs > 20) {
      status = 'warning'; // System potentially overloaded
      description = 'High job load - monitor performance';
    } else if (activeJobs > 0) {
      status = 'good'; // Jobs processing normally
      description = 'Processing jobs normally';
    } else {
      status = 'good'; // No active jobs is fine
      description = 'No active jobs';
    }
    
    card.update({
      value: activeJobs.toString(),  // Show only processing jobs as active
      status: status,
      description: `${activeJobs} active (${processing} processing, ${pending} queued)`
    });
  }

  updateActiveAgents(data) {
    const card = this.metricCards.get('activeAgents');
    
    // Extract agents data from API response
    let activeAgents = 0;
    let totalAgents = 0;
    let status = 'good';
    let description = 'AI agents available';
    
    if (data && data.agents) {
      // API format: {agents: [...], total_agents: N, active_agents: N}
      totalAgents = data.total_agents || 0;
      activeAgents = data.active_agents || 0;
      
      if (activeAgents === 0) {
        status = 'warning';
        description = 'No agents running';
      } else {
        const categories = [...new Set(data.agents.map(a => a.category))];
        description = `${activeAgents}/${totalAgents} agents (${categories.length} categories)`;
      }
    } else if (data && data.error) {
      status = 'danger';
      description = 'Agents service error';
      totalAgents = 0;
      activeAgents = 0;
    }
    
    card.update({
      value: `${activeAgents}/${totalAgents}`,
      status: status,
      description: description
    });
  }

  updateAllMetrics(dashboardData) {
    this.updateSystemHealth(dashboardData.system_health);
    this.updateWorkers(dashboardData.workers_status);
    this.updateQueue(dashboardData.queue_status);
    this.updateJobs(dashboardData.today_jobs);
  }
}