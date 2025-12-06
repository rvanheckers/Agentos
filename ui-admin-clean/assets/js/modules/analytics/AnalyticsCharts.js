/**
 * AnalyticsCharts Module
 * Handles all chart rendering and management for Analytics dashboard
 */

export class AnalyticsCharts {
  constructor() {
    this.charts = new Map(); // Store Chart.js instances
    this.chartColors = {
      primary: '#4C6EF5',
      secondary: '#51CF66', 
      warning: '#FFD43B',
      danger: '#FF6B6B',
      info: '#339AF0',
      success: '#51CF66'
    };
  }

  /**
   * Destroy a specific chart instance
   */
  destroyChart(chartKey) {
    if (this.charts.has(chartKey)) {
      this.charts.get(chartKey).destroy();
      this.charts.delete(chartKey);
    }
  }

  /**
   * Destroy all chart instances
   */
  destroyAllCharts() {
    for (const [key, chart] of this.charts) {
      chart.destroy();
    }
    this.charts.clear();
  }

  /**
   * Refresh all charts with animation
   */
  refreshAllCharts() {
    for (const [key, chart] of this.charts) {
      chart.update('active');
    }
  }

  /**
   * Render main performance chart
   */
  renderPerformanceChart(data) {
    console.log('🔄 renderPerformanceChart called with data:', !!data);
    const canvas = document.getElementById('performanceChart');
    if (!canvas) {
      console.warn('❌ Canvas #performanceChart not found');
      return;
    }
    console.log('✅ Canvas found:', canvas);

    this.destroyChart('performance');

    if (typeof Chart === 'undefined') {
      console.error('❌ Chart.js not available - charts will not render');
      return;
    }

    const ctx = canvas.getContext('2d');
    const chartData = this.getPerformanceChartData(data);
    console.log('📊 Chart data:', chartData);

    const chart = new Chart(ctx, {
      type: 'line',
      data: {
        labels: chartData.labels,
        datasets: [
          {
            label: 'Success Rate (%)',
            data: chartData.successRates,
            borderColor: this.chartColors.success,
            backgroundColor: `${this.chartColors.success}20`,
            yAxisID: 'percentage',
            tension: 0.3
          },
          {
            label: 'Avg Response Time (s)',
            data: chartData.responseTimes,
            borderColor: this.chartColors.info,
            backgroundColor: `${this.chartColors.info}20`,
            yAxisID: 'time',
            tension: 0.3
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            position: 'top'
          },
          tooltip: {
            mode: 'index',
            intersect: false
          }
        },
        scales: {
          x: {
            display: true,
            title: {
              display: true,
              text: 'Time Period'
            }
          },
          percentage: {
            type: 'linear',
            display: true,
            position: 'left',
            title: {
              display: true,
              text: 'Success Rate (%)'
            },
            min: 0,
            max: 100
          },
          time: {
            type: 'linear',
            display: true,
            position: 'right',
            title: {
              display: true,
              text: 'Response Time (s)'
            },
            grid: {
              drawOnChartArea: false
            }
          }
        }
      }
    });

    this.charts.set('performance', chart);
  }

  /**
   * Get performance chart data
   */
  getPerformanceChartData(data) {
    const defaultData = {
      labels: ['00:00', '04:00', '08:00', '12:00', '16:00', '20:00'],
      successRates: [98, 97, 99, 96, 98, 97],
      responseTimes: [1.2, 1.3, 1.1, 1.5, 1.3, 1.4]
    };

    if (data.performance_trends && data.performance_trends.length > 0) {
      return {
        labels: data.performance_trends.map(t => t.hour),
        successRates: data.performance_trends.map(t => t.success_rate),
        responseTimes: data.performance_trends.map(t => t.avg_response_time)
      };
    }
    
    return defaultData;
  }

