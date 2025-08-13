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
        title: 'Today\'s Jobs',
        value: '0',
        description: 'Jobs created today',
        status: 'good',
        icon: '✅',
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
    const uptime = data.uptime || '0h';
    const status = data.status === 'healthy' ? 'good' : 'warning';
    
    card.update({
      value: uptime, // No % for uptime!
      status: status,
      description: `System status: ${data.status || 'unknown'}`
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
      active = data.workers.filter(w => w.status === 'active' || w.status === 'idle').length;
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
      // Calculate concurrency info for better description
      const concurrency = total > 0 ? 4 : 0; // Hardcoded for now, should come from API
      const capacityDesc = total > 0 
        ? `${total} node${total > 1 ? 's' : ''} (${total * concurrency} concurrent jobs)`
        : 'No processing capacity';
        
      card.update({
        value: `${active}/${total}`,
        status: total > 0 ? 'good' : 'warning',
        description: capacityDesc
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
      // Show most relevant queue metric: pending > processing > total
      const displayValue = pending > 0 ? pending : (processing > 0 ? processing : total);
      
      // Update status based on what we're showing
      if (processing > 0 && pending === 0) {
        status = 'good'; // Processing jobs is good
      }
      
      card.update({
        value: displayValue.toString(),
        status: status,
        description: processing > 0 ? `${processing} currently processing` : `${completed} completed jobs`
      });
    }
  }

  updateJobs(data) {
    const card = this.metricCards.get('jobs');
    const completed = data.completed || 0;  // Now correctly passed from Dashboard.js
    const failed = data.failed || 0;
    const total = data.total || 0;
    
    // CRITICAL FIX: Use API success_rate if available, otherwise calculate
    const apiSuccessRate = data.success_rate;
    
    let status = 'good';
    let description = '';
    
    console.log('🔍 MetricManager jobs data:', { completed, failed, total, apiSuccessRate });
    
    if (total === 0) {
      status = 'good';
      description = 'No jobs today';
    } else {
      // Use API success rate if available, otherwise calculate
      const successRate = apiSuccessRate !== undefined 
        ? Math.round(apiSuccessRate) 
        : Math.round((completed / total) * 100);
        
      if (failed > 5 && successRate < 50) status = 'danger';
      else if (failed > 2 && successRate < 80) status = 'warning';
      
      description = `${successRate}% success (${completed}/${total} completed today)`;
    }
    
    card.update({
      value: total.toString(),  // CRITICAL FIX: Show total jobs today, not just completed
      status: status,
      description: description
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