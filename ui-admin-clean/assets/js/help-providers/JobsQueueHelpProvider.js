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
    // Get dynamic data from current view (safe for SSR/tests)
    const hasWindow = typeof window !== 'undefined';
    const jobHistory = hasWindow && window.jobHistory ? window.jobHistory : null;
    const totalJobs = jobHistory?.jobs?.length ?? 0;
    const currentFilter = jobHistory?.currentFilter?.preset ?? 'all';
    const itemsPerPage = jobHistory?.itemsPerPage ?? 20;
    
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
            "Worker capacity: Dynamisch gebaseerd op configuratie (check System > Workers voor actuele capaciteit)"
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
      },

      // NEW METRICS HELP ENTRIES - Queue Management Redesign
      'queue_depth_help': {
        beginner: {
          title: "Queue Depth - Wachtrij Diepte",
          praktisch: "Aantal jobs die wachten om verwerkt te worden. Net als de wachtrij bij de bakker - hoe hoger, hoe langer je moet wachten.",
          wat_te_doen: [
            "📥 0-10 jobs = Rustige wachtrij, snelle verwerking",
            "🟡 11-20 jobs = Normale drukte, acceptabele wachttijd", 
            "🔴 >20 jobs = Lange wachtrij, overweeg meer workers",
            "💡 Hoge queue depth = Tijd om capaciteit op te schalen"
          ]
        },
        intermediate: {
          title: "Queue Depth - Pipeline Bottleneck Analysis",
          praktisch: "Real-time queue depth voor capacity planning en bottleneck detectie.",
          technisch: "Count van jobs met status 'pending' in database",
          metrics: [
            "Queue depth trends: Peak loading patterns analysis",
            "Worker utilization correlation: High depth = underutilized workers",
            "SLA impact: Queue depth directly affects processing latency"
          ]
        }
      },

      'active_processing_help': {
        beginner: {
          title: "Active Processing - Lopende Verwerking",
          praktisch: "Jobs die NU bezig zijn met verwerken. Dit zijn je actieve projecten die door het systeem lopen.",
          wat_te_doen: [
            "⚡ 0 jobs = Systeem staat stil, geen activiteit",
            "✅ 1-5 jobs = Normale activiteit, systeem werkt goed",
            "🔄 >5 jobs = Hoge activiteit, veel projecten tegelijk",
            "📊 Vergelijk met Worker Utilization voor efficiency"
          ]
        },
        intermediate: {
          title: "Active Processing - Concurrent Job Analysis",
          praktisch: "Real-time concurrent job execution monitoring voor resource management.",
          technisch: "Count van jobs met status 'processing' - actual running jobs",
          metrics: [
            "Concurrency patterns: Peak concurrent job analysis",
            "Resource utilization: Processing count vs available workers",
            "Throughput optimization: Optimal concurrent job levels"
          ]
        }
      },

      'queue_throughput_help': {
        beginner: {
          title: "Queue Throughput - Verwerkingssnelheid",
          praktisch: "Hoeveel jobs per uur je systeem afrondt. Net als auto's per uur door een tolpoort.",
          wat_te_doen: [
            "📊 0-5/hr = Laag, systeem verwerkt weinig",
            "✅ 6-20/hr = Goed, normale verwerkingssnelheid",
            "🚀 >20/hr = Excellent, zeer efficiënt systeem",
            "📈 Trend pijl toont of snelheid stijgt of daalt"
          ]
        },
        intermediate: {
          title: "Queue Throughput - Performance Optimization",
          praktisch: "Jobs/hour completion rate met trend analysis voor performance tuning.",
          technisch: "Completed jobs count per hour met rolling trend calculation",
          metrics: [
            "Throughput trends: Hourly completion rate patterns",
            "Performance correlation: Throughput vs system resource usage",
            "Capacity planning: Expected throughput under different load conditions"
          ]
        }
      },

      'success_rate_24h_help': {
        beginner: {
          title: "24h Success Rate - Dagelijkse Betrouwbaarheid", 
          praktisch: "Percentage jobs van vandaag die succesvol zijn afgerond. Toont hoe betrouwbaar je systeem vandaag presteert.",
          wat_te_doen: [
            "✅ >90% = Excellent, systeem werkt zeer betrouwbaar",
            "🟡 70-90% = Goed, maar kan beter - check failed jobs",
            "🔴 <70% = Probleem, veel jobs falen - actie nodig",
            "📅 Dagelijkse metric, verse data vs historisch gemiddelde"
          ]
        },
        intermediate: {
          title: "24h Success Rate - Pipeline Health Monitoring",
          praktisch: "Recent success rate voor pipeline health assessment en trend analysis.",
          technisch: "Completed/(Completed + Failed) × 100% voor jobs created in laatste 24h",
          metrics: [
            "Pipeline reliability: Recent success patterns vs historical baseline",
            "Quality assurance: Success rate correlation met job complexity",
            "Operational health: Daily success rate als system health indicator"
          ]
        }
      },

      'failed_today_help': {
        beginner: {
          title: "Failed Jobs Today - Vandaagse Problemen",
          praktisch: "Aantal jobs dat vandaag is mislukt. Als een dagelijkse 'problem report' voor je systeem.",
          wat_te_doen: [
            "✅ 0 failed = Perfect, geen problemen vandaag",
            "🟡 1-3 failed = Normaal, kleine problemen opgelost",
            "🔴 >3 failed = Aandacht nodig, structureel probleem",
            "🔍 Klik door naar failed jobs voor details en oplossingen"
          ]
        },
        intermediate: {
          title: "Failed Jobs Today - Error Pattern Analysis",
          praktisch: "Daily failure count voor error pattern detection en proactive maintenance.",
          technisch: "Count van jobs met status 'failed' created in laatste 24h",
          metrics: [
            "Error patterns: Daily failure trends en root cause correlation",
            "System stability: Failure rate vs normal operational baseline",
            "Proactive alerts: Failure threshold monitoring voor incident prevention"
          ]
        }
      },

      'total_jobs_help': {
        beginner: {
          title: "Total Jobs - Complete Projectenlijst",
          praktisch: "Alle jobs die ooit in je systeem zijn geweest. Toont je complete werkhistorie met verdeling per status.",
          wat_te_doen: [
            "📁 Total count = Complete geschiedenis van al je projecten", 
            "📊 Breakdown = Verdeling: hoeveel complete, failed, actief",
            "📈 Hoog totaal = Veel gebruik, systeem wordt goed benut",
            "🎯 Status verdeling toont overall systeem prestaties"
          ]
        },
        intermediate: {
          title: "Total Jobs - Historical Workload Analysis",
          praktisch: "Complete job inventory met status breakdown voor capacity planning.",
          technisch: "Aggregate count van alle jobs met status distribution analysis",
          metrics: [
            "Workload history: Total job volume trends over tijd",
            "Status distribution: Complete vs failed vs active job ratios",
            "Capacity utilization: Total workload vs system capacity over time"
          ]
        }
      },

      'today_jobs_help': {
        beginner: {
          title: "Today's Jobs - Vandaagse Werkload",
          praktisch: "Alle jobs die vandaag zijn gestart. Toont je dagelijkse activiteit en hoe die verdeeld is.",
          wat_te_doen: [
            "📅 0 jobs = Rustige dag, geen nieuwe projecten",
            "✅ 1-10 jobs = Normale dag, goed tempo",
            "🚀 >10 jobs = Drukke dag, veel nieuwe projecten",
            "📊 Status breakdown toont hoe de dag verloopt"
          ]
        },
        intermediate: {
          title: "Today's Jobs - Daily Activity Monitoring",
          praktisch: "Daily job volume met status breakdown voor operational awareness.",
          technisch: "Count van jobs created vandaag met real-time status distribution",
          metrics: [
            "Daily patterns: Typical workload vs today's volume",
            "Operational tempo: Today's job creation rate analysis",
            "Performance tracking: Daily completion vs creation ratios"
          ]
        }
      },

      'worker_utilization_help': {
        beginner: {
          title: "Worker Utilization - Werknemers Bezetting",
          praktisch: "Percentage van je workers die bezig zijn. Net als bezettingsgraad van je team - hoeveel zijn er aan het werk.",
          wat_te_doen: [
            "😴 0-30% = Onderbenut, workers staan stil - meer work toewijzen",
            "✅ 31-80% = Goed, gezonde werklast verdeling",
            "🔥 81-100% = Volledig benut, overweeg meer workers toevoegen",
            "⚖️ Balanceer workload vs beschikbare capaciteit"
          ]
        },
        intermediate: {
          title: "Worker Utilization - Resource Optimization",
          praktisch: "Worker busy percentage voor resource allocation en scaling decisions.",
          technisch: "Active workers / Total workers × 100% met real-time monitoring",
          metrics: [
            "Resource efficiency: Worker utilization vs throughput correlation",
            "Scaling indicators: High utilization = scale up triggers",
            "Cost optimization: Utilization patterns voor worker pool sizing"
          ]
        }
      },

      'avg_processing_help': {
        beginner: {
          title: "Avg Processing Time - Gemiddelde Verwerkingstijd", 
          praktisch: "Hoe lang een gemiddelde job erover doet om af te komen. Toont de snelheid van je systeem.",
          wat_te_doen: [
            "⚡ <60s = Zeer snel, excellent systeem performance",
            "✅ 60-300s = Normaal, goede verwerkingssnelheid",
            "🟡 >300s = Langzaam, mogelijk performance problemen",
            "📊 Vergelijk met throughput voor complete performance beeld"
          ]
        },
        intermediate: {
          title: "Avg Processing Time - Performance Benchmarking",
          praktisch: "Mean job completion time voor performance optimization en SLA monitoring.",
          technisch: "Average (completed_at - started_at) voor completed jobs",
          metrics: [
            "Performance trends: Processing time patterns over time",
            "SLA compliance: Processing time vs configured service levels",
            "Optimization targets: Processing time reduction opportunities"
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
      }
    }

    if (componentId === null) {
      return helpContent;
    }
    if (!Object.prototype.hasOwnProperty.call(helpContent, componentId)) {
      return {};
      // of: throw new Error(`Unknown help component: ${componentId}`);
    }
    return { [componentId]: helpContent[componentId] };
  }
};