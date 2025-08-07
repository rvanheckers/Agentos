/**
 * AgentsWorkersHelpProvider - Help Content voor Agents & Workers View
 * 
 * Complete help content met fabriek metaforen voor AI agents en worker management.
 * Focus: Workers = fabrieks werknemers, Agents = gespecialiseerde tools/machines
 * 
 * Content Structure:
 * - Fabriek metafoor consistent met andere views
 * - Workers als werknemers die jobs afwerken
 * - Agents als gespecialiseerde AI tools (video use case voorbeeld)
 * - Beginner: kort en duidelijk, Intermediate: meer technische details
 * 
 * Created: 4 Augustus 2025
 * Based on: AgentsWorkers.js view + consistent help system architecture
 */

export const AgentsWorkersHelpProvider = {
  /**
   * Get help content voor specific component
   * @param {string} componentId - Component identifier or null voor all help
   * @returns {object} Help content object
   */
  getHelp(componentId = null) {
    // Get dynamic data from current view
    const totalWorkers = window.agentsWorkersView ? window.agentsWorkersView.workers?.length || 0 : 0;
    const totalAgents = window.agentsWorkersView ? window.agentsWorkersView.agents?.length || 0 : 0;
    
    const helpContent = {
      // Main view overview
      'agents_workers_overview': {
        beginner: {
          title: "Agents & Workers - Fabriek Personeel Overzicht",
          praktisch: `Dit is je personeels overzicht waar je alle ${totalAgents} AI agents en ${totalWorkers} Celery workers beheert. Het is zoals de HR afdeling van je fabriek - hier zie je wie er werkt en wat ze doen.`,
          wat_te_doen: [
            "👷 Celery Workers = Flexibele werknemers voor alle soorten taken",
            "🤖 AI Agents = Gespecialiseerde machines voor video/audio processing",
            "📊 System Overview = Totaal overzicht van je personeel capaciteit",
            "⚡ Active count = Hoeveel er nu daadwerkelijk bezig zijn",
            "🎯 Gebruik tabs om details per type personeel te bekijken"
          ]
        },
        intermediate: {
          title: "Agents & Workers - Hybrid Processing Architecture",
          praktisch: `Unified management voor ${totalAgents} AI agents + ${totalWorkers} Celery workers. Hybrid processing model combineert specialized AI processing met general-purpose distributed computing.`,
          technisch: "Architecture: Specialized AI agents (domain-specific) + Celery worker pool (general-purpose distributed tasks)",
          metrics: [
            "🤖 AI Specialization: Domain-optimized agents voor video/audio/ML workflows",
            "👷 Celery Scaling: Horizontaal schaalbare worker pool voor general tasks",
            "⚡ Resource Efficiency: Combined utilization tracking en capacity planning",
            "🔄 Pipeline Coordination: Seamless task handoff tussen agents en workers"
          ]
        }
      },

      // System Overview - main metrics section
      'system_overview': {
        beginner: {
          title: "System Overview - Fabriek Capaciteit Dashboard",
          praktisch: `Dit dashboard toont je complete personeel overzicht: ${totalAgents} AI agents + ${totalWorkers} Celery workers. Het is je fabriek capaciteit in één oogopslag.`,
          wat_te_doen: [
            "🤖 AI Agents count = Gespecialiseerde machines beschikbaar",
            "👷 Celery Workers count = Flexibele werknemers beschikbaar", 
            "✅ Active total = Hoeveel er nu daadwerkelijk werken",
            "🔄 Success Rate = Hoe goed je fabriek presteert (%)",
            "📊 Gebruik deze cijfers om te zien of je genoeg personeel hebt"
          ]
        },
        intermediate: {
          title: "System Overview - Resource Capacity Analytics",
          praktisch: "Unified dashboard voor complete resource landscape monitoring. Toont real-time capacity utilization across hybrid AI + Celery processing architecture.",
          technisch: "Combined metrics: AI agent fleet status + Celery worker pool utilization + aggregate performance KPIs",
          metrics: [
            "🤖 Agent Capacity: Domain-specific processing unit availability en workload",
            "👷 Worker Pool: Distributed computing capacity en horizontal scaling status",
            "✅ Active Utilization: Resource efficiency ratio (active/total resources)",
            "🔄 Quality Metrics: Aggregate success rate trends voor system health"
          ]
        }
      },

      // Workers Management - workforce section
      'workers_management': {
        beginner: {
          title: "Workers Management - Fabriek Werknemers",
          praktisch: "Dit zijn je fabriek werknemers die jobs oppakken en afwerken. Elke worker kan verschillende taken doen.",
          wat_te_doen: [
            "👥 Workers = Werknemers die jobs van de lopende band pakken",
            "🟢 Active = Werknemers die nu bezig zijn met een job",
            "🟡 Idle = Werknemers die beschikbaar zijn maar wachten op werk",
            "🔴 Offline = Werknemers die niet beschikbaar zijn",
            "Meer workers = snellere verwerking van jobs in de wachtrij"
          ]
        },
        intermediate: {
          title: "Workers Management - Celery Workforce Administration",
          praktisch: "Distributed task processing workforce management voor scalable job execution.",
          technisch: "Celery worker pool management met auto-scaling en health monitoring",
          metrics: [
            "👥 Worker Instances: Individual worker process monitoring",
            "🟢 Active Jobs: Current task assignments per worker",
            "🟡 Idle Capacity: Available worker capacity voor load balancing",
            "🔴 Failed Workers: Error detection en automatic restart procedures",
            "📈 Performance Metrics: Task completion rates per worker instance"
          ]
        }
      },

      // AI Agents Management - specialized tools section
      'agents_management': {
        beginner: {
          title: "AI Agents - Gespecialiseerde Machines",
          praktisch: "Dit zijn gespecialiseerde AI machines in je fabriek, elk met eigen specialiteit (zoals video bewerking).",
          wat_te_doen: [
            "🤖 AI Agents = Slimme machines die specifieke taken doen",
            "🎬 Video Agents = Machines voor video naar clips (bijvoorbeeld)",
            "📝 Text Agents = Machines voor tekst verwerking", 
            "🔊 Audio Agents = Machines voor geluid bewerking",
            "🟢 Available = Machine is klaar voor werk",
            "🔴 Busy = Machine is bezig met een taak"
          ]
        },
        intermediate: {
          title: "AI Agents - Specialized Processing Units",
          praktisch: "AI service fleet management voor domain-specific processing capabilities.",
          technisch: "Microservice architecture met specialized AI agents voor verschillende job types",
          metrics: [
            "🤖 Agent Types: Different AI capabilities (video, audio, text processing)",
            "🎬 Video Pipeline: Download → Transcribe → Analyze → Crop → Cut workflow",
            "📝 Processing Chains: Multi-stage AI workflows per job type",
            "🔊 Resource Allocation: GPU/CPU assignment voor AI processing",
            "🟢 Service Health: Individual agent availability en error rates"
          ]
        }
      },

      // Pipeline Status - workflow monitoring
      'pipeline_status': {
        beginner: {
          title: "Pipeline Status - Productielijn Overzicht", 
          praktisch: "Dit toont hoe goed de hele productielijn werkt - van job binnenkomst tot eindproduct.",
          wat_te_doen: [
            "⚡ Pipeline = Productielijn die jobs stap voor stap afwerkt",
            "📥 Input Rate = Hoeveel nieuwe jobs er binnenkomen",
            "📤 Output Rate = Hoeveel jobs er klaar komen",
            "🔄 Processing Time = Hoe lang een job duurt van start tot eind",
            "Bij rode cijfers: kijk naar workers en agents voor knelpunten"
          ]
        },
        intermediate: {
          title: "Pipeline Status - Workflow Performance Analytics",
          praktisch: "End-to-end pipeline monitoring voor bottleneck detection en optimization.",
          technisch: "Multi-stage workflow analytics met performance bottleneck identification",
          metrics: [
            "⚡ Throughput Analysis: Jobs/hour capacity vs actual processing rate",
            "📥 Queue Depth: Input rate vs processing capacity analysis", 
            "📤 Completion Rate: Success rate en failure pattern analysis",
            "🔄 Stage Timing: Per-stage performance voor bottleneck identification",
            "🎯 SLA Monitoring: Processing time targets vs actual performance"
          ]
        }
      }
    };

    // Add Smart Filter help section
    if (componentId === 'smart_filter' || componentId === null) {
      helpContent['smart_filter'] = {
        beginner: {
          title: "Smart Filters - Personeel Sortering",
          praktisch: "Filters helpen je snel het juiste personeel te vinden. Zoals verschillende vakjes voor verschillende soorten werknemers in je fabriek.",
          wat_te_doen: [
            "📊 System Overview = Alles samen zien (standaard weergave)",
            "🤖 AI Agents = Alleen gespecialiseerde machines tonen",
            "👷 Celery Workers = Alleen flexibele werknemers tonen", 
            "🔄 Pipelines = Productielijn status en prestaties",
            "Klik op filter om snel tussen overzichten te wisselen"
          ]
        },
        intermediate: {
          title: "Smart Filters - Resource View Management",
          praktisch: "Tab-based view switching voor focused resource management. Elke filter toont specifieke resource categorieën met relevante metrics.",
          technisch: "Client-side view filtering met dynamic content rendering per resource type",
          metrics: [
            "📊 Overview: Combined metrics voor complete resource landscape",
            "🤖 Agents: Domain-specific AI processing units met specialization metrics",
            "👷 Workers: Celery distributed computing pool met scalability metrics",
            "🔄 Pipelines: End-to-end workflow performance en bottleneck analysis"
          ]
        }
      };
    }

    // Add Quick Stats help sections
    helpContent['total_agents'] = {
      beginner: {
        title: "AI Agents - Slimme Fabriek Machines",
        praktisch: `Je hebt ${totalAgents} slimme machines in je fabriek. Elke machine is gespecialiseerd in één type werk - bijvoorbeeld video bewerking. Ze zijn sneller dan gewone werknemers, maar kunnen alleen hun eigen specialiteit.`,
        wat_te_doen: [
          "🤖 Elke agent = Een gespecialiseerde machine",
          "📹 Video agents downloaden, knippen en monteren video's", 
          "🎵 Audio agents maken transcripties van gesproken tekst",
          "⚡ Veel sneller dan workers voor hun eigen werk",
          "📊 Klik op 'Agents' tab voor details per machine"
        ]
      },
      intermediate: {
        title: "AI Agent Fleet - Domain-Specific Processing Units",
        praktisch: `${totalAgents} gespecialiseerde AI processing units actief. Elke agent is geoptimaliseerd voor specifieke task domains met hogere throughput dan general-purpose workers.`,
        technisch: "Domain-specific processing units: video-downloader, audio-transcriber, moment-detector, video-cutter",
        metrics: [
          "🎯 Specialization Advantage: 3-5x sneller dan workers voor domain tasks",
          "⚡ Pipeline Efficiency: End-to-end video processing in ~45 seconden",
          "🔄 Workflow Chaining: Sequential agent execution zonder data overhead",
          "📊 Success Tracking: Per-agent KPIs + aggregate pipeline metrics",
          "🚀 Horizontal Scaling: Agent instances op basis van workload patterns"
        ]
      }
    };

    helpContent['total_workers'] = {
      beginner: {
        title: "Workers - Fabriek Werknemers",
        praktisch: `Je hebt ${totalWorkers} gewone werknemers in je fabriek. Ze kunnen alle soorten work oppakken - niet gespecialiseerd zoals agents, maar wel flexibel. Als er veel werk is, kunnen er automatisch meer workers bijkomen.`,
        wat_te_doen: [
          "👷 Elke worker = Een flexibele werknemer",
          "📦 Pakken elke job uit de wachtrij en werken het af",
          "🔄 Automatisch meer workers als er drukte is",
          "⏱️ Langzamer dan agents, maar kunnen alles",
          "📊 Klik op 'Workers' tab om te zien wie wat doet"
        ]
      },
      intermediate: {
        title: "Celery Worker Pool - Distributed Computing Layer",
        praktisch: `${totalWorkers} Celery workers vormen de horizontaal schaalbare computing laag. General-purpose processing power voor non-specialized tasks en overflow capacity.`,
        technisch: "Python Celery workers met Redis broker - horizontaal schaalbaar processing pool",
        metrics: [
          "⚖️ Load Distribution: Automatische job verdeling over beschikbare workers",
          "📈 Auto-Scaling: Worker pool size aanpassen op basis van queue depth",
          "🔄 Fault Tolerance: Retry mechanisms + graceful failure handling",
          "📊 Throughput KPI: ~15-25 jobs/minute per worker (task afhankelijk)",
          "🎯 Resource Efficiency: CPU/memory optimalisatie per worker process"
        ]
      }
    };

    helpContent['active_count'] = {
      beginner: {
        title: "Active - Werkend Personeel Totaal",  
        praktisch: "Dit toont hoeveel werknemers en machines er nu daadwerkelijk bezig zijn met werk (niet in pauze of offline). Het is het totaal van alle actieve workers en agents samen.",
        wat_te_doen: [
          "✅ Active = Alle bezig zijnde workers + agents",
          "💼 Hoe hoger dit getal, hoe meer er tegelijk gemaakt wordt",
          "📊 Ideaal tijdens drukke momenten: bijna alle personeel actief",
          "⚠️ Te laag getal = misschien te weinig personeel of geen werk",
          "🎯 Monitor dit om te zien of je fabriek op volle toeren draait"
        ]
      },
      intermediate: {
        title: "Active Resource Utilization - Current Processing Load",
        praktisch: "Real-time indicator van processing capacity utilization. Toont gecombineerde active workers + active agents die momenteel jobs executeren.",
        technisch: "Real-time count: Σ(active Celery workers) + Σ(active AI agents in processing state)",
        metrics: [
          "⚡ Capacity Utilization: Active/Total resources ratio voor efficiency tracking",
          "📊 Resource Efficiency: Idle vs active resource distribution analysis",
          "🎯 Scaling Trigger: Low active count = potential over-provisioning",
          "⚖️ Load Balance: Even distribution across available processing units",
          "📈 Performance KPI: Higher utilization = better resource economics"
        ]
      }
    };

    helpContent['success_rate'] = {
      beginner: {
        title: "Success Rate - Fabriek Prestatie Percentage",
        praktisch: "Dit toont hoeveel % van alle jobs goed zijn afgerond zonder fouten. Het is zoals het 'prestatie rapport' van je hele fabriek - hoe hoger, hoe beter je fabriek draait!",
        wat_te_doen: [
          "📊 90%+ = Goede fabriek prestatie",
          "🎯 95%+ = Zeer goede kwaliteitscontrole", 
          "🏆 98%+ = Excellente productie kwaliteit",
          "⚠️ <90% = Er gaan te veel dingen mis, check systeem",
          "🔧 Bij daling: kijk naar error logs en worker status"
        ]
      },
      intermediate: {
        title: "Success Rate - Aggregate Quality Metric",
        praktisch: "Gewogen gemiddelde van alle agent success rates + worker task completion ratios. Real-time kwaliteits indicator voor het hele processing systeem.",
        technisch: "Berekening: (Σ agent success rates + Σ worker completion ratios) ÷ totaal actieve resources",
        metrics: [
          "📊 Quality KPI: <95% indicates systemic processing issues",
          "🎯 SLA Target: >98% voor production service levels",
          "🔍 Trend Analysis: Dalende trend = vroege waarschuwing voor problemen",
          "⚖️ Resource Quality: Individual vs aggregate performance comparison",
          "📈 Historical Tracking: Success rate patterns voor capacity planning"
        ]
      }
    };

    return componentId ? { [componentId]: helpContent[componentId] } : helpContent;
  }
};