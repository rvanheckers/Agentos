/**
 * DashboardHelpProvider - Help Content voor Dashboard View
 * 
 * Complete help content met metaforen en jip-en-janneke uitleg voor alle dashboard componenten.
 * Dashboard focus: System health overview, widget explanations, troubleshooting scenarios.
 * 
 * Content Structure:
 * - Dashboard als "Control Room" metafoor
 * - Widgets als "Information Cards" 
 * - Diagnostische workflows voor veelvoorkomende problemen
 * - Quick Actions uitleg
 * 
 * Created: 4 Augustus 2025
 * Based on: Dashboard.js v2.7.0 + Help System Architecture
 */

export const DashboardHelpProvider = {
  /**
   * Get help content voor specific component
   * @param {string} componentId - Component identifier or null voor all help
   * @returns {object} Help content object
   */
  getHelp(componentId = null) {
    // Get dynamic counts from actual dashboard data
    const totalWidgets = document.querySelectorAll('.metric-card').length || 4;
    const totalQuickActions = document.querySelectorAll('.quick-action').length || 6;
    
    const helpContent = {
      // System Health Widget
      'system_health': {
        beginner: {
          title: "System Health - Systeemgezondheid Monitor",
          praktisch: `Deze 'Gezondheidsmonitor' toont of het hele AgentOS systeem goed draait. Net als een dashboard in je auto: groen = alles oké, geel = let op, rood = probleem. Hij controleert ${totalWidgets} belangrijke onderdelen van het systeem.`,
          wat_te_doen: [
            "Groene status = systeem loopt perfect",
            "Gele status = systeem werkt maar let op performance",
            "Rode status = er is een probleem, check de details",
            "Klik op widget voor meer details over welk onderdeel problemen heeft"
          ]
        },
        intermediate: {
          title: "System Health - Infrastructure Monitor",
          praktisch: `De 'Gezondheidsmonitor' controleert alle core services: API server, database verbinding, Redis queue, en WebSocket real-time updates. Combineert uptime data met resource monitoring (CPU/Memory/Disk).`,
          technisch: "Aggregates health status from API, PostgreSQL, Redis, WebSocket services + system resources",
          metrics: [
            "CPU Usage: <70% is gezond voor normale operaties",
            "Memory Usage: <80% voorkomt performance problemen",
            "Disk Usage: <85% voorkomt storage issues",
            "Service Status: Alle services moeten 'healthy' zijn"
          ]
        }
      },

      // Workers Widget
      'workers_status': {
        beginner: {
          title: "Workers - Celery Verwerkingsteam",
          praktisch: "Dit zijn je fabriek werknemers - ze werken jobs af (zoals video's naar clips, maar ook andere taken). Meer workers = snellere productie.",
          wat_te_doen: [
            "Groene status = workers zijn actief bezig met taken",
            "Gele status = workers zijn er maar doen niks (geen werk)",
            "Rode status = geen workers beschikbaar (taken blijven hangen)",
            "Bij problemen: herstart Celery workers via Quick Actions"
          ]
        },
        intermediate: {
          title: "Workers - Celery Task Processing",
          praktisch: "Celery workers voeren workflow chains uit - ze pakken taken uit Redis queues en voeren agent code uit. Workers kunnen verschillende soorten werk doen: file processing, AI analysis, data transformation. Performance hangt af van aantal workers en hun concurrency settings.",
          technisch: "Celery workers with 4 concurrency each, processing specialized queues for different workflow types",
          metrics: [
            "Active Workers: 3+ workers recommended voor production",
            "Total Capacity: ~20 parallelle taken (5 workers × 4 concurrency)",
            "Queue Distribution: Workers pakken taken van meerdere specialized queues",
            "Heartbeat: Workers rapporteren status elke 30 seconden"
          ]
        }
      },

      // Queue Widget  
      'queue_status': {
        beginner: {
          title: "Queue - Taakwachtrij",
          praktisch: "Dit is de lopende band die jobs organiseert voor workers (bijvoorbeeld video's die clips moeten worden, maar ook andere producten). Net als bij de bakker: hoeveel staan er in de rij.",
          wat_te_doen: [
            "Pending = jobs die wachten (zoals video's die clips moeten worden)",
            "Processing = jobs die nu bezig zijn", 
            "Completed = jobs die succesvol af zijn",
            "Failed = jobs die mislukt zijn (check logs)"
          ]
        },
        intermediate: {
          title: "Queue - Redis Task Distribution",
          praktisch: "Redis distribueert taken over verschillende queues om bottlenecks te voorkomen. Verschillende soorten werk krijgen eigen queues. Workers pakken taken uit de queues waar ze het beste in zijn.",
          technisch: "Redis-based task queues with specialized routing for different workflow types",
          metrics: [
            "Pending Tasks: Lage aantallen zijn gezond per queue type",
            "Processing Rate: Hangt af van worker capacity en workflow complexity",
            "Queue Health: Balanced distribution voorkomt bottlenecks",
            "Retry Logic: Failed tasks krijgen automatic retries"
          ]
        }
      },

      // Jobs Widget
      'jobs_today': {
        beginner: {
          title: "Jobs Today - Dagelijkse Productie",
          praktisch: "Dit toont hoeveel jobs er vandaag zijn verwerkt (bijvoorbeeld video's die clips werden, maar ook andere taken). Je ziet hier het dagelijkse productie overzicht.",
          wat_te_doen: [
            "Total = totaal aantal jobs vandaag (video uploads, etc.)",
            "Completed = jobs die succesvol af zijn (zoals clips die gemaakt zijn)",
            "Processing = jobs die nu bezig zijn",
            "Failed = jobs waar iets mis ging (check waarom)"
          ]
        },
        intermediate: {
          title: "Jobs Today - Daily Processing Statistics", 
          praktisch: "Dagelijkse productie statistieken tonen job lifecycle performance. Use case: video upload triggert multi-stage pipeline (download → transcribe → analyze → cut).",
          technisch: "Daily job statistics showing pipeline success rate across video processing workflow stages",
          metrics: [
            "Success Rate: >90% completion rate is gezond",
            "Average Duration: 30-120 seconden per job (video use case afhankelijk van lengte)",
            "Pipeline Stages: 6 agents moeten succesvol zijn per job",
            "Peak Hours: Monitoring voor capacity planning"
          ]
        }
      },

      // Pipeline Tools Widget (dynamisch toegevoegd)
      'pipeline_tools': {
        beginner: {
          title: "Pipeline Tools - AI Specialisten Team",
          praktisch: "Dit zijn je 'AI Specialisten' die verschillende stappen van video verwerking doen: video downloaden, geluid naar tekst maken, beste momenten vinden, video knippen. Elk specialist doet zijn eigen taak.",
          wat_te_doen: [
            "Groen = alle specialisten zijn beschikbaar en werkend",
            "Geel = sommige specialisten zijn niet actief",
            "Check welke tools ontbreken als er problemen zijn",
            "Video Processor, Audio Transcriber, AI Analyzer zijn de belangrijkste"
          ]
        },
        intermediate: {
          title: "Pipeline Tools - Agent Workflow Chain",
          praktisch: "De 'AI Specialisten' zijn gespecialiseerde agents in een sequential pipeline: VideoDownloader → AudioTranscriber → MomentDetector → FaceDetector → IntelligentCropper → VideoCutter.",
          technisch: "Specialized agents handling sequential video processing pipeline with different queue assignments",
          metrics: [
            "Agent Count: 6 core agents in production pipeline",
            "Queue Types: 4 specialized queues (video, transcription, AI, file ops)",
            "Success Rate: >95% per agent stage voor healthy pipeline",
            "Bottleneck Detection: Monitor welke agent stage het langzaamst is"
          ]
        }
      },

      // Recent Activity Section
      'recent_activity': {
        beginner: {
          title: "Recent Activity - Wat Er Gebeurt",
          praktisch: "Dit is het 'Activiteitenlogboek' dat laat zien wat er de laatste tijd gebeurd is in het systeem. Nieuwe video's, systeem updates, worker status - alles wat belangrijk is voor jou als beheerder.",
          wat_te_doen: [
            "Nieuwste activiteiten staan bovenaan",
            "Groene iconen = positieve gebeurtenissen",
            "Gele/rode iconen = problemen of waarschuwingen",
            "Gebruik dit om trends te zien in systeem gebruik"
          ]
        },
        intermediate: {
          title: "Recent Activity - System Event Log",
          praktisch: "Het 'Activiteitenlogboek' aggregeert real-time events van jobs, workers, en system health. Toont business-relevante events zoals job completions, worker scaling, en system health changes.",
          technisch: "Aggregated event log from job lifecycle, worker heartbeats, system health checks",
          metrics: [
            "Event Types: Jobs, workers, system health, user actions",
            "Retention: Laatste 5 events getoond voor overview",
            "Real-time: Events komen binnen via WebSocket updates",
            "Event Severity: Info, warning, error classification"
          ]
        }
      },

      // Quick Actions Section
      'quick_actions': {
        beginner: {
          title: "Quick Actions - Snelle Acties",
          praktisch: `Dit zijn je '${totalQuickActions} Snelle Hulp Knoppen' voor veelvoorkomende beheer taken. System Check controleert alles, Flower Dashboard toont worker details, Restart Failed probeert mislukte video's opnieuw.`,
          wat_te_doen: [
            "System Check = uitgebreide gezondheidscheck van alles",
            "Flower Dashboard = gedetailleerde worker monitoring",
            "Restart Failed = probeer mislukte jobs vandaag opnieuw",
            "Refresh Data = ververs alle cijfers handmatig"
          ]
        },
        intermediate: {
          title: "Quick Actions - Administrative Operations",
          praktisch: `De '${totalQuickActions} Snelle Hulp Knoppen' triggeren common administrative workflows. System Check = comprehensive health audit, Flower = Celery monitoring UI (localhost:5555), Restart Failed = retry logic voor failed jobs.`,
          technisch: "Administrative shortcuts for health checks, monitoring dashboards, job management, reporting",
          metrics: [
            "System Check: Tests API, database, Redis, WebSocket connectivity",
            "Flower Dashboard: Opens localhost:5555 voor detailed worker monitoring",
            "Restart Failed: Retries jobs met 'failed' status from today",
            "Daily Report: Exports job statistics en system performance"
          ]
        }
      },

      // Diagnostics - Veelvoorkomende Problemen
      'diagnostics': {
        beginner: {
          title: "System Dashboard - Fabriek Overzicht",
          praktisch: "Dit is het controlepaneel van je fabriek. Je ziet in één oogopslag hoe de productie gaat.",
          wat_te_doen: [
            "📊 System Health = Controlelampjes fabriek (groen = alles loopt goed)",
            "👥 Workers = Aantal werknemers op de fabrieksvloer", 
            "📋 Queue = Lopende band met jobs die wachten",
            "📈 Today's Jobs = Hoeveel producten vandaag af zijn",
            "⚡ Pipeline = Productielijn snelheid en efficiency",
            "🔥 Recent Activity = Live feed van fabriek activiteit",
            "⚡ Quick Actions = Fabriek bedieningsknoppen"
          ]
        },
        intermediate: {
          title: "System Dashboard - Factory Floor Management",
          praktisch: "Production facility control center voor real-time fabriek monitoring en capacity management.",
          technisch: "Real-time metrics aggregation met WebSocket updates voor factory floor optimization",
          metrics: [
            "📊 System Health: Service availability monitoring (API, DB, Redis status)",
            "👥 Workers: Process pool capacity management (concurrent job processing)",
            "📋 Queue: Conveyor belt job scheduling (FIFO/priority queue management)", 
            "📈 Today's Jobs: Daily production throughput metrics",
            "⚡ Pipeline: Production line efficiency (job completion rates)",
            "🔥 Recent Activity: Real-time factory floor event streaming"
          ]
        }
      }
    };

    // System Dashboard Overview - Main dashboard help
    helpContent.dashboard_overview = {
      beginner: {
        title: "System Dashboard - Fabriek Overzicht",
        praktisch: "Dit is het hoofdpaneel van je fabriek. Hier zie je in één oogopslag hoe alle onderdelen van het systeem presteren.",
        wat_te_doen: [
          "📊 System Health = Controlelampjes van je fabriek (groen = alles goed)",
          "👥 Workers = Werknemers die jobs afwerken",
          "📋 Queue = Lopende band met wachtende jobs",
          "📈 Jobs Today = Productie cijfers van vandaag",
          "⚡ Recent Activity = Live updates van wat er gebeurt",
          "🚀 Quick Actions = Handige knoppen voor dagelijks gebruik"
        ]
      },
      intermediate: {
        title: "System Dashboard - Production Facility Control Center",
        praktisch: "Real-time production monitoring dashboard voor complete fabriek oversight en operationele besluitvorming.",
        technisch: "Centralized monitoring hub aggregating data from all service layers via Admin SSOT pattern",
        metrics: [
          "📊 Health Monitoring: Real-time service availability tracking",
          "👥 Workforce Management: Worker capacity en job distribution",
          "📋 Production Queue: Job scheduling en throughput metrics",
          "📈 Daily Production: Performance trends en capacity planning",
          "⚡ Live Operations: Event streaming voor immediate awareness"
        ]
      }
    };

    // Return specific component help or all help
    return componentId ? { [componentId]: helpContent[componentId] } : helpContent;
  }
};