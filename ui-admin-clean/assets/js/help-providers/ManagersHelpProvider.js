/**
 * ManagersHelpProvider - Help Content voor Service Managers View
 * 
 * Complete help content met metaforen en jip-en-janneke uitleg.
 * Gebruikt de correcte service terminologie en workflow metaforen.
 * 
 * Content Structure:
 * - Technische bewoording eerst (AdminDataManager, JobsService, etc.)
 * - Daarna jip-en-janneke uitleg met metaforen
 * - Concrete acties voor gebruikers
 * - Performance metrics uitleg
 * 
 * Created: 4 Augustus 2025
 * Based on: AgentOS v2.7.0 architecture + workflow analysis
 */

export const ManagersHelpProvider = {
  /**
   * Get help content voor specific component
   * @param {string} componentId - Component identifier or null voor all help
   * @returns {object} Help content object
   */
  getHelp(componentId = null) {
    // Get dynamic counts from actual data
    const totalServices = window.managersView ? window.managersView.managers.length : 6;
    
    const helpContent = {
      // AdminDataManager - Hoofd Supervisor
      'admin_data': {
        beginner: {
          title: "AdminDataManager - Hoofd Supervisor",
          praktisch: `Dit is de 'Hoofd Supervisor' die alle teams overziet en rapporteert aan het admin dashboard. Hij verzamelt informatie van alle ${totalServices} services (inclusief zichzelf) en toont dit in één overzicht. Als deze rood is, zie je misschien geen actuele cijfers van andere services.`,
          wat_te_doen: [
            "Controleer of alle andere services groen zijn",
            "Herstart de service als hij vastloopt",
            "Kijk naar 'Details' voor meer informatie over welke data niet binnenkomt",
            "Check of database verbinding werkt (AdminDataManager heeft database nodig)"
          ]
        },
        intermediate: {
          title: "AdminDataManager - SSOT Controller",
          praktisch: `De 'Hoofd Supervisor' verzamelt data van alle ${totalServices} services elke 30 seconden via directe Python calls (geen HTTP overhead). Response tijd toont hoe snel je dashboard updates krijgt. Hij consolideert alle admin data in één SSOT (Single Source of Truth) endpoint.`,
          technisch: "SSOT (Single Source of Truth) controller - aggregeert admin UI data via service layer calls",
          metrics: [
            `Response Time: <300ms is goed (complexe aggregatie van ${totalServices} services)`,
            "CPU Usage: <25% normaal (data processing en caching)",
            "Requests/min: ~25 (dashboard updates elke 30s)",
            "Cache Hit Rate: >80% voor optimale performance"
          ]
        }
      },

      // JobsService - Project Manager  
      'jobs': {
        beginner: {
          title: "JobsService - Project Manager",
          praktisch: "Dit is de 'Project Manager' die alle video-verwerkingsprojecten beheert. Hij krijgt opdrachten van gebruikers (video uploads), maakt nieuwe projecten aan, en stuurt het werk door naar de juiste teams. Je ziet hier welke projecten draaien, klaar zijn, of mislukt zijn.",
          wat_te_doen: [
            "Groene status = alle projecten lopen goed",
            "Gele status = projecten lopen langzamer dan normaal",
            "Rode status = projecten mislukken, check de details",
            "Bij problemen: herstart de service en check database verbinding"
          ]
        },
        intermediate: {
          title: "JobsService - Job Lifecycle Manager",
          praktisch: "De 'Project Manager' beheert de hele levenscyclus van video processing jobs. Van upload tot finale clips in je resultaten grid. Hij triggert Celery workflows en houdt job status bij in PostgreSQL database.",
          technisch: "Handles job lifecycle, triggers Celery workflows, manages status updates via PostgreSQL",
          metrics: [
            "Response Time: <100ms is uitstekend (directe database ops)",
            "Success Rate: >95% is gezond voor job completion",
            "Requests/min: ~45 (job operations en status updates)",
            "Queue Depth: <10 pending jobs is optimaal"
          ]
        }
      },

      // QueueService - Werk Verdeler
      'queue': {
        beginner: {
          title: "QueueService - Werk Verdeler", 
          praktisch: "Dit is de 'Werk Verdeler' die ervoor zorgt dat taken eerlijk verdeeld worden over beschikbare workers. Hij voorkomt dat het systeem vastloopt door werk slim te verdelen. Als deze rood is, worden nieuwe taken niet meer verwerkt.",
          wat_te_doen: [
            "Check of Celery workers nog actief zijn",
            "Herstart workers als de wachtrij vastloopt",
            "Kijk naar worker status in System Health",
            "Bij lange wachtrij: voeg meer workers toe"
          ]
        },
        intermediate: {
          title: "QueueService - Task Distribution Controller",
          praktisch: "De 'Werk Verdeler' distribueert video processing tasks over Celery workers via Redis message broker. Hij coördineert tot 20 parallelle taken tegelijk (5 workers × 4 concurrency). Gebruikt verschillende queues voor verschillende soorten werk.",
          technisch: "Manages Celery task queues, worker coordination, job distribution via Redis broker",
          metrics: [
            "Response Time: <50ms is excellent (lightweight queue ops)",
            "Queue Length: <10 tasks is healthy voor elk queue type",
            "Worker Count: 5+ workers recommended voor production load",
            "Throughput: ~15 jobs/minute bij optimale configuratie"
          ]
        }
      },

      // AgentsService - (AI) Specialisten Manager
      'agents': {
        beginner: {
          title: "AgentsService - (AI) Specialisten Manager",
          praktisch: "Dit is de 'Team Manager' die een team van 6 (AI) specialisten/tools beheert die je video's verwerken. Het team bestaat uit: video downloaders, geluid-naar-tekst omzetters (AI), moment detectoren (AI), gezichtsherkenners, smart croppers, en video snijders. Als deze service problemen heeft, werken je AI tools niet.",
          wat_te_doen: [
            "Groene status = alle (AI) specialisten/tools werken",
            "Check welke tools actief zijn in Details",
            "Bij problemen: herstart specifieke (AI) tools",
            "Let op AI API limieten (Whisper, Claude) bij veel gebruik"
          ]
        },
        intermediate: {
          title: "AgentsService - Automation Pipeline Controller",
          praktisch: "De '(AI) Specialisten Manager' controleert de 6-stap automation pipeline: VideoDownloader → AudioTranscriber (AI) → MomentDetector (AI) → FaceDetector → SmartCropper → VideoCutter. Mix van AI tools (Whisper, Claude) en processing tools (FFmpeg, MediaPipe).",
          technisch: "Controls 6-stage automation pipeline: mix of AI tools and processing tools execution",
          metrics: [
            "Response Time: <75ms good (agent coordination overhead)", 
            "Active Agents: 6 core agents monitored (2 AI, 4 processing tools)",
            "Pipeline Success Rate: >90% end-to-end completion",
            "AI API Usage: Monitor Whisper/Claude rate limits"
          ]
        }
      },

      // AnalyticsService - Rapportage Specialist
      'analytics': {
        beginner: {
          title: "AnalyticsService - Rapportage Specialist",
          praktisch: "Dit is de 'Rapportage Specialist' die overzichten maakt van hoe het systeem presteert. Hij telt hoeveel video's zijn verwerkt, hoeveel zijn gelukt, en hoe snel alles gaat. Deze rapporten zijn handig voor management updates en het spotten van problemen.",
          wat_te_doen: [
            "Bekijk Dashboard voor overzicht statistieken",
            "Check trends om problemen vroeg te spotten", 
            "Export rapporten voor management updates",
            "Monitor success rates om kwaliteit te bewaken"
          ]
        },
        intermediate: {
          title: "AnalyticsService - Performance Reporting Engine",
          praktisch: "De 'Rapportage Specialist' genereert real-time performance metrics, success rates, error analysis en system health reports. Hij analyseert PostgreSQL data om trends te identificeren en management dashboards te voeden.",
          technisch: "Provides performance metrics, reporting, system analytics via PostgreSQL aggregation queries",
          metrics: [
            "Response Time: <140ms acceptable (complex metric calculations)",
            "Data Points: 1000+ jobs analyzed voor trend berekeningen",
            "Report Generation: <5s voor standard management reports",
            "Data Retention: 30 dagen detailed, 1 jaar aggregated"
          ]
        }
      },

      // DatabaseManager - Archivaris
      'database': {
        beginner: {
          title: "DatabaseManager - Archivaris",
          praktisch: "Dit is de 'Archivaris' die alle belangrijke informatie bewaart: gebruikers, video's, resultaten, en systeemlogboeken. Alles wat AgentOS doet wordt hier opgeslagen. Als deze rood is, kunnen geen gegevens worden opgeslagen en gaat er informatie verloren!",
          wat_te_doen: [
            "Rode status = kritiek! Backup je data direct",
            "Check database schijfruimte (PostgreSQL heeft ruimte nodig)",
            "Herstart PostgreSQL service bij verbindingsproblemen", 
            "Monitor connection pool - te veel connections kunnen problemen geven"
          ]
        },
        intermediate: {
          title: "DatabaseManager - PostgreSQL Operations Controller",
          praktisch: "De 'Archivaris' beheert production PostgreSQL met connection pooling (50 total connections). Hij bewaart alle kritische data: jobs, users, clips, processing steps, system events. Gebruikt 21+ indexes voor optimale query performance.",
          technisch: "Handles PostgreSQL operations, connection pooling, optimized queries met 21+ performance indexes",
          metrics: [
            "Response Time: <35ms excellent (direct database operations)",
            "Connection Pool: 20 base + 30 overflow connections beschikbaar",
            "Query Performance: <50ms gemiddeld voor complex queries",
            "Storage Growth: ~500MB/maand bij normale usage"
          ]
        }
      }
    };

    // Add metrics help sections
    helpContent.response_time = {
      beginner: {
        title: "Response Time - Reactietijd",
        praktisch: "Dit toont hoe snel een service reageert op verzoeken. Net als wachttijd in een restaurant - hoe lager, hoe beter!",
        wat_te_doen: [
          "Onder 100ms = Uitstekend (zeer responsief)",
          "100-300ms = Goed (normaal gebruik)",
          "300-1000ms = Traag (kan verbetering gebruiken)",
          "Boven 1000ms = Probleem (onderzoek nodig)"
        ]
      },
      intermediate: {
        title: "Response Time - Performance Analysis",
        praktisch: "Response time meet de tijd tussen request en response. Critical performance indicator voor user experience en system health.",
        technisch: "Measured from request initiation to response completion, includes processing + network latency",
        metrics: [
          "P50 (median): Typical response time voor 50% van requests",
          "P95: Response time voor 95% van requests (outlier detection)",
          "Network latency: 5-50ms typical binnen datacenter",
          "Processing time: Service-specific, database-dependent"
        ]
      }
    };

    helpContent.success_rate = {
      beginner: {
        title: "Success Rate - Succespercentage",
        praktisch: "Hoeveel procent van de taken succesvol worden afgerond. Als een bakker: hoeveel broden lukken er van de 100?",
        wat_te_doen: [
          "95-100% = Uitstekend (bijna alles lukt)",
          "90-95% = Goed (acceptabel voor productie)",
          "80-90% = Matig (onderzoek problemen)",
          "Onder 80% = Kritiek (directe actie vereist)"
        ]
      },
      intermediate: {
        title: "Success Rate - Error Rate Analysis",
        praktisch: "Success rate berekent percentage successful operations vs total operations. Key reliability metric voor service health monitoring.",
        technisch: "Calculated as (successful_requests / total_requests) * 100, measured over time windows",
        metrics: [
          "HTTP 2xx responses = Success (200, 201, 204)",
          "HTTP 4xx/5xx responses = Failure (400, 404, 500, 503)",
          "Timeout exceptions = Failure (circuit breaker trips)",
          "SLA targets: 99.9% uptime = 8.76 hours downtime/year"
        ]
      }
    };

    helpContent.requests_per_min = {
      beginner: {
        title: "Requests/min - Verzoeken per Minuut",
        praktisch: "Hoeveel verzoeken de service per minuut verwerkt. Als een kassier: hoeveel klanten per minuut kunnen ze helpen?",
        wat_te_doen: [
          "Hoge waarde = Service is druk bezig",
          "Lage waarde = Service heeft weinig te doen",
          "Plotse stijging = Mogelijk probleem of piekbelasting",
          "Nul verzoeken = Service mogelijk offline"
        ]
      },
      intermediate: {
        title: "Requests/min - Throughput Analysis",
        praktisch: "Request rate meet throughput - aantal verzoeken verwerkt per tijdseenheid. Essential load indicator voor capacity planning.",
        technisch: "Measured as request_count / time_window, typically aggregated over 1-5 minute windows",
        metrics: [
          "Peak throughput: Maximum sustainable requests/min",
          "Average throughput: Normal operational load",
          "Load balancing: Distribute requests across instances",
          "Rate limiting: Throttle requests om overload te voorkomen"
        ]
      }
    };

    helpContent.cpu_usage = {
      beginner: {
        title: "CPU Usage - Processorgebruik",
        praktisch: "Hoeveel van de processorkracht wordt gebruikt. Als het motortoerental van een auto - te hoog betekent problemen!",
        wat_te_doen: [
          "0-50% = Gezond (voldoende reserve)",
          "50-70% = Druk maar OK (monitor trends)",
          "70-90% = Hoog (overweeg scaling)",
          "90-100% = Kritiek (directe actie, mogelijk crashes)"
        ]
      },
      intermediate: {
        title: "CPU Usage - Resource Utilization",
        praktisch: "CPU utilization meet processor load as percentage van available compute capacity. Critical resource constraint indicator.",
        technisch: "Measured as (busy_time / total_time) * 100, includes user + system + iowait time",
        metrics: [
          "User CPU: Application processing time",
          "System CPU: Kernel/OS processing time", 
          "IOWait: CPU waiting voor disk/network I/O",
          "Load average: CPU queue depth over 1/5/15 minute windows"
        ]
      }
    };

    // Add section help
    helpContent.system_overview = {
      beginner: {
        title: "System Overview - Systeemoverzicht",
        praktisch: "Dit geeft je een snelle blik op hoe het hele systeem presteert. Als het dashboard van een auto - alle belangrijke info in één oogopslag.",
        wat_te_doen: [
          "Kijk eerst naar de algemene cijfers",
          "Check hoeveel services gezond zijn (groen)",
          "Let op gemiddelde response times",
          "Monitor system load voor problemen"
        ]
      },
      intermediate: {
        title: "System Overview - Aggregate Metrics",
        praktisch: "System overview aggregeert key performance indicators across all services. Provides high-level system health snapshot voor operational monitoring.",
        technisch: "Real-time aggregation van service metrics: health checks, response times, throughput, resource usage",
        metrics: [
          "Total Services: Count van alle geregistreerde services",
          "Healthy Services: Services met status 'healthy' (success rate >95%)",
          "Average Response Time: Mean response time across all services",
          "System Load: Aggregate CPU/memory usage percentage"
        ]
      }
    };

    helpContent.business_services = {
      beginner: {
        title: "Core Business Services - Hoofddiensten",
        praktisch: `Dit zijn de ${totalServices} hoofdteams die al het werk doen in AgentOS. Elke service heeft een eigen specialiteit, net als afdelingen in een bedrijf.`,
        wat_te_doen: [
          "AdminDataManager = Hoofd Supervisor (coördineert alles)",
          "JobsService = Project Manager (beheert video projecten)",
          "QueueService = Werk Verdeler (verdeelt taken)",
          "AgentsService = (AI) Specialisten Manager (6 AI tools)",
          "AnalyticsService = Rapportage Specialist (maakt overzichten)",
          "DatabaseManager = Archivaris (bewaart alle data)"
        ]
      },
      intermediate: {
        title: "Core Business Services - Service Architecture",
        praktisch: "Core business services implementeren de domain logic van AgentOS video processing platform. Each service owns specific business capabilities.",
        technisch: "Microservices architecture met service layer pattern, each service handles specific domain responsibilities",
        metrics: [
          "Service Layer Pattern: Direct Python calls, geen HTTP overhead",
          "Domain Separation: Each service owns specific business logic",
          "SSOT Architecture: AdminDataManager aggregates all service data",
          "Fault Isolation: Service failures don't cascade to other services"
        ]
      }
    };

    // Add general help sections
    helpContent.general = {
      beginner: {
        title: "Service Status Kleuren",
        praktisch: "Leer wat de verschillende kleuren betekenen zodat je snel problemen kunt herkennen.",
        wat_te_doen: [
          "Groen (Healthy) = Service werkt normaal, alle metrics zijn goed",
          "Geel (Warning) = Service werkt maar heeft performance problemen", 
          "Rood (Error) = Service heeft ernstige problemen of is offline",
          "Grijs (Unknown) = Status kon niet bepaald worden, check connectie"
        ]
      },
      intermediate: {
        title: "Performance Metrics Uitleg",
        praktisch: "Begrijp wat de performance cijfers betekenen voor systeembeheer.",
        technisch: "Key performance indicators voor production system monitoring",
        metrics: [
          "Response Time: Hoe snel service reageert (lager = beter performance)",
          "CPU Usage: Percentage processorkracht gebruikt (>80% = probleem)",
          "Success Rate: Percentage taken succesvol afgerond (>95% = gezond)",
          "Requests/min: Verzoeken per minuut verwerkt (load indicator)"
        ]
      }
    };

    // Business Service Layers help
    helpContent.diagnostics = {
      beginner: {
        title: "Business Service Layers - Fabriek Afdelingen",
        praktisch: "Dit zijn de verschillende afdelingen van je fabriek. Elke afdeling heeft een specifieke taak om jobs af te werken.",
        wat_te_doen: [
          "🏢 AdminDataManager = Hoofd Supervisor die alle afdelingen overziet",
          "📋 JobsService = Project Manager die opdrachten organiseert", 
          "🔄 QueueService = Werk Verdeler die taken eerlijk verdeelt",
          "🤖 AgentsService = Team Manager van AI specialisten",
          "📊 AnalyticsService = Rapportage Specialist voor overzichten",
          "🗄️ DatabaseManager = Archivaris die alles opslaat",
          "Groene status = Afdeling werkt goed, rode status = heeft hulp nodig"
        ]
      },
      intermediate: {
        title: "Business Service Layers - Geavanceerd Overzicht",
        praktisch: "Fabriek management overzicht voor gevorderde beheerders. Toont hoe alle afdelingen samenwerken en prestaties leveren.",
        technisch: "Service layer architecture met microservice patterns voor horizontale scalability",
        metrics: [
          "🏢 Total Managers: Aantal actieve fabriek afdelingen (normaal 6)",
          "💚 Healthy Services: Afdelingen die goed presteren (target >95%)",
          "⚡ Avg Response Time: Hoe snel afdelingen reageren (<300ms optimaal)",
          "📊 CPU Usage: Resource gebruik over alle afdelingen (target <70%)",
          "🔄 Load Balancing: Work distributie over service instances"
        ]
      }
    };

    // SmartFilter help
    helpContent.smartfilter = {
      beginner: {
        title: "SmartFilter - Slim Filteren",
        praktisch: "Met SmartFilter kun je snel de services vinden die je nodig hebt. Net als zoeken in een winkel - filter op wat je wilt zien.",
        wat_te_doen: [
          "Performance → Toon alle services met prestatie-info",
          "Healthy → Alleen groene, gezonde services", 
          "Issues → Alleen services met problemen (geel/rood)",
          "Custom → Maak je eigen filter combinaties"
        ],
        use_cases: [
          "Dagelijkse controle: Gebruik 'Healthy' om snel te zien of alles goed gaat",
          "Problemen zoeken: Gebruik 'Issues' om direct probleem services te vinden",
          "Performance monitoring: Gebruik 'Performance' om trends te bekijken"
        ]
      },
      intermediate: {
        title: "SmartFilter - Geavanceerde Workflows",
        praktisch: "Advanced filtering voor operational workflows. Combineer meerdere criteria voor specifieke use cases.",
        workflows: [
          {
            naam: "Incident Response Workflow",
            stappen: [
              "Start met 'Issues' preset → Vind alle probleem services",
              "Filter op Response Time >1000ms → Vind performance bottlenecks", 
              "Filter op Success Rate <95% → Vind reliability issues",
              "Correlate met System Overview metrics voor impact assessment"
            ]
          },
          {
            naam: "Capacity Planning Workflow", 
            stappen: [
              "Start met 'Performance' preset → Bekijk alle metrics",
              "Filter op CPU Usage >70% → Vind resource constraints",
              "Filter op Requests/min trends → Vind load patterns",
              "Export data voor capacity forecasting"
            ]
          },
          {
            naam: "Health Check Workflow",
            stappen: [
              "Start met 'Healthy' preset → Baseline gezonde services",
              "Switch naar 'Issues' → Vergelijk met probleem services",
              "Check trends over tijd → Identifceer degradation patterns",
              "Set monitoring alerts voor proactive management"
            ]
          }
        ]
      }
    };

    // Detailed Analysis help
    helpContent.detailed_analysis = {
      beginner: {
        title: "Detailed Performance Analysis - Diepgaande Analyse",
        praktisch: "Hier kun je één service uitkiezen en alle details bekijken. Net als een doktersonderzoek - je bekijkt één patiënt heel grondig in plaats van een snelle check van iedereen.",
        wat_te_doen: [
          "Kies een service uit de dropdown (bijv. JobsService)",
          "Klik 'View Details' om alle metrics te zien",
          "Bekijk Performance Metrics → Response Time, Success Rate, Error Rate",
          "Check Resource Usage → CPU, Memory, Health Status",
          "Let op Performance Trend → Is het beter of slechter geworden?"
        ],
        diagnostische_tips: [
          "Hoge Error Rate + Lage Success Rate = Service heeft problemen",
          "Hoge CPU + Memory Usage = Service is overbelast",  
          "Lange Response Time = Bottleneck in verwerking",
          "Performance Trend 'degrading' = Prestaties worden slechter"
        ]
      },
      intermediate: {
        title: "Detailed Analysis - Deep Diagnostics",
        praktisch: "Granular performance analysis voor specific service troubleshooting. Correleer multiple metrics voor root cause analysis van performance degradation.",
        technisch: "Service-specific metrics aggregation met historical trend analysis en resource correlation",
        diagnostic_workflows: [
          {
            scenario: "High Response Time Investigation",
            stappen: [
              "Check Response Time trend → Identify spike patterns",
              "Correlate met CPU/Memory usage → Resource constraint analysis",
              "Check Error Rate → Determine if errors causing slowdown", 
              "Analyze Requests/min → Load correlation with performance"
            ]
          },
          {
            scenario: "Resource Utilization Analysis", 
            stappen: [
              "Monitor CPU usage patterns → Identify processing bottlenecks",
              "Track Memory usage growth → Detect memory leaks",
              "Correlate resource usage met Success Rate → Impact analysis",
              "Compare tegen baseline metrics → Performance regression detection"
            ]
          }
        ],
        metrics_interpretation: [
          "Response Time: <100ms excellent, 100-500ms good, >1000ms investigate",
          "Success Rate: >99% excellent, 95-99% acceptable, <95% critical",
          "Error Rate: <1% healthy, 1-5% monitor, >5% investigate immediately",
          "CPU Usage: <70% healthy, 70-85% monitor, >85% scale/optimize"
        ]
      }
    };

    // Return specific component help or all help
    if (componentId && helpContent[componentId]) {
      return { [componentId]: helpContent[componentId] };
    }

    return helpContent;
  }
};

export default ManagersHelpProvider;