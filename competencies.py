"""Competency Framework & Taxonomy for India's Official Statistical System (SIH26101).

Defines core competency domains, skills, benchmark target scores, and
mapping rules for MoSPI / National Statistical System capacity building.
"""

from typing import Dict, List, Any

# Major Competency Domains aligned with SIH26101
DOMAIN_STATISTICAL = "Statistical Competencies"
DOMAIN_TECHNICAL = "Technical Competencies"
DOMAIN_DIGITAL_GOV = "Digital Governance"
DOMAIN_BEHAVIOURAL = "Behavioural & Managerial"

COMPETENCY_DOMAINS = [
    DOMAIN_STATISTICAL,
    DOMAIN_TECHNICAL,
    DOMAIN_DIGITAL_GOV,
    DOMAIN_BEHAVIOURAL,
]

# Configurable Competency Catalogue with standard benchmarks and descriptions
COMPETENCY_CATALOGUE: Dict[str, Dict[str, Any]] = {
    # ------------------ A. Statistical Competencies ------------------
    "Survey Design & Sampling": {
        "domain": DOMAIN_STATISTICAL,
        "default_target": 75,
        "description": "Design of sample surveys, stratified sampling, cluster sampling, sample size estimation, and sampling frames.",
        "keywords": ["sampling", "survey design", "sample size", "stratified", "cluster", "sampling error", "nss", "field survey"]
    },
    "Descriptive & Inferential Statistics": {
        "domain": DOMAIN_STATISTICAL,
        "default_target": 70,
        "description": "Measures of central tendency, dispersion, probability distributions, hypothesis testing, and regression analysis.",
        "keywords": ["mean", "median", "variance", "standard deviation", "probability", "hypothesis testing", "p-value", "regression", "correlation"]
    },
    "National Accounts & GVA": {
        "domain": DOMAIN_STATISTICAL,
        "default_target": 70,
        "description": "Compilation of GDP, GVA, Gross Fixed Capital Formation, Input-Output tables, and System of National Accounts (SNA).",
        "keywords": ["national accounts", "gdp", "gva", "sna", "capital formation", "input output", "economic accounts", "constant prices"]
    },
    "Price Statistics & Indices": {
        "domain": DOMAIN_STATISTICAL,
        "default_target": 75,
        "description": "CPI, WPI, IIP index calculation, Laspeyres, Paasche, and Fisher index numbers, weighting diagrams.",
        "keywords": ["cpi", "wpi", "iip", "price index", "inflation", "laspeyres", "paasche", "fisher index", "index number"]
    },
    "SDG Indicators & Data Quality": {
        "domain": DOMAIN_STATISTICAL,
        "default_target": 70,
        "description": "National Indicator Framework (NIF) for Sustainable Development Goals, metadata standards, data auditing, and validation.",
        "keywords": ["sdg", "sustainable development goals", "nif", "data quality", "metadata", "validation", "audit", "indicators"]
    },

    # ------------------ B. Technical Competencies ------------------
    "Python for Statistical Analysis": {
        "domain": DOMAIN_TECHNICAL,
        "default_target": 70,
        "description": "Data wrangling, cleaning, Pandas, NumPy, statistical modeling, and automation of data pipelines.",
        "keywords": ["python", "pandas", "numpy", "dataframe", "data cleaning", "scipy", "statsmodels", "scripting"]
    },
    "R Programming & Econometrics": {
        "domain": DOMAIN_TECHNICAL,
        "default_target": 65,
        "description": "Statistical programming in R, tidyverse, ggplot2, econometric analysis, and survey data processing.",
        "keywords": ["r programming", "tidyverse", "ggplot2", "econometrics", "cran", "survey package", "r script"]
    },
    "SQL & Database Systems": {
        "domain": DOMAIN_TECHNICAL,
        "default_target": 70,
        "description": "Relational querying, aggregation, joins, database schema design, and extraction of microdata.",
        "keywords": ["sql", "database", "query", "select", "join", "group by", "rdbms", "postgresql", "mysql", "microdata"]
    },
    "Data Visualization & BI": {
        "domain": DOMAIN_TECHNICAL,
        "default_target": 70,
        "description": "Interactive dashboards, PowerBI, Tableau, Matplotlib, charting best practices, and statistical communication.",
        "keywords": ["visualization", "charts", "powerbi", "tableau", "matplotlib", "seaborn", "dashboard", "infographics"]
    },
    "AI/ML in Official Statistics": {
        "domain": DOMAIN_TECHNICAL,
        "default_target": 60,
        "description": "Machine learning, automated classification, NLP for survey text, anomaly detection in large datasets.",
        "keywords": ["ai", "machine learning", "ml", "classification", "clustering", "nlp", "anomaly detection", "neural network"]
    },

    # ------------------ C. Digital Governance ------------------
    "Cybersecurity & Data Privacy": {
        "domain": DOMAIN_DIGITAL_GOV,
        "default_target": 75,
        "description": "Protection of statistical microdata, encryption, cyber threats, secure dissemination, and DPDP Act compliance.",
        "keywords": ["cybersecurity", "cyber crime", "privacy", "dpdp", "encryption", "firewall", "data breach", "malware", "spoofing", "fraud"]
    },
    "Digital Public Infrastructure & Cloud": {
        "domain": DOMAIN_DIGITAL_GOV,
        "default_target": 65,
        "description": "Government Cloud (MeghRaj), Open Data principles, API exchange architectures, and digital workflows.",
        "keywords": ["dpi", "digital public infrastructure", "cloud", "meghraj", "open data", "api", "e-governance", "interoperability"]
    },

    # ------------------ D. Behavioural & Managerial ------------------
    "Statistical Ethics & Integrity": {
        "domain": DOMAIN_BEHAVIOURAL,
        "default_target": 80,
        "description": "UN Fundamental Principles of Official Statistics, professional ethics, respondent confidentiality, and impartiality.",
        "keywords": ["ethics", "integrity", "confidentiality", "un principles", "impartiality", "trust", "transparency"]
    },
    "Project Management & Communication": {
        "domain": DOMAIN_BEHAVIOURAL,
        "default_target": 70,
        "description": "Coordination of statistical operations, team leadership, stakeholder reporting, and change management.",
        "keywords": ["project management", "communication", "leadership", "teamwork", "coordination", "reporting", "decision making"]
    },
}


def get_all_competencies() -> List[str]:
    """Return all configured competency skill names."""
    return list(COMPETENCY_CATALOGUE.keys())


def get_skills_by_domain(domain: str) -> List[str]:
    """Return list of skill names belonging to a specific domain."""
    return [
        skill for skill, meta in COMPETENCY_CATALOGUE.items()
        if meta["domain"] == domain
    ]


def get_competency_meta(skill_name: str) -> Dict[str, Any]:
    """Retrieve metadata for a specific skill."""
    return COMPETENCY_CATALOGUE.get(skill_name, {
        "domain": DOMAIN_STATISTICAL,
        "default_target": 70,
        "description": f"Competency in {skill_name}.",
        "keywords": [skill_name.lower()]
    })


def get_default_target_scores() -> Dict[str, int]:
    """Return dict of {skill_name: target_score} across all competencies."""
    return {
        skill: meta["default_target"]
        for skill, meta in COMPETENCY_CATALOGUE.items()
    }


def map_text_to_competencies(text: str) -> List[Dict[str, Any]]:
    """Scan text keywords and return matching competencies with match counts."""
    text_lower = text.lower()
    matches = []
    for skill, meta in COMPETENCY_CATALOGUE.items():
        hits = sum(1 for kw in meta["keywords"] if kw in text_lower)
        if hits > 0:
            matches.append({
                "skill": skill,
                "domain": meta["domain"],
                "relevance_hits": hits
            })
    matches.sort(key=lambda x: x["relevance_hits"], reverse=True)
    return matches
