"""iGOT Karmayogi API-Ready Integration Layer (SIH26101 Prototype).

This service provides an API-ready abstraction layer for the iGOT Karmayogi
competency-linked learning ecosystem. In production, this connector interfaces
with official iGOT / Karmayogi Bharat REST endpoints using OAuth2 mTLS tokens.

CURRENT STATUS:
[Prototype / API-Ready Integration Mode]
Demonstrates course discovery, search, enrollment hooks, and automated
skill-gap-based curriculum recommendations.
"""

from typing import List, Dict, Any, Optional
from competencies import DOMAIN_STATISTICAL, DOMAIN_TECHNICAL, DOMAIN_DIGITAL_GOV, DOMAIN_BEHAVIOURAL

# Curated catalogue aligned with iGOT Karmayogi & MoSPI capacity building
SAMPLE_IGOT_COURSES: List[Dict[str, Any]] = [
    {
        "id": "igot-stat-101",
        "title": "Sample Survey Methodologies & NSS Framework",
        "provider": "iGOT Karmayogi (MoSPI / NASA)",
        "domain": DOMAIN_STATISTICAL,
        "primary_skill": "Survey Design & Sampling",
        "duration_hours": 8,
        "rating": 4.8,
        "level": "Intermediate",
        "summary": "Covers probability sampling, multi-stage stratified designs, estimation of standard errors, and NSS survey operations.",
        "modules": ["Sampling Foundations", "Stratified Sampling", "Cluster & Multi-Stage Sampling", "Weighting & Non-Response Adjustment"],
        "badge": "Official Statistics Certified"
    },
    {
        "id": "igot-stat-102",
        "title": "National Accounts & GVA Compilation Guidelines",
        "provider": "iGOT Karmayogi (Central Statistics Office)",
        "domain": DOMAIN_STATISTICAL,
        "primary_skill": "National Accounts & GVA",
        "duration_hours": 12,
        "rating": 4.9,
        "level": "Advanced",
        "summary": "Practical training on System of National Accounts (SNA), Gross Value Added calculation, and constant price adjustments.",
        "modules": ["SNA Principles", "Institutional Sectors", "GVA Estimation", "Deflators & Constant Prices"],
        "badge": "CSO Certified"
    },
    {
        "id": "igot-stat-103",
        "title": "Index Numbers: CPI, WPI, and Inflation Measurement",
        "provider": "iGOT Karmayogi (Economic Statistics Cadre)",
        "domain": DOMAIN_STATISTICAL,
        "primary_skill": "Price Statistics & Indices",
        "duration_hours": 6,
        "rating": 4.7,
        "level": "Intermediate",
        "summary": "Mastering Laspeyres, Paasche, and Fisher index numbers, base year revision, and CPI urban/rural aggregation.",
        "modules": ["Formulae & Axiomatic Tests", "Item Basket Selection", "Imputation for Missing Prices", "Chain Indexing"],
        "badge": "MoSPI Verified"
    },
    {
        "id": "igot-stat-104",
        "title": "Statistical Quality Assurance & Metadata Standards",
        "provider": "iGOT Karmayogi (Data Quality Division)",
        "domain": DOMAIN_STATISTICAL,
        "primary_skill": "SDG Indicators & Data Quality",
        "duration_hours": 5,
        "rating": 4.6,
        "level": "Beginner",
        "summary": "Data auditing frameworks, validation rules, SDMX metadata standards, and National Indicator Framework (NIF) tracking.",
        "modules": ["Data Quality Dimensions", "SDMX Introduction", "Validation Workflows", "SDG Reporting"],
        "badge": "Quality Assurance"
    },
    {
        "id": "igot-tech-201",
        "title": "Python for Public Sector Statistical Analysis",
        "provider": "iGOT Karmayogi (Digital Capacity Building)",
        "domain": DOMAIN_TECHNICAL,
        "primary_skill": "Python for Statistical Analysis",
        "duration_hours": 10,
        "rating": 4.9,
        "level": "Beginner to Intermediate",
        "summary": "Hands-on Python, Pandas, and NumPy for processing government survey microdata, cleaning dirty datasets, and tabular reports.",
        "modules": ["Python Syntax & Setup", "Pandas for Tabular Data", "Handling Outliers & Missing Values", "Automated Excel/PDF Generation"],
        "badge": "Tech Specialist"
    },
    {
        "id": "igot-tech-202",
        "title": "SQL for Large Scale Microdata Extraction",
        "provider": "iGOT Karmayogi (National Data Warehouse)",
        "domain": DOMAIN_TECHNICAL,
        "primary_skill": "SQL & Database Systems",
        "duration_hours": 7,
        "rating": 4.8,
        "level": "Intermediate",
        "summary": "Query optimization, nested joins, window functions, and extracting unit-level data from central relational repositories.",
        "modules": ["Relational Schemas", "Complex Joins & Aggregations", "Window Functions & Ranking", "Performance Optimization"],
        "badge": "Data Engineering"
    },
    {
        "id": "igot-tech-203",
        "title": "Data Visualization & Executive Dashboards with BI Tools",
        "provider": "iGOT Karmayogi (Governance Analytics)",
        "domain": DOMAIN_TECHNICAL,
        "primary_skill": "Data Visualization & BI",
        "duration_hours": 6,
        "rating": 4.7,
        "level": "All Levels",
        "summary": "Communicating official indicators effectively through visual storytelling, map charting, and automated dashboards.",
        "modules": ["Visual Perception Rules", "Statistical Chart Selection", "Dashboard Layouts", "Accessibility in Visuals"],
        "badge": "BI Specialist"
    },
    {
        "id": "igot-tech-204",
        "title": "Applied Machine Learning for Census & Anomaly Audits",
        "provider": "iGOT Karmayogi (AI Centre of Excellence)",
        "domain": DOMAIN_TECHNICAL,
        "primary_skill": "AI/ML in Official Statistics",
        "duration_hours": 14,
        "rating": 4.8,
        "level": "Advanced",
        "summary": "Applying supervised and unsupervised machine learning algorithms to detect fraudulent entries and automate industrial classification.",
        "modules": ["Supervised Classification", "Clustering & Anomaly Detection", "NIC Code NLP Mapping", "Model Validation"],
        "badge": "AI/ML Certified"
    },
    {
        "id": "igot-gov-301",
        "title": "Cybersecurity, Microdata Privacy & DPDP Compliance",
        "provider": "iGOT Karmayogi (Cert-In & MeitY)",
        "domain": DOMAIN_DIGITAL_GOV,
        "primary_skill": "Cybersecurity & Data Privacy",
        "duration_hours": 5,
        "rating": 4.9,
        "level": "Essential",
        "summary": "Securing national microdata servers, threat awareness (phishing, spoofing, tampering), and Digital Personal Data Protection Act compliance.",
        "modules": ["Threat Landscape in Government", "Anonymization & De-identification", "DPDP Mandates", "Incident Response"],
        "badge": "Mandatory Governance"
    },
    {
        "id": "igot-gov-302",
        "title": "Digital Public Infrastructure & Open Government Data",
        "provider": "iGOT Karmayogi (Data Governance Unit)",
        "domain": DOMAIN_DIGITAL_GOV,
        "primary_skill": "Digital Public Infrastructure & Cloud",
        "duration_hours": 4,
        "rating": 4.6,
        "level": "Beginner",
        "summary": "Leveraging MeghRaj cloud, API-based interoperability, and releasing open datasets on data.gov.in securely.",
        "modules": ["DPI Framework", "Cloud Security (MeghRaj)", "API Standards", "Open Data Licenses"],
        "badge": "E-Gov Certified"
    },
    {
        "id": "igot-mgr-401",
        "title": "Official Statistical Ethics, Impartiality & UN Principles",
        "provider": "iGOT Karmayogi (National Statistical Commission)",
        "domain": DOMAIN_BEHAVIOURAL,
        "primary_skill": "Statistical Ethics & Integrity",
        "duration_hours": 3,
        "rating": 4.9,
        "level": "Essential",
        "summary": "Ethical codes for government statisticians, maintaining public trust, preventing political tampering, and strict respondent privacy.",
        "modules": ["UN Fundamental Principles", "Professional Independence", "Conflict of Interest", "Public Trust Building"],
        "badge": "Core Integrity"
    },
    {
        "id": "igot-mgr-402",
        "title": "Statistical Project Leadership & Field Team Management",
        "provider": "iGOT Karmayogi (Administrative Staff College)",
        "domain": DOMAIN_BEHAVIOURAL,
        "primary_skill": "Project Management & Communication",
        "duration_hours": 6,
        "rating": 4.7,
        "level": "Intermediate",
        "summary": "Managing large-scale field enumerator cohorts, timeline tracking, crisis escalation, and clear inter-ministerial communication.",
        "modules": ["Field Operations Scheduling", "Enumerator Quality Monitoring", "Cross-Agency Communication", "Risk Management"],
        "badge": "Leadership"
    }
]


class iGOTService:
    """API-ready service interface for iGOT Karmayogi ecosystem integration."""

    def __init__(self, api_endpoint: Optional[str] = None, api_key: Optional[str] = None):
        self.api_endpoint = api_endpoint or "https://api.igotkarmayogi.gov.in/v1 (Mock Prototype)"
        self.api_key = api_key
        self.is_live_connection = False  # Set to True when live endpoint credentials are configured

    def get_service_status(self) -> Dict[str, Any]:
        """Return connectivity and mode status."""
        return {
            "mode": "API-Ready Integration Prototype",
            "endpoint": self.api_endpoint,
            "connected": True,
            "catalogue_count": len(SAMPLE_IGOT_COURSES),
            "disclaimer": "Prototype / API-ready iGOT Integration layer for SIH26101 demonstration."
        }

    def getCourses(self, domain: Optional[str] = None, skill: Optional[str] = None) -> List[Dict[str, Any]]:
        """Retrieve course catalogue filtered optionally by domain or skill."""
        courses = SAMPLE_IGOT_COURSES
        if domain:
            courses = [c for c in courses if c["domain"].lower() == domain.lower()]
        if skill:
            courses = [c for c in courses if c["primary_skill"].lower() == skill.lower()]
        return courses

    def searchCourses(self, query: str) -> List[Dict[str, Any]]:
        """Search course titles, summaries, and modules."""
        if not query:
            return SAMPLE_IGOT_COURSES
        q = query.lower()
        results = []
        for c in SAMPLE_IGOT_COURSES:
            if (q in c["title"].lower() or
                q in c["summary"].lower() or
                q in c["primary_skill"].lower() or
                any(q in m.lower() for m in c["modules"])):
                results.append(c)
        return results

    def getCourseDetails(self, course_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve full metadata for a specific iGOT course."""
        for c in SAMPLE_IGOT_COURSES:
            if c["id"] == course_id:
                return c
        return None

    def recommendCourses(self, skill_gaps: List[Dict[str, Any]], limit: int = 5) -> List[Dict[str, Any]]:
        """Generate personalized course recommendations based on identified skill gaps."""
        recommendations = []
        seen_course_ids = set()
        for gap in skill_gaps:
            skill = gap.get("skill", "")
            current_score = gap.get("current_score", 0)
            target_score = gap.get("target_score", 70)
            gap_pct = gap.get("gap", 0)
            priority = gap.get("priority", "Medium")

            # Find matching course in catalogue
            matched_courses = [c for c in SAMPLE_IGOT_COURSES if c["primary_skill"].lower() == skill.lower()]
            if not matched_courses:
                # Fallback to domain match
                domain = gap.get("domain", "")
                matched_courses = [c for c in SAMPLE_IGOT_COURSES if c["domain"].lower() == domain.lower()]

            for course in matched_courses:
                if course["id"] in seen_course_ids:
                    continue
                seen_course_ids.add(course["id"])
                recommendations.append({
                    "course_id": course["id"],
                    "course_title": course["title"],
                    "provider": course["provider"],
                    "domain": course["domain"],
                    "skill": skill,
                    "duration_hours": course["duration_hours"],
                    "level": course["level"],
                    "summary": course["summary"],
                    "priority": priority,
                    "reason": f"Current competency in '{skill}' is {current_score}%, which is {gap_pct}% below your target benchmark of {target_score}%.",
                    "badge": course.get("badge", "iGOT Certified")
                })
                if len(recommendations) >= limit:
                    return recommendations

        return recommendations[:limit]


# Global service instance
igot_service = iGOTService()