  /**
   * Render status distribution pie chart
   */
  renderStatusDistribution(data) {
    const canvas = document.getElementById('statusDistributionChart');
    if (!canvas) return;

    this.destroyChart('statusDistribution');

    const ctx = canvas.getContext('2d');
    const chartData = this.getStatusDistributionData(data);

    const chart = new Chart(ctx, {
      type: 'doughnut',
      data: {
        labels: chartData.labels,
        datasets: [{
          data: chartData.values,
          backgroundColor: [
            this.chartColors.success,
            this.chartColors.warning,
            this.chartColors.danger,
            this.chartColors.info
          ],
          borderWidth: 2,
          borderColor: '#fff'
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            position: 'bottom',
            labels: {
              padding: 15,
              font: {
                size: 12
              }
            }
          },
          tooltip: {
            callbacks: {
              label: (context) => {
                const label = context.label || '';
                const value = context.parsed || 0;
                const total = context.dataset.data.reduce((a, b) => a + b, 0);
                const percentage = ((value / total) * 100).toFixed(1);
                return `${label}: ${value} (${percentage}%)`;
              }
            }
          }
        }
      }
    });

    this.charts.set('statusDistribution', chart);
  }

  /**
   * Get status distribution data
   */
  getStatusDistributionData(data) {
    if (data.job_metrics) {
      return {
        labels: ['Completed', 'Processing', 'Failed', 'Queued'],
        values: [
          data.job_metrics.completed || 0,
          data.job_metrics.processing || 0,
          data.job_metrics.failed || 0,
          data.job_metrics.queued || 0
        ]
      };
    }

    return {
      labels: ['Completed', 'Processing', 'Failed', 'Queued'],
      values: [850, 45, 25, 80]
    };
  }

  /**
   * Render processing time histogram
   */
  renderProcessingTimeChart(data) {
    const canvas = document.getElementById('processingTimeChart');
    if (!canvas) return;

    this.destroyChart('processingTime');

    const ctx = canvas.getContext('2d');
    const chartData = this.getProcessingTimeData(data);

    const chart = new Chart(ctx, {
      type: 'bar',
      data: {
        labels: chartData.labels,
        datasets: [{
          label: 'Jobs Count',
          data: chartData.values,
          backgroundColor: this.chartColors.primary,
          borderColor: this.chartColors.primary,
          borderWidth: 1
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            display: false
          },
          tooltip: {
            callbacks: {
              title: (context) => {
                return `Processing Time: ${context[0].label}`;
              },
              label: (context) => {
                return `Jobs: ${context.parsed.y}`;
              }
            }
          }
        },
        scales: {
          x: {
            title: {
              display: true,
              text: 'Processing Time (seconds)'
            }
          },
          y: {
            title: {
              display: true,
              text: 'Number of Jobs'
            },
            beginAtZero: true
          }
        }
      }
    });

    this.charts.set('processingTime', chart);
  }

  /**
   * Get processing time data
   */
  getProcessingTimeData(data) {
    if (data.processing_times) {
      return {
        labels: data.processing_times.map(t => t.range),
        values: data.processing_times.map(t => t.count)
      };
    }

    return {
      labels: ['0-10s', '10-30s', '30-60s', '60-120s', '120s+'],
      values: [450, 280, 150, 80, 40]
    };
  }

  /**
   * Render response time trend chart
   */
  renderResponseTimeChart(data) {
    const canvas = document.getElementById('responseTimeChart');
    if (!canvas) return;

    this.destroyChart('responseTime');

    const ctx = canvas.getContext('2d');
    
    const chart = new Chart(ctx, {
      type: 'line',
      data: {
        labels: ['00:00', '04:00', '08:00', '12:00', '16:00', '20:00'],
        datasets: [{
          label: 'Response Time (ms)',
          data: [120, 135, 110, 145, 130, 125],
          borderColor: this.chartColors.info,
          backgroundColor: `${this.chartColors.info}20`,
          tension: 0.3,
          fill: true
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            display: false
          }
        },
        scales: {
          y: {
            beginAtZero: true,
            title: {
              display: true,
              text: 'Response Time (ms)'
            }
          }
        }
      }
    });

    this.charts.set('responseTime', chart);
  }

