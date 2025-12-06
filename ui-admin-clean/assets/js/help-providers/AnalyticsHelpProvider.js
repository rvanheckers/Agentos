/**
 * AnalyticsHelpProvider - Help Content voor Analytics View
 * 
 * Comprehensive help content met actionable intelligence focus voor Analytics dashboard.
 * Transforms passive metrics into operational intelligence met context, thresholds en actions.
 * 
 * Content Structure:
 * - Performance Metrics met optimization actions
 * - Error Analysis met response workflows  
 * - Capacity Planning met scaling recommendations
 * - Business Intelligence met actionable insights
 * - Threshold-based contextual help
 * 
 * Created: 11 Augustus 2025
 * Based on: ANALYTICS_REDESIGN_ASSESSMENT.md + JobsQueueHelpProvider pattern
 */

export const AnalyticsHelpProvider = {
  /**
   * Get help content voor specific component
   * @param {string} componentId - Component identifier or null voor all help
   * @returns {object} Help content object
   */
  getHelp(componentId = null) {
    // Get dynamic data from current view (safe for SSR/tests)
    const hasWindow = typeof window !== 'undefined';
    const analytics = hasWindow && window.analytics ? window.analytics : null;
    const currentTimeframe = analytics?.currentTimeframe ?? '24h';
    const currentTab = analytics?.currentTab ?? 'performance';
    
    const helpContent = {
      // Analytics Overview - main section help
      'analytics_overview': {
        beginner: {
          title: "Analytics - Business Intelligence Dashboard",
          praktisch: `Je complete business analytics centrum waar je niet alleen data kunt bekijken, maar ook direct kan handelen. Huidige focus: ${currentTab} metrics over ${currentTimeframe} periode.`,
          wat_te_doen: [
            "📊 Performance = Snelheid en efficiency van je systeem",
            "🔍 Usage = Wie gebruikt wat wanneer voor business insights", 
            "❌ Errors = Probleem detectie met directe actie opties",
            "📈 Capacity = Resource planning met scaling aanbevelingen",
            "🎯 Elke metric heeft actie knoppen voor direct ingrijpen"
          ]
        },
        intermediate: {
          title: "Analytics - Operational Intelligence Center",
          praktisch: `Advanced analytics met actionable insights voor operational excellence. Real-time metrics met threshold-based actions en smart recommendations voor proactive system management.`,
          technisch: "Analytics data aggregated from multiple sources met WebSocket real-time updates",
          metrics: [
            "Response times: <1s excellent, >3s requires action",
            "Error rates: <1% healthy, >5% critical threshold",
            "Resource utilization: 60-80% optimal range",
            "Business KPIs: SLA compliance, user satisfaction, cost efficiency"
          ]
        }
      },

      // Performance Metrics Tab
      'performance_metrics': {
        beginner: {
          title: "Performance Dashboard - Systeem Snelheid",
          praktisch: "Toont hoe snel je systeem reageert en presteert. Net als een snelheidsmeter voor je auto - je ziet direct of alles goed loopt.",
          wat_te_doen: [
            "⚡ Response Time = Hoe snel systeem antwoordt op verzoeken",
            "📊 Throughput = Hoeveel werk per tijdseenheid wordt gedaan",
            "🎯 SLA Compliance = Of je beloofde service levels worden gehaald",
            "🔧 Performance actions = Direct optimalisatie knoppen"
          ]
        },
        intermediate: {
          title: "Performance Analytics - System Optimization Center",
          praktisch: "Real-time performance monitoring met actionable optimization recommendations en automated scaling triggers.",
          technisch: "Performance metrics from application monitoring, database queries, en system resources",
          metrics: [
            "Response time trends: P50, P95, P99 percentiles tracking",
            "Throughput patterns: Requests/second with peak load analysis", 
            "Resource correlation: CPU/Memory vs response time relationships",
            "SLA dashboard: Uptime percentage and breach notifications"
          ]
        }
      },

      // Response Time Analysis
      'response_time_analysis': {
        beginner: {
          title: "Response Time - Hoe Snel Reageert Het Systeem",
          praktisch: "Meet hoe lang het duurt voordat je systeem antwoord geeft. Als je op een knop drukt, hoe snel krijg je reactie?",
          wat_te_doen: [
            "🟢 <1s = Excellent, gebruikers zijn tevreden",
            "🟡 1-3s = Acceptabel, maar kan beter", 
            "🔴 >3s = Traag, gebruikers worden ongeduldig",
            "⚡ Optimization knoppen voor directe verbetering"
          ],
          actions: [
            "Bij trage tijden: klik 'Optimize Performance'",
            "Bij structurele problemen: 'Scale Resources'", 
            "Voor analyse: genereer 'Performance Report'"
          ]
        },
        intermediate: {
          title: "Response Time Optimization - Performance Management",
          praktisch: "Advanced response time analysis met automated optimization triggers en performance tuning recommendations.",
          technisch: "Response time percentiles (P50/P95/P99) met correlation analysis voor bottleneck identification",
          metrics: [
            "Baseline performance: Historical response time patterns",
            "Peak load impact: Response time degradation under load",
            "Optimization opportunities: Caching, indexing, resource scaling",
            "SLA tracking: Response time vs configured service levels"
          ]
        }
      },

      // SLA Compliance Dashboard
      'sla_compliance': {
        beginner: {
          title: "SLA Compliance - Service Level Betrouwbaarheid",
          praktisch: "Percentage van de tijd dat je systeem werkt zoals beloofd aan gebruikers. >99% is uitstekend.",
          wat_te_doen: [
            "🟢 >99% = Perfect, systeem zeer betrouwbaar",
            "🟡 95-99% = Goed, enkele issues - monitor trends",
            "🔴 <95% = Probleem, onderzoek en actie nodig",
            "📈 Klik actions voor diepere analyse"
          ],
          actions: [
            "Bij score <99%: bekijk failed operations details",
            "Genereer SLA rapport voor management review",
            "Set alerts voor automatische waarschuwingen"
          ]
        },
        intermediate: {
          title: "SLA Management - Service Level Agreement Monitoring", 
          praktisch: "Real-time SLA performance tegen gedefinieerde service levels voor operational excellence.",
          technisch: "Uptime calculated als (Total Time - Downtime) / Total Time × 100%",
          metrics: [
            "Target SLA: 99.5% uptime (4.38h downtime/month max)",
            "Measurement window: Rolling 30-day calculation", 
            "Factors: System availability, response times, error rates",
            "Business impact: SLA breach cost analysis"
          ]
        }
      },

      // Error Analytics Tab  
      'error_analytics': {
        beginner: {
          title: "Error Analytics - Probleem Detective Dashboard",
          praktisch: "Toont alle fouten en problemen in je systeem met directe oplossings opties. Net als een probleem detective die niet alleen problemen vindt maar ook oplossingen voorstelt.",
          wat_te_doen: [
            "🔍 Error Rate = Percentage verzoeken dat misgaat",
            "📊 Error Types = Welke soorten problemen komen voor",
            "🚨 Critical Errors = Ernstige problemen die direct aandacht nodig hebben",
            "🔧 Error Actions = Directe oplossing knoppen"
          ]
        },
        intermediate: {
          title: "Error Management Center - Proactive Issue Resolution",
          praktisch: "Advanced error analysis met pattern recognition en automated response workflows voor proactive issue management.",
          technisch: "Error aggregation with pattern analysis, automated alerting en resolution workflows",
          metrics: [
            "Error rate trends: Pattern analysis over time periods",
            "Error categorization: 4xx client errors vs 5xx server errors",
            "Resolution workflows: Automated retry, escalation patterns", 
            "Impact analysis: Error correlation met business metrics"
          ]
        }
      },

      // Error Rate Monitoring
      'error_rate_monitoring': {
        beginner: {
          title: "Error Rate - Foutpercentage Monitoring", 
          praktisch: "Percentage van alle verzoeken dat fout gaat. Als 1% van je klanten problemen heeft, is dat acceptabel. Bij 10% heb je een crisis.",
          wat_te_doen: [
            "🟢 <1% = Uitstekend, systeem loopt zeer stabiel",
            "🟡 1-5% = Acceptabel, maar monitor voor trends",
            "🔴 >5% = Probleem, direct onderzoek en actie nodig",
            "🚨 Spike detection = Plotselinge stijgingen worden gedetecteerd"
          ],
          actions: [
            "Bij hoge error rate: 'Investigate Top Errors'",
            "Voor bulk herstel: 'Retry Failed Operations'",
            "Emergency response: 'Generate Error Report'"
          ]
        },
        intermediate: {
          title: "Error Rate Analysis - Quality Assurance Monitoring",
          praktisch: "Statistical error rate analysis met automated alerting en pattern recognition voor quality assurance.",
          technisch: "Error rate calculated als Failed Requests / Total Requests × 100% met sliding window",
          metrics: [
            "Error rate thresholds: <1% green, 1-5% yellow, >5% red",
            "Pattern analysis: Error spikes, periodic failures, trending issues",
            "Root cause correlation: Error types vs system components",
            "Recovery metrics: Mean time to resolution, auto-recovery rates"
          ]
        }
      },

      // Capacity Planning Tab
      'capacity_planning': {
        beginner: {
          title: "Capacity Planning - Resource Management Dashboard",
          praktisch: "Toont of je genoeg 'kracht' hebt om alle werk te doen. Net als controleren of je genoeg werknemers hebt voor de drukte.",
          wat_te_doen: [
            "👷 Worker Utilization = Hoeveel van je workers zijn bezig",
            "💾 Resource Usage = CPU, geheugen, opslag gebruik", 
            "📈 Scaling Recommendations = Wanneer meer resources nodig",
            "⚖️ Load Balancing = Werk eerlijk verdelen over workers"
          ]
        },
        intermediate: {
          title: "Capacity Management - Resource Optimization Center",
          praktisch: "Advanced capacity planning met predictive scaling en resource optimization voor cost-effective operations.",
          technisch: "Resource utilization monitoring met automated scaling triggers en cost optimization",
          metrics: [
            "Utilization patterns: CPU, memory, disk, network usage trends",
            "Scaling triggers: Automatic horizontal/vertical scaling thresholds",
            "Cost optimization: Resource efficiency vs operational costs",
            "Predictive analytics: Future capacity needs based on growth trends"
          ]
        }
      },

      // Worker Utilization Management
      'worker_utilization': {
        beginner: {
          title: "Worker Utilization - Team Bezettingsgraad",
          praktisch: "Percentage van je workers die actief bezig zijn met werk. 70% is ideaal - niet te druk, niet te rustig.",
          wat_te_doen: [
            "😴 <30% = Onderbenut, workers staan stil - meer work",
            "✅ 30-80% = Perfect, gezonde werklast verdeling", 
            "🔥 >80% = Overbelast, overweeg meer workers",
            "⚖️ Auto-scaling beschikbaar voor optimale balans"
          ],
          actions: [
            "Bij onderbenutting: 'Redistribute Work'",
            "Bij overbelasting: 'Scale Up Workers'",
            "Voor optimalisatie: 'Optimize Worker Pool'"
          ]
        },
        intermediate: {
          title: "Worker Resource Optimization - Efficient Scaling",
          praktisch: "Advanced worker utilization analysis met intelligent scaling en workload distribution optimization.", 
          technisch: "Worker utilization metrics: Active workers / Total workers × 100% met workload analysis",
          metrics: [
            "Optimal utilization: 60-80% range voor efficiency vs responsiveness",
            "Scaling algorithms: Predictive scaling based on queue depth en historical patterns", 
            "Resource efficiency: Work distribution algorithms voor load balancing",
            "Cost optimization: Right-sizing worker pools voor operational costs"
          ]
        }
      },

      // Business Intelligence Tab
      'business_intelligence': {
        beginner: {
          title: "Business Intelligence - Slimme Business Inzichten",
          praktisch: "Toont niet alleen wat er gebeurt, maar helpt je begrijpen waarom en wat je eraan kunt doen voor betere business resultaten.",
          wat_te_doen: [
            "💰 Cost Analysis = Hoeveel kost je systeem om te runnen",
            "👥 User Behavior = Hoe gebruikers je systeem gebruiken",
            "📊 Business KPIs = Belangrijkste business prestatie indicatoren", 
            "🎯 Smart Recommendations = AI-gestuurde business adviezen"
          ]
        },
        intermediate: {
          title: "Business Intelligence Center - Data-Driven Decision Making",
          praktisch: "Advanced business analytics met machine learning insights en automated recommendation engine voor strategic planning.",
          technisch: "Business metrics aggregation met predictive analytics en automated insight generation",
          metrics: [
            "Revenue optimization: Cost per transaction, profit margins analysis",
            "User engagement: Usage patterns, feature adoption, satisfaction scores",
            "Operational efficiency: Process optimization, resource ROI analysis", 
            "Predictive insights: Trend analysis, forecasting, risk assessment"
          ]
        }
      },

      // Smart Recommendations Engine
      'smart_recommendations': {
        beginner: {
          title: "Smart Recommendations - AI Assistent voor Betere Prestaties",
          praktisch: "Je persoonlijke AI assistent die naar je systeem kijkt en slimme verbeter tips geeft. Net als een ervaren collega die altijd goede adviezen heeft.",
          wat_te_doen: [
            "💡 Performance Tips = Automatische voorstellen voor betere snelheid",
            "🔧 Optimization Actions = One-click verbeteringen",
            "⚠️ Issue Alerts = Waarschuwingen voordat problemen groot worden",
            "📈 Growth Recommendations = Tips voor systeem uitbreiding"
          ],
          actions: [
            "Implementeer 'High Priority' recommendations eerst",
            "Review 'Medium Priority' tips wekelijks", 
            "Monitor 'Low Priority' suggestions voor lange termijn planning"
          ]
        },
        intermediate: {
          title: "ML-Powered Recommendation Engine - Intelligent Optimization",
          praktisch: "Machine learning recommendations engine met pattern recognition en predictive optimization voor intelligent system management.",
          technisch: "ML algorithms analyze system metrics voor automated recommendation generation",
          metrics: [
            "Recommendation accuracy: Success rate van implemented suggestions",
            "Impact measurement: Performance improvement na recommendation implementation",
            "Pattern recognition: Historical data analysis voor predictive recommendations",
            "Business value: ROI calculation voor recommended optimizations"
          ]
        }
      },

      // Automation & Actions
      'automation_center': {
        beginner: {
          title: "Automation Center - Automatische Acties voor Efficiency",
          praktisch: "Laat je systeem zichzelf optimaliseren met slimme automatisering. Net als een zelf-rijdende auto die automatisch de beste route kiest.",
          wat_te_doen: [
            "🤖 Auto-Scaling = Automatisch meer/minder workers bij drukte",
            "🧹 Auto-Cleanup = Automatisch opruimen van oude data",
            "📊 Auto-Reports = Automatische rapporten naar management",
            "⚠️ Auto-Alerts = Automatische waarschuwingen bij problemen"
          ],
          actions: [
            "Configure automation rules voor your use case",
            "Set thresholds voor automated responses",
            "Monitor automation effectiveness regularly"
          ]
        },
        intermediate: {
          title: "Advanced Automation - Intelligent System Orchestration",
          praktisch: "Enterprise-level automation met complex rule engines en intelligent decision making voor autonomous operations.",
          technisch: "Rule-based automation engine met machine learning optimization en feedback loops",
          metrics: [
            "Automation coverage: Percentage van manual tasks automated",
            "Decision accuracy: Automated action success rates",
            "Operational efficiency: Time saved through automation",
            "Risk management: Automated response effectiveness voor incident prevention"
          ]
        }
      },

      // Threshold Management
      'threshold_management': {
        beginner: {
          title: "Threshold Management - Waarschuwings Grenzen Instellen",
          praktisch: "Stel grenzen in waarbij je systeem automatisch waarschuwt of actie onderneemt. Net als een brandalarm dat afgaat bij te veel rook.",
          wat_te_doen: [
            "🟡 Warning Thresholds = Vroege waarschuwing grenzen",
            "🔴 Critical Thresholds = Emergency actie grenzen", 
            "⚡ Automated Actions = Wat moet er automatisch gebeuren",
            "📊 Threshold History = Hoe vaak grenzen worden overschreden"
          ]
        },
        intermediate: {
          title: "Dynamic Threshold Management - Adaptive Alerting",
          praktisch: "Machine learning-based dynamic thresholds die zich aanpassen aan changing conditions voor accurate alerting.",
          technisch: "Adaptive threshold algorithms met baseline learning en anomaly detection",
          metrics: [
            "Threshold accuracy: False positive vs true positive rates",
            "Adaptive learning: Threshold adjustment based on historical patterns",
            "Alert fatigue prevention: Intelligent alert aggregation",
            "Response optimization: Threshold tuning voor optimal system responses"
          ]
        }
      }
    };

    // Add troubleshooting scenarios for analytics
    if (componentId === 'analytics_troubleshooting' || componentId === null) {
      helpContent['analytics_troubleshooting'] = {
        beginner: {
          title: "Analytics Problemen Oplossen - Veel Voorkomende Situaties",
          scenarios: [
            {
              symptoom: "Analytics data wordt niet geupdate", 
              oorzaken: [
                "WebSocket verbinding verbroken",
                "Cache warming problemen",
                "Database connectie issues"
              ],
              oplossingen: [
                "Refresh de pagina voor nieuwe WebSocket verbinding",
                "Check CentralDataService status in browser console",
                "Wacht 5 minuten voor automatische cache refresh",
                "Contact support bij aanhoudende problemen"
              ]
            },
            {
              symptoom: "Metrics tonen onjuiste waarden",
              oorzaken: [
                "Cache synchronisatie vertraging",
                "Time zone verschillen", 
                "Filter instellingen niet correct"
              ],
              oplossingen: [
                "Controleer geselecteerde tijdsperiode (24h, 7d, 30d)",
                "Reset filters met 'Clear All' knop",
                "Vergelijk met Dashboard metrics voor validatie",
                "Check browser tijd instellingen"
              ]
            },
            {
              symptoom: "Action buttons werken niet",
              oorzaken: [
                "Onvoldoende permissies",
                "ActionService niet verbonden",
                "Rate limiting actief"
              ],
              oplossingen: [
                "Check admin permissies met system administrator",
                "Refresh pagina voor ActionService reconnect",
                "Wacht enkele minuten bij rate limiting",
                "Controleer browser console voor error messages"
              ]
            }
          ]
        },
        intermediate: {
          title: "Advanced Analytics Troubleshooting - System Diagnostics",
          scenarios: [
            {
              symptoom: "Performance metrics show anomalous patterns",
              oorzaken: [
                "System load spikes affecting measurement accuracy",
                "Database query performance degradation",
                "Network latency affecting data collection",
                "Time series data gaps or corruption"
              ],
              oplossingen: [
                "Cross-reference metrics met system monitoring tools",
                "Analyze database query performance logs",
                "Check network connectivity to monitoring endpoints",
                "Validate time series data integrity en implement gap filling",
                "Consider sampling rate adjustments voor high-load periods"
              ]
            },
            {
              symptoom: "Automated actions not triggering correctly",
              oorzaken: [
                "Threshold configuration issues",
                "Circuit breaker in OPEN state",
                "Automation rule conflicts",
                "Insufficient system resources voor action execution"
              ],
              oplossingen: [
                "Review automation rule configuration en conflict resolution",
                "Check circuit breaker status en manual reset if needed", 
                "Monitor action execution logs voor failure patterns",
                "Implement action queue monitoring en resource allocation",
                "Test automation rules in staging environment first"
              ]
            }
          ]
        }
      };
    }

    if (componentId === null) {
      return helpContent;
    }
    if (!Object.prototype.hasOwnProperty.call(helpContent, componentId)) {
      return {};
    }
    return { [componentId]: helpContent[componentId] };
  }
};