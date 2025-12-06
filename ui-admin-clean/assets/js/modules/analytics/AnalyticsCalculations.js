/**
 * AnalyticsCalculations Module
 * Handles all KPI calculations, metrics processing and data transformations
 */

export class AnalyticsCalculations {
  constructor() {
    this.targetSLA = 95; // Default SLA target
    this.baselineThroughput = 1000; // Baseline for throughput calculations
  }

  /**
   * Calculate enterprise-level KPIs
   */
  calculateEnterpriseKPIs(data) {
    const jobMetrics = data.job_metrics || {};
    const systemHealth = data.system_health || {};
    const queueMetrics = data.queue_status || {};
    
    return {
      mttr: this.calculateMTTR(jobMetrics),
      sla_compliance: this.calculateSLACompliance(jobMetrics.success_rate || 95),
      system_load: this.calculateSystemLoadScore(systemHealth, queueMetrics),
      throughput_trend: this.calculateThroughputTrend(jobMetrics),
      efficiency_score: this.calculateEfficiencyScore(jobMetrics, systemHealth)
    };
  }

  /**
   * Calculate Mean Time To Recovery (MTTR)
   */
  calculateMTTR(jobMetrics) {
    const safeJobMetrics = jobMetrics || {};
    
    if (safeJobMetrics.failed === 0 || !safeJobMetrics.failed) return 0;
    
    return Math.floor(Math.random() * 30) + 10; // Simulated for now
  }

  /**
   * Calculate SLA compliance percentage
   */
  calculateSLACompliance(successRate) {
    const safeRate = successRate || 0;
    const compliance = (safeRate / this.targetSLA) * 100;
    return Math.min(100, Math.round(compliance * 10) / 10);
  }

  /**
   * Calculate system load score (0-100)
   */
  calculateSystemLoadScore(systemHealth, queueMetrics) {
    const cpuScore = 100 - (systemHealth.cpu_usage || 0);
    const memoryScore = 100 - (systemHealth.memory_usage || 0);
    const queueScore = Math.max(0, 100 - ((queueMetrics.total_queued || 0) / 10));
    const workerScore = ((systemHealth.active_workers || 0) / (systemHealth.total_workers || 1)) * 100;
    
    const weights = {
      cpu: 0.3,
      memory: 0.2,
      queue: 0.3,
      workers: 0.2
    };
    
    return Math.round(
      cpuScore * weights.cpu +
      memoryScore * weights.memory +
      queueScore * weights.queue +
      workerScore * weights.workers
    );
  }

  /**
   * Calculate throughput trend
   */
  calculateThroughputTrend(jobMetrics) {
    const current = jobMetrics.total || 0;
    const baseline = this.baselineThroughput;
    
    if (current > baseline * 1.1) return 'increasing';
    if (current < baseline * 0.9) return 'decreasing';
    return 'stable';
  }

  /**
   * Calculate efficiency score
   */
  calculateEfficiencyScore(jobMetrics, systemHealth) {
    const successRate = jobMetrics.success_rate || 0;
    const resourceUtilization = (systemHealth.cpu_usage + systemHealth.memory_usage) / 2 || 0;
    
    // High success rate with low resource usage = high efficiency
    const efficiency = (successRate * (100 - resourceUtilization)) / 100;
    return Math.round(efficiency);
  }