  /**
   * Render SLA compliance gauge chart
   */
  renderSLAComplianceChart(data) {
    const canvas = document.getElementById('slaComplianceChart');
    if (!canvas) return;

    this.destroyChart('slaCompliance');

    const ctx = canvas.getContext('2d');
    const complianceRate = data.kpis?.sla_compliance || 95;
    
    const chart = new Chart(ctx, {
      type: 'doughnut',
      data: {
        datasets: [{
          data: [complianceRate, 100 - complianceRate],
          backgroundColor: [
            complianceRate >= 95 ? this.chartColors.success : 
            complianceRate >= 90 ? this.chartColors.warning : 
            this.chartColors.danger,
            '#f0f0f0'
          ],
          borderWidth: 0
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        rotation: -90,
        circumference: 180,
        plugins: {
          legend: {
            display: false
          },
          tooltip: {
            enabled: false
          }
        }
      }
    });

    this.charts.set('slaCompliance', chart);
  }

  /**
   * Render throughput trend chart
   */
  renderThroughputChart(data) {
    const canvas = document.getElementById('throughputChart');
    if (!canvas) return;

    this.destroyChart('throughput');

    const ctx = canvas.getContext('2d');
    
    const chart = new Chart(ctx, {
      type: 'bar',
      data: {
        labels: ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'],
        datasets: [{
          label: 'Jobs Processed',
          data: [1200, 1350, 1100, 1450, 1300, 900, 600],
          backgroundColor: this.chartColors.primary,
          borderRadius: 4
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            display: false
          }
        },
        scales: {
          y: {
            beginAtZero: true,
            title: {
              display: true,
              text: 'Jobs Processed'
            }
          }
        }
      }
    });

    this.charts.set('throughput', chart);
  }

  /**
   * Render daily jobs trend chart
   */
  renderDailyJobsChart(data) {
    const canvas = document.getElementById('dailyJobsChart');
    if (!canvas) return;

    this.destroyChart('dailyJobs');

    const ctx = canvas.getContext('2d');
    
    const chart = new Chart(ctx, {
      type: 'line',
      data: {
        labels: Array.from({length: 30}, (_, i) => `Day ${i + 1}`),
        datasets: [{
          label: 'Jobs Processed',
          data: Array.from({length: 30}, () => Math.floor(Math.random() * 500) + 800),
          borderColor: this.chartColors.primary,
          backgroundColor: `${this.chartColors.primary}20`,
          tension: 0.3,
          fill: true
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            display: false
          }
        },
        scales: {
          y: {
            beginAtZero: true,
            title: {
              display: true,
              text: 'Jobs Count'
            }
          }
        }
      }
    });

    this.charts.set('dailyJobs', chart);
  }

  /**
   * Render user activity heatmap
   */
  renderUserActivityChart(data) {
    const canvas = document.getElementById('userActivityChart');
    if (!canvas) return;

    this.destroyChart('userActivity');

    const ctx = canvas.getContext('2d');
    
    const chart = new Chart(ctx, {
      type: 'bar',
      data: {
        labels: ['00:00', '04:00', '08:00', '12:00', '16:00', '20:00'],
        datasets: [{
          label: 'Active Users',
          data: [5, 3, 25, 45, 38, 15],
          backgroundColor: this.chartColors.info,
          borderRadius: 4
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            display: false
          }
        },
        scales: {
          y: {
            beginAtZero: true,
            title: {
              display: true,
              text: 'Active Users'
            }
          }
        }
      }
    });

    this.charts.set('userActivity', chart);
  }

  /**
   * Render job types distribution chart
   */
  renderJobTypesChart(data) {
    const canvas = document.getElementById('jobTypesChart');
    if (!canvas) return;

    this.destroyChart('jobTypes');

    const ctx = canvas.getContext('2d');
    
    const chart = new Chart(ctx, {
      type: 'pie',
      data: {
        labels: ['Video Processing', 'Transcoding', 'Thumbnail', 'Analysis', 'Export'],
        datasets: [{
          data: [35, 25, 20, 15, 5],
          backgroundColor: [
            this.chartColors.primary,
            this.chartColors.secondary,
            this.chartColors.warning,
            this.chartColors.info,
            this.chartColors.danger
          ]
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            position: 'right',
            labels: {
              padding: 10,
              font: {
                size: 11
              }
            }
          }
        }
      }
    });

    this.charts.set('jobTypes', chart);
  }

  /**
   * Render peak hours heatmap
   */
  renderPeakHoursChart(data) {
    const canvas = document.getElementById('peakHoursChart');
    if (!canvas) return;

    this.destroyChart('peakHours');

    const ctx = canvas.getContext('2d');
    
    const chart = new Chart(ctx, {
      type: 'bar',
      data: {
        labels: ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'],
        datasets: [
          {
            label: 'Morning (6-12)',
            data: [120, 135, 110, 145, 130, 80, 60],
            backgroundColor: this.chartColors.info
          },
          {
            label: 'Afternoon (12-18)',
            data: [180, 195, 170, 205, 190, 120, 90],
            backgroundColor: this.chartColors.primary
          },
          {
            label: 'Evening (18-24)',
            data: [90, 85, 80, 95, 85, 140, 130],
            backgroundColor: this.chartColors.secondary
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        scales: {
          x: {
            stacked: true
          },
          y: {
            stacked: true,
            beginAtZero: true,
            title: {
              display: true,
              text: 'Jobs Processed'
            }
          }
        }
      }
    });

    this.charts.set('peakHours', chart);
  }

  /**
   * Render error rate trend chart
   */
  renderErrorRateChart(data) {
    const canvas = document.getElementById('errorRateChart');
    if (!canvas) return;

    this.destroyChart('errorRate');

    const ctx = canvas.getContext('2d');
    
    const chart = new Chart(ctx, {
      type: 'line',
      data: {
        labels: ['00:00', '04:00', '08:00', '12:00', '16:00', '20:00'],
        datasets: [{
          label: 'Error Rate (%)',
          data: [2.1, 1.8, 2.5, 3.2, 2.3, 2.0],
          borderColor: this.chartColors.danger,
          backgroundColor: `${this.chartColors.danger}20`,
          tension: 0.3,
          fill: true
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            display: false
          }
        },
        scales: {
          y: {
            beginAtZero: true,
            max: 10,
            title: {
              display: true,
              text: 'Error Rate (%)'
            }
          }
        }
      }
    });

    this.charts.set('errorRate', chart);
  }

  /**
   * Render error types distribution chart
   */
  renderErrorTypesChart(data) {
    const canvas = document.getElementById('errorTypesChart');
    if (!canvas) return;

    this.destroyChart('errorTypes');

    const ctx = canvas.getContext('2d');
    
    const chart = new Chart(ctx, {
      type: 'bar',
      data: {
        labels: ['Timeout', 'Network', 'Invalid Input', 'Processing', 'Other'],
        datasets: [{
          label: 'Error Count',
          data: [12, 8, 15, 5, 3],
          backgroundColor: [
            this.chartColors.danger,
            this.chartColors.warning,
            this.chartColors.info,
            this.chartColors.secondary,
            this.chartColors.primary
          ],
          borderRadius: 4
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        indexAxis: 'y',
        plugins: {
          legend: {
            display: false
          }
        },
        scales: {
          x: {
            beginAtZero: true,
            title: {
              display: true,
              text: 'Number of Errors'
            }
          }
        }
      }
    });

    this.charts.set('errorTypes', chart);
  }

  /**
   * Render MTTR (Mean Time To Recovery) chart
   */
  renderMTTRChart(data) {
    const canvas = document.getElementById('mttrChart');
    if (!canvas) return;

    this.destroyChart('mttr');

    const ctx = canvas.getContext('2d');
    
    const chart = new Chart(ctx, {
      type: 'line',
      data: {
        labels: ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'],
        datasets: [{
          label: 'MTTR (minutes)',
          data: [15, 12, 18, 10, 14, 11, 13],
          borderColor: this.chartColors.warning,
          backgroundColor: `${this.chartColors.warning}20`,
          tension: 0.3,
          fill: true
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            display: false
          }
        },
        scales: {
          y: {
            beginAtZero: true,
            title: {
              display: true,
              text: 'Recovery Time (minutes)'
            }
          }
        }
      }
    });

    this.charts.set('mttr', chart);
  }

  /**
   * Render resource utilization chart
   */
  renderResourceUtilChart(data) {
    const canvas = document.getElementById('resourceUtilChart');
    if (!canvas) return;

    this.destroyChart('resourceUtil');

    const ctx = canvas.getContext('2d');
    
    const chart = new Chart(ctx, {
      type: 'radar',
      data: {
        labels: ['CPU', 'Memory', 'Storage', 'Network', 'Workers'],
        datasets: [{
          label: 'Current',
          data: [75, 82, 65, 70, 88],
          borderColor: this.chartColors.primary,
          backgroundColor: `${this.chartColors.primary}20`
        }, {
          label: 'Threshold',
          data: [85, 85, 85, 85, 85],
          borderColor: this.chartColors.danger,
          backgroundColor: `${this.chartColors.danger}10`,
          borderDash: [5, 5]
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        scales: {
          r: {
            beginAtZero: true,
            max: 100,
            ticks: {
              stepSize: 20
            }
          }
        }
      }
    });

    this.charts.set('resourceUtil', chart);
  }

  /**
   * Render queue depth over time chart
   */
  renderQueueDepthChart(data) {
    const canvas = document.getElementById('queueDepthChart');
    if (!canvas) return;

    this.destroyChart('queueDepth');

    const ctx = canvas.getContext('2d');
    
    const chart = new Chart(ctx, {
      type: 'line',
      data: {
        labels: ['00:00', '04:00', '08:00', '12:00', '16:00', '20:00'],
        datasets: [{
          label: 'Queue Depth',
          data: [20, 15, 45, 80, 65, 30],
          borderColor: this.chartColors.info,
          backgroundColor: `${this.chartColors.info}20`,
          tension: 0.3,
          fill: true
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            display: false
          }
        },
        scales: {
          y: {
            beginAtZero: true,
            title: {
              display: true,
              text: 'Queue Depth'
            }
          }
        }
      }
    });

    this.charts.set('queueDepth', chart);
  }

  /**
   * Render worker load distribution chart
   */
  renderWorkerLoadChart(data) {
    const canvas = document.getElementById('workerLoadChart');
    if (!canvas) return;

    this.destroyChart('workerLoad');

    const ctx = canvas.getContext('2d');
    
    const chart = new Chart(ctx, {
      type: 'bar',
      data: {
        labels: ['Worker 1', 'Worker 2', 'Worker 3', 'Worker 4', 'Worker 5'],
        datasets: [{
          label: 'Load (%)',
          data: [85, 72, 90, 68, 78],
          backgroundColor: (context) => {
            const value = context.parsed.y;
            if (value > 85) return this.chartColors.danger;
            if (value > 70) return this.chartColors.warning;
            return this.chartColors.success;
          },
          borderRadius: 4
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            display: false
          }
        },
        scales: {
          y: {
            beginAtZero: true,
            max: 100,
            title: {
              display: true,
              text: 'Load Percentage'
            }
          }
        }
      }
    });

    this.charts.set('workerLoad', chart);
  }

  /**
   * Render forecasting trend chart
   */
  renderForecastingChart(data) {
    const canvas = document.getElementById('forecastingChart');
    if (!canvas) return;

    this.destroyChart('forecasting');

    const ctx = canvas.getContext('2d');
    
    const chart = new Chart(ctx, {
      type: 'line',
      data: {
        labels: ['Week 1', 'Week 2', 'Week 3', 'Week 4', 'Week 5', 'Week 6', 'Week 7', 'Week 8'],
        datasets: [{
          label: 'Actual',
          data: [1200, 1350, 1100, 1450, null, null, null, null],
          borderColor: this.chartColors.primary,
          backgroundColor: `${this.chartColors.primary}20`,
          tension: 0.3
        }, {
          label: 'Forecast',
          data: [null, null, null, 1450, 1520, 1580, 1650, 1700],
          borderColor: this.chartColors.secondary,
          backgroundColor: `${this.chartColors.secondary}20`,
          borderDash: [5, 5],
          tension: 0.3
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            position: 'top'
          }
        },
        scales: {
          y: {
            beginAtZero: true,
            title: {
              display: true,
              text: 'Job Volume'
            }
          }
        }
      }
    });

    this.charts.set('forecasting', chart);
  }
}