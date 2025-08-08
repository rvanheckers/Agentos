/**
 * JobsQueueHelpProvider - Help Content voor Jobs & Queue View
 * 
 * Complete help content met metaforen en jip-en-janneke uitleg voor job management.
 * Jobs & Queue focus: Job lifecycle, filtering, troubleshooting, pipeline management.
 * 
 * Content Structure:
 * - Jobs als "Projecten" metafoor
 * - Queue als "Werk Wachtrij" 
 * - Pipeline als "Productielijn"
 * - Diagnostische workflows voor veelvoorkomende job problemen
 * - Filter system uitleg
 * 
 * Created: 4 Augustus 2025
 * Based on: JobHistory.js v2.7.0 + Help System Architecture
 */

export const JobsQueueHelpProvider = {
  /**
   * Get help content voor specific component
   * @param {string} componentId - Component identifier or null voor all help
   * @returns {object} Help content object
   */
  getHelp(componentId = null) {
    // Get dynamic data from current view
    const totalJobs = window.jobHistory ? window.jobHistory.jobs?.length || 0 : 0;
    const currentFilter = window.jobHistory ? window.jobHistory.currentFilter?.preset || 'all' : 'all';
    const itemsPerPage = window.jobHistory ? window.jobHistory.itemsPerPage : 20;
    
    const helpContent = {
      // Jobs Overview - main section help
      'jobs_overview': {
        beginner: {
          title: "Jobs & Queue - Project Overzicht",
          praktisch: `Dit is je 'Project Overzicht' waar je alle video verwerkings opdrachten kunt zien. Je hebt momenteel ${totalJobs} jobs in verschillende stadia. Elke job is een project dat door de automatiserings productielijn gaat.`,
          wat_te_doen: [
            "📥 Queued = Project wacht op beurt (net ingediend)",
            "⚡ Processing = Wordt verwerkt (team is bezig)",
            "✅ Completed = Klaar en succesvol (project afgerond)",
            "❌ Failed = Mislukt (project vastgelopen, actie nodig)",
            "📊 Klik op job voor details en logs"
          ]
        },
        intermediate: {
          title: "Jobs & Queue - Pipeline Management",
          praktisch: `Job processing pipeline met ${itemsPerPage} jobs per pagina voor optimale performance. Huidige filter: ${currentFilter}. Jobs doorlopen gestructureerde workflow chains via Celery task queue.`,
          technisch: "Jobs utilize Celery distributed task processing with PostgreSQL persistence and Redis queue management",
          metrics: [
            "Processing time: <2min normaal, >10min onderzoeken",
            "Success rate: >95% gezond, <90% systematisch probleem",
            "Queue length: <10 goed, >50 bottleneck indicatie",
            "Worker capacity: 20 parallelle jobs (5 workers × 4 concurrency)"
          ]
        }
      },

      // Job Pipeline - status explanation
      'job_pipeline': {
        beginner: {
          title: "Job Statuses - Project Fasen",
          praktisch: `Jobs zijn net als projecten die verschillende fasen doorlopen. Je ziet hier ${totalJobs} jobs in verschillende stadia van de automatiserings productielijn.`,
          wat_te_doen: [
            "📥 Queued = Wacht op beurt (net nieuw project aangemaakt)",
            "⚡ Processing = Wordt verwerkt (automatiserings team is bezig)", 
            "✅ Completed = Klaar en succesvol (project volledig afgerond)",
            "❌ Failed = Mislukt (project vastgelopen, handmatige actie nodig)",
            "🚫 Cancelled = Gestopt door gebruiker (definitief)"
          ]
        },
        intermediate: {
          title: "Job Lifecycle Management - Technical Pipeline",
          praktisch: `Job state transitions via Celery task queue: queued → processing → completed/failed. State persistence in PostgreSQL met real-time updates via WebSocket.`,
          technisch: "Jobs progress through: Task Creation → Queue Assignment → Worker Processing → Result Storage → UI Update",
          metrics: [
            "Queued duration: <1min normaal (afhankelijk van worker beschikbaarheid)",
            "Processing phases: Download → Transcribe → Analyze → Crop → Cut → Complete",
            "State transitions: Atomic updates met rollback on failure",
            "Retry mechanism: Max 3 attempts met exponential backoff"
          ]
        }
      },

      // Smart Filters - filter system explanation  
      'job_filters': {
        beginner: {
          title: "Smart Filters - Job Sortering",
          praktisch: "Filters helpen je snel de juiste jobs te vinden, net als sorteerkasten voor verschillende project types. Geen gedoe met ingewikkelde zoekopdrachten.",
          wat_te_doen: [
            "⚡ Active Jobs = Alle lopende projecten (queued + processing)",
            "⚠️ Failed Jobs = Mislukte projecten die aandacht nodig hebben",
            "✅ Completed = Afgeronde projecten van laatste tijd", 
            "📊 All Jobs = Alle projecten samen (volledig overzicht)",
            "🧹 Clear All = Reset alle filters naar standaard weergave"
          ]
        },
        intermediate: {
          title: "Advanced Filtering - Query Optimization", 
          praktisch: "Context-aware filtering met preset optimization voor verschillende job management workflows. Filters gebruiken database indexes voor snelle resultaten.",
          technisch: "Client-side filtering combined met server-side pagination for large datasets",
          metrics: [
            "Filter response: <100ms voor goede UX ervaring",
            "Index usage: Status + created_at indexes for fast queries",
            "State persistence: Filter keuzes bewaard in browser sessie",
            "Memory efficiency: Only visible jobs loaded in DOM"
          ]
        }
      },

      // Pipeline Metrics - performance indicators
      'pipeline_metrics': {
        beginner: {
          title: "Pipeline Overview - Job Verwerkings Dashboard",
          praktisch: "Productielijn dashboard van je fabriek. Toont hoe de lopende band presteert.",
          wat_te_doen: [
            "📋 Total Jobs = Producten op de lopende band sinds opstart",
            "⚡ Active Jobs = Producten die nu door werknemers worden gemaakt", 
            "🎯 Success Rate = Percentage producten dat goed afkomt",
            "⏱️ Avg Processing = Gemiddelde tijd per product op de productielijn"
          ]
        },
        intermediate: {
          title: "Pipeline Performance - Real-time KPI Monitoring",
          praktisch: "Real-time pipeline metrics voor operationele monitoring. Toont throughput, success rates en processing load van het job processing systeem.",
          technisch: "Metrics aggregated from PostgreSQL job data met real-time updates via WebSocket",
          metrics: [
            "📋 Total Jobs: Cumulative count van alle jobs in systeem database",
            "⚡ Active Jobs: Current processing count (queued + processing status)",
            "🎯 Success Rate: Completed/(Completed + Failed) × 100% over recent period",
            "⏱️ Avg Processing: Mean completion time from queued → completed status",
            "Pipeline Health: >90% success rate + <2min avg processing = optimal"
          ]
        }
      },

      // Individual metric card help content
      'jobs_queue_total_jobs': {
        beginner: {
          title: "Alle Jobs Totaal - Complete Werklast",
          praktisch: `Dit toont alle ${totalJobs} jobs in je systeem (historisch). Verschil met Dashboard: Dashboard toont alleen "vandaag", dit toont alle jobs ooit.`,
          wat_te_doen: [
            "📋 Alle jobs samen = Complete geschiedenis van al je projecten",
            "📈 Hoog getal = Veel activiteit, systeem wordt goed gebruikt",  
            "📉 Laag getal = Weinig gebruik of nieuw systeem",
            "🔍 Voor dagelijkse status: kijk naar Dashboard 'Today's Jobs'"
          ]
        },
        intermediate: {
          title: "All-time Jobs Metric - Historical Volume Analysis", 
          praktisch: "Historical job count voor trend analysis en capacity planning. Toont cumulative workload over complete database.",
          technisch: "COUNT(*) query over jobs table, cached voor performance",
          metrics: [
            "Trend analysis: Track growth patterns over time",
            "Capacity planning: Historical peak loads vs current capacity", 
            "Usage patterns: Job distribution over days/weeks"
          ]
        }
      },

      'jobs_queue_active_jobs': {
        beginner: {
          title: "Actieve Jobs - Wat Draait Er Nu",
          praktisch: "Jobs die NU bezig zijn met verwerken. Dit zijn je 'lopende projecten' die nog niet klaar zijn.",
          wat_te_doen: [
            "⚡ 0-5 jobs = Rustig, systeem heeft capaciteit over",
            "🟡 6-10 jobs = Normale drukte, systeem loopt lekker", 
            "🔴 >10 jobs = Druk, mogelijk wachttijden",
            "💡 Te veel jobs? Overweeg meer workers toevoegen"
          ]
        },
        intermediate: {
          title: "Active Jobs Load Monitoring - Real-time Capacity",
          praktisch: "Current processing load indicator voor worker capacity management. Toont real-time queue depth.",
          technisch: "SUM(status IN ['processing', 'queued']) real-time query",  
          metrics: [
            "Load balancing: Distribute work across available workers",
            "Scaling triggers: >10 jobs = consider horizontal scaling",
            "Response time impact: High load = longer queue times"
          ]
        }
      },

      'jobs_queue_success_rate': {
        beginner: {
          title: "Succes Percentage - Hoe Goed Werkt Het",
          praktisch: "Percentage jobs dat goed afkomt. Dit toont hoe betrouwbaar je systeem is over alle tijd.",
          wat_te_doen: [
            "🟢 >90% = Uitstekend, systeem werkt zeer goed",
            "🟡 70-90% = Goed, normale prestaties",
            "🔴 <70% = Aandacht nodig, veel problemen",
            "📊 Verschil met Dashboard: Dit is historisch, Dashboard is van vandaag"
          ]
        },
        intermediate: {
          title: "Overall Success Rate - Pipeline Reliability KPI",
          praktisch: "Historical success rate voor pipeline reliability assessment. Key performance indicator voor system health.",
          technisch: "Completed/(Completed+Failed) × 100% over all historical data",
          metrics: [
            "Reliability trending: Monitor changes over time periods",
            "Service level objectives: Target >95% voor production readiness",
            "Failure analysis: Identify patterns in unsuccessful jobs"
          ]
        }
      },

      'jobs_queue_avg_processing': {
        beginner: {
          title: "Gemiddelde Verwerkingstijd - Hoe Snel Gaat Het", 
          praktisch: "Hoe lang jobs gemiddeld nodig hebben om klaar te komen. Dit is de 'snelheid van je fabriek'.",
          wat_te_doen: [
            "🟢 <2 min = Supersnel, systeem is geoptimaliseerd",
            "🟡 2-5 min = Normale snelheid, acceptabele prestaties",
            "🔴 >5 min = Langzaam, mogelijk optimalisatie nodig",
            "📊 Verschil met Dashboard: Dit is historisch gemiddelde"
          ]
        },
        intermediate: {
          title: "Historical Processing Time - Performance Benchmark",
          praktisch: "Long-term processing time average voor performance trending en bottleneck identification.",
          technisch: "AVG(completed_at - created_at) voor alle completed jobs",
          metrics: [
            "Performance trending: Track improvements/degradations over time",
            "Capacity planning: Processing time × job volume = resource needs", 
            "SLA compliance: Target processing time benchmarks"
          ]
        }
      }
    };

    // Add diagnostics scenarios for troubleshooting
    if (componentId === 'job_troubleshooting' || componentId === null) {
      helpContent['job_troubleshooting'] = {
        beginner: {
          title: "Problemen Oplossen - Veelvoorkomende Situaties",
          scenarios: [
            {
              symptoom: "Job blijft hangen op 'processing' status",
              oorzaken: [
                "Worker crash tijdens verwerking",
                "Externe API timeouts (YouTube/AI services)",
                "Beschadigd input bestand"
              ],
              oplossingen: [
                "Wacht 10 minuten - soms herstelt het automatisch",
                "Cancel de job en probeer retry met andere bron",
                "Check System Dashboard voor worker status",
                "Contact support als probleem blijft bestaan"
              ]
            },
            {
              symptoom: "Veel jobs krijgen 'failed' status", 
              oorzaken: [
                "API rate limits overschreden",
                "Specifieke tools hebben problemen",
                "Verkeerde input formaten"
              ],
              oplossingen: [
                "Bij API limits: wacht 1 uur en probeer opnieuw",
                "Check error messages voor specifieke fouten",
                "Gebruik ondersteunde video formaten (MP4, WebM)",
                "Probeer jobs in kleinere batches"
              ]
            },
            {
              symptoom: "Filter toont geen resultaten",
              oorzaken: [
                "Verkeerde filter combinatie",
                "Jobs zijn te oud voor huidige filter",
                "Alle jobs hebben andere status dan filter"
              ],
              oplossingen: [
                "Klik 'Clear All' om alle filters te resetten",
                "Probeer 'All Jobs' filter voor volledig overzicht",
                "Check datum range - misschien jobs van gisteren/vorige week"
              ]
            }
          ]
        },
        intermediate: {
          title: "Advanced Troubleshooting - Root Cause Analysis",
          scenarios: [
            {
              symptoom: "System performance degradation",
              oorzaken: [
                "Queue length consistently >50 jobs",
                "Worker memory leaks na lange runtime",
                "Database connection pool exhaustion",
                "Resource competition tussen workers"
              ],
              oplossingen: [
                "Scale worker instances horizontally (meer workers)",
                "Monitor resource usage patterns per worker",
                "Implement job priority queuing voor kritieke tasks",
                "Review error patterns for systematic failures",
                "Check PostgreSQL connection pool status"
              ]
            },
            {
              symptoom: "High failure rate voor specific job types",
              oorzaken: [
                "External service availability issues",
                "Resource limitations voor memory-intensive jobs",
                "Configuration drift in agent parameters"
              ],
              oplossingen: [
                "Implement circuit breakers voor external API calls",
                "Configure resource limits per job type",
                "Monitor agent success rates per type",
                "Implement gradual rollout voor agent updates"
              ]
            }
          ]
        }
      };
    }

    return componentId ? { [componentId]: helpContent[componentId] } : helpContent;
  }
};