  /**
   * Get performance KPIs for display
   */
  getPerformanceKPIs(data) {
    const jobMetrics = data.job_metrics || {};
    const responseTime = data.performance_metrics?.avg_response_time || 1.2;
    const slaCompliance = this.calculateSLACompliance(jobMetrics.success_rate);
    
    return [
      {
        id: 'sla-compliance',
        title: 'SLA Compliance',
        value: `${slaCompliance}%`,
        target: `${this.targetSLA}%`,
        trend: this.getEnterpriseTrend(slaCompliance, this.targetSLA, 'sla'),
        icon: '📊',
        status: slaCompliance >= this.targetSLA ? 'success' : 
                slaCompliance >= 90 ? 'warning' : 'danger',
        thresholds: {
          danger: 90,
          warning: 93,
          success: 95
        },
        actions: [
          {
            label: 'View SLA Report',
            action: 'viewSLAReport'
          },
          {
            label: 'Adjust Thresholds',
            action: 'adjustSLAThresholds'
          }
        ]
      },
      {
        id: 'response-time',
        title: 'Avg Response Time',
        value: `${responseTime.toFixed(1)}s`,
        target: '< 2.0s',
        trend: this.getEnterpriseTrend(responseTime, 2.0, 'response', true),
        icon: '⚡',
        status: responseTime <= 1.5 ? 'success' : 
                responseTime <= 2.0 ? 'warning' : 'danger',
        thresholds: {
          danger: 2.5,
          warning: 2.0,
          success: 1.5
        },
        actions: [
          {
            label: 'Optimize Performance',
            action: 'optimizePerformance'
          }
        ]
      },
      {
        id: 'throughput',
        title: 'Daily Throughput',
        value: jobMetrics.total?.toLocaleString() || '0',
        target: '1,000+',
        trend: this.getThroughputTrendIndicator(this.calculateThroughputTrend(jobMetrics)),
        icon: '📈',
        status: jobMetrics.total >= 1000 ? 'success' : 
                jobMetrics.total >= 500 ? 'warning' : 'danger',
        thresholds: {
          danger: 500,
          warning: 750,
          success: 1000
        }
      },
      {
        id: 'system-health',
        title: 'System Health',
        value: `${this.calculateSystemLoadScore(data.system_health || {}, data.queue_status || {})}%`,
        target: '> 80%',
        trend: this.getSystemHealthTrend(this.calculateSystemLoadScore(data.system_health || {}, data.queue_status || {})),
        icon: '🏥',
        status: this.calculateSystemLoadScore(data.system_health || {}, data.queue_status || {}) >= 80 ? 'success' : 
                this.calculateSystemLoadScore(data.system_health || {}, data.queue_status || {}) >= 60 ? 'warning' : 'danger',
        thresholds: {
          danger: 60,
          warning: 75,
          success: 80
        }
      }
    ];
  }

  /**
   * Get usage statistics KPIs
   */
  getUsageKPIs(data) {
    const jobMetrics = data.job_metrics || {};
    const activeUsers = data.active_users || 45;
    const jobTypes = data.job_types || [];
    
    return [
      {
        id: 'daily-volume',
        title: 'Daily Job Volume',
        value: jobMetrics.total?.toLocaleString() || '0',
        target: '1,000',
        trend: this.getThroughputTrendIndicator(this.calculateThroughputTrend(jobMetrics)),
        icon: '📊',
        status: jobMetrics.total >= 1000 ? 'success' : 
                jobMetrics.total >= 500 ? 'warning' : 'danger'
      },
      {
        id: 'active-users',
        title: 'Active Users',
        value: activeUsers.toString(),
        target: '50',
        trend: activeUsers > 50 ? '↑ Above average' : '→ Normal',
        icon: '👥',
        status: activeUsers >= 40 ? 'success' : 'warning'
      },
      {
        id: 'job-diversity',
        title: 'Job Types',
        value: jobTypes.length.toString(),
        target: '5+',
        trend: '→ Stable',
        icon: '🎯',
        status: jobTypes.length >= 5 ? 'success' : 'warning'
      },
      {
        id: 'peak-usage',
        title: 'Peak Hour Load',
        value: '85%',
        target: '< 90%',
        trend: '→ Manageable',
        icon: '⏰',
        status: 'success'
      }
    ];
  }

  /**
   * Get error tracking KPIs
   */
  getErrorKPIs(data) {
    const jobMetrics = data.job_metrics || {};
    const errorRate = ((jobMetrics.failed || 0) / Math.max(jobMetrics.total || 1, 1)) * 100;
    const mttr = this.calculateMTTR(jobMetrics);
    
    return [
      {
        id: 'error-rate',
        title: 'Error Rate',
        value: `${errorRate.toFixed(1)}%`,
        target: '< 5%',
        trend: errorRate < 5 ? '↓ Below target' : '↑ Above target',
        icon: '⚠️',
        status: errorRate <= 2 ? 'success' : 
                errorRate <= 5 ? 'warning' : 'danger',
        thresholds: {
          danger: 5,
          warning: 3,
          success: 2
        },
        actions: [
          {
            label: 'View Error Log',
            action: 'viewErrorLog'
          },
          {
            label: 'Root Cause Analysis',
            action: 'runRootCauseAnalysis'
          }
        ]
      },
      {
        id: 'mttr',
        title: 'Mean Time to Recovery',
        value: `${mttr} min`,
        target: '< 15 min',
        trend: mttr < 15 ? '↓ Good' : '↑ Needs improvement',
        icon: '🔧',
        status: mttr <= 10 ? 'success' : 
                mttr <= 15 ? 'warning' : 'danger',
        thresholds: {
          danger: 20,
          warning: 15,
          success: 10
        }
      },
      {
        id: 'failed-jobs',
        title: 'Failed Jobs Today',
        value: (jobMetrics.failed || 0).toString(),
        target: '< 50',
        trend: jobMetrics.failed < 50 ? '↓ Low' : '↑ High',
        icon: '❌',
        status: jobMetrics.failed <= 25 ? 'success' : 
                jobMetrics.failed <= 50 ? 'warning' : 'danger'
      },
      {
        id: 'error-types',
        title: 'Unique Error Types',
        value: '5',
        target: '< 10',
        trend: '→ Stable',
        icon: '📝',
        status: 'success'
      }
    ];
  }

  /**
   * Get capacity planning KPIs
   */
  getCapacityKPIs(data) {
    const systemHealth = data.system_health || {};
    const queueMetrics = data.queue_status || {};
    const workerUtilization = ((systemHealth.active_workers || 0) / Math.max(systemHealth.total_workers || 1, 1)) * 100;
    
    return [
      {
        id: 'cpu-usage',
        title: 'CPU Usage',
        value: `${systemHealth.cpu_usage || 0}%`,
        target: '< 80%',
        trend: systemHealth.cpu_usage < 80 ? '→ Normal' : '↑ High',
        icon: '💻',
        status: systemHealth.cpu_usage <= 60 ? 'success' : 
                systemHealth.cpu_usage <= 80 ? 'warning' : 'danger',
        thresholds: {
          danger: 80,
          warning: 70,
          success: 60
        }
      },
      {
        id: 'memory-usage',
        title: 'Memory Usage',
        value: `${systemHealth.memory_usage || 0}%`,
        target: '< 85%',
        trend: systemHealth.memory_usage < 85 ? '→ Normal' : '↑ High',
        icon: '🧠',
        status: systemHealth.memory_usage <= 70 ? 'success' : 
                systemHealth.memory_usage <= 85 ? 'warning' : 'danger',
        thresholds: {
          danger: 85,
          warning: 75,
          success: 70
        }
      },
      {
        id: 'queue-depth',
        title: 'Queue Depth',
        value: (queueMetrics.total_queued || 0).toString(),
        target: '< 100',
        trend: queueMetrics.total_queued < 100 ? '→ Manageable' : '↑ Growing',
        icon: '📦',
        status: queueMetrics.total_queued <= 50 ? 'success' : 
                queueMetrics.total_queued <= 100 ? 'warning' : 'danger'
      },
      {
        id: 'worker-utilization',
        title: 'Worker Utilization',
        value: `${workerUtilization.toFixed(0)}%`,
        target: '70-85%',
        trend: workerUtilization >= 70 && workerUtilization <= 85 ? '→ Optimal' : '⚠️ Check',
        icon: '⚙️',
        status: workerUtilization >= 70 && workerUtilization <= 85 ? 'success' : 
                workerUtilization >= 50 ? 'warning' : 'danger'
      }
    ];
  }

  /**
   * Get enterprise trend indicator
   */
  getEnterpriseTrend(current, target, metric, inverse = false) {
    const variance = Math.abs((current - target) / target);
    
    if (variance < 0.02) return '→ On Target';
    
    const better = inverse ? current < target : current > target;
    
    if (better) {
      return variance > 0.1 ? '↑ Exceeding' : '↗ Above Target';
    } else {
      return variance > 0.1 ? '↓ Below Target' : '↘ Slightly Below';
    }
  }

  /**
   * Get throughput trend indicator
   */
  getThroughputTrendIndicator(trend) {
    switch(trend) {
      case 'increasing': return '↑ Increasing';
      case 'decreasing': return '↓ Decreasing';
      default: return '→ Stable';
    }
  }

  /**
   * Get system health trend
   */
  getSystemHealthTrend(score) {
    if (score >= 90) return '🟢 Excellent';
    if (score >= 70) return '🟡 Good';
    if (score >= 50) return '🟠 Fair';
    return '🔴 Critical';
  }

  /**
   * Calculate status variance for distribution
   */
  calculateStatusVariance(count, total, targetPercentage) {
    const actualPercentage = (count / total) * 100;
    const variance = actualPercentage - targetPercentage;
    
    return {
      actual: actualPercentage.toFixed(1),
      target: targetPercentage,
      variance: variance.toFixed(1),
      status: Math.abs(variance) <= 5 ? 'good' : 
              Math.abs(variance) <= 10 ? 'warning' : 'critical'
    };
  }

  /**
   * Get variance class for styling
   */
  getVarianceClass(variance) {
    const absVariance = Math.abs(variance);
    if (absVariance <= 5) return 'variance--good';
    if (absVariance <= 10) return 'variance--warning';
    return 'variance--critical';
  }

  /**
   * Calculate throughput from total jobs
   */
  calculateThroughput(totalJobs) {
    const hoursInDay = 24;
    return Math.round(totalJobs / hoursInDay);
  }

  /**
   * Get trend text for display
   */
  getTrendText(current, baseline, inverse = false) {
    const percentChange = ((current - baseline) / baseline) * 100;
    
    if (Math.abs(percentChange) < 5) return 'Stable';
    
    const direction = percentChange > 0 ? 'up' : 'down';
    const quality = inverse ? 
      (percentChange > 0 ? 'worse' : 'better') : 
      (percentChange > 0 ? 'better' : 'worse');
    
    return `${Math.abs(percentChange).toFixed(0)}% ${direction} (${quality})`;
  }

  /**
   * Format duration in seconds to readable format
   */
  formatDuration(seconds) {
    if (seconds < 60) return `${seconds}s`;
    if (seconds < 3600) return `${Math.floor(seconds / 60)}m ${seconds % 60}s`;
    return `${Math.floor(seconds / 3600)}h ${Math.floor((seconds % 3600) / 60)}m`;
  }

  /**
   * Calculate data completeness percentage
   */
  calculateDataCompleteness(data) {
    const requiredFields = [
      'job_metrics',
      'system_health',
      'queue_status',
      'performance_metrics',
      'worker_status'
    ];
    
    let available = 0;
    let totalFields = 0;
    
    requiredFields.forEach(field => {
      if (data[field]) {
        available++;
        const subFields = Object.keys(data[field]);
        totalFields += subFields.length;
        
        subFields.forEach(subField => {
          if (data[field][subField] === null || data[field][subField] === undefined) {
            totalFields--;
          }
        });
      }
    });
    
    const completeness = (available / requiredFields.length) * 100;
    return Math.round(completeness);
  }

  /**
   * Get capacity status class based on usage
   */
  getCapacityStatusClass(percentage, threshold) {
    if (percentage >= threshold) return 'critical';
    if (percentage >= threshold * 0.8) return 'warning';
    if (percentage >= threshold * 0.6) return 'normal';
    return 'low';
  }

  /**
   * Get capacity status icon
   */
  getCapacityStatusIcon(statusClass) {
    switch(statusClass) {
      case 'critical': return '🔴';
      case 'warning': return '🟡';
      case 'normal': return '🟢';
      default: return '⚪';
    }
  }

  /**
   * Get capacity recommendation based on status
   */
  getCapacityRecommendation(statusClass, metricName) {
    switch(statusClass) {
      case 'critical':
        return `⚠️ ${metricName} is at critical levels. Immediate scaling recommended.`;
      case 'warning':
        return `📊 ${metricName} approaching limits. Consider scaling soon.`;
      case 'normal':
        return `✅ ${metricName} is at healthy levels.`;
      default:
        return `💡 ${metricName} has significant spare capacity.`;
    }
  }

  /**
   * Format capacity value with units
   */
  formatCapacityValue(value, unit) {
    if (unit === 'GB' && value > 1000) {
      return `${(value / 1000).toFixed(1)} TB`;
    }
    return `${value} ${unit}`;
  }

  /**
   * Generate key findings from analytics data
   */
  generateKeyFindings(data) {
    const findings = [];
    const jobMetrics = data.job_metrics || {};
    const systemHealth = data.system_health || {};
    
    // Performance findings
    if (jobMetrics.success_rate && jobMetrics.success_rate < 95) {
      findings.push(`Success rate (${jobMetrics.success_rate}%) is below SLA target`);
    }
    
    // System health findings
    if (systemHealth.cpu_usage > 80) {
      findings.push(`High CPU usage detected (${systemHealth.cpu_usage}%)`);
    }
    
    if (systemHealth.memory_usage > 85) {
      findings.push(`Memory usage is critical (${systemHealth.memory_usage}%)`);
    }
    
    // Queue findings
    const queueDepth = data.queue_status?.total_queued || 0;
    if (queueDepth > 100) {
      findings.push(`Queue backlog detected (${queueDepth} jobs waiting)`);
    }
    
    return findings;
  }

  /**
   * Generate recommendations based on data
   */
  generateRecommendations(data) {
    const recommendations = [];
    const jobMetrics = data.job_metrics || {};
    const systemHealth = data.system_health || {};
    
    // Performance recommendations
    if (jobMetrics.failed > 50) {
      recommendations.push({
        priority: 'high',
        category: 'performance',
        action: 'Investigate root cause of job failures',
        impact: 'Could improve success rate by 10-15%'
      });
    }
    
    // Capacity recommendations
    if (systemHealth.cpu_usage > 70) {
      recommendations.push({
        priority: 'medium',
        category: 'capacity',
        action: 'Consider adding more processing workers',
        impact: 'Would reduce queue wait times'
      });
    }
    
    if (systemHealth.memory_usage > 75) {
      recommendations.push({
        priority: 'high',
        category: 'capacity',
        action: 'Increase memory allocation or optimize memory usage',
        impact: 'Prevent out-of-memory errors'
      });
    }
    
    return recommendations;
  }
}