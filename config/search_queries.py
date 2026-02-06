"""
Centralized Search Queries Configuration

Single source of truth for all discovery scripts.
All search terms are consolidated here to avoid duplication.
"""

# Main architectural search queries used by all discovery sources
QUERIES = [
    # General architecture
    "architecture",
    "architectural",
    "architecture drawing",
    "architectural drawing",
    "architectural plan",
    "architectural elevation",
    "building",
    "structure",
    "building facade",
    "architectural ornament",
    "architectural detail",
    "architectural geometry",

    # Religious architecture
    "cathedral",
    "cathedral architecture",
    "cathedral facade",
    "cathedral portal",
    "church",
    "church architecture",
    "church facade",
    "chapel",
    "basilica",
    "mosque",
    "mosque architecture",
    "temple",
    "temple facade",
    "synagogue",
    "medieval church",
    "medieval monastery",
    "romanesque church",

    # Architectural styles
    "gothic architecture",
    "gothic cathedral",
    "gothic tracery",
    "gothic vault",
    "romanesque",
    "romanesque architecture",
    "byzantine architecture",
    "byzantine mosaic",
    "baroque architecture",
    "renaissance architecture",
    "medieval architecture",
    "classical architecture",
    "islamic architecture",
    "islamic geometric",
    "pre-1920 architecture",

    # Architectural elements
    "rose window",
    "flying buttress",
    "column",
    "arch",
    "dome",
    "glass dome",
    "vault",
    "vault construction",
    "tracery",
    "ornament geometry",
    "geometric ornament",
    "geometric pattern",
    "muqarnas",
    "zellige",
    "stereotomy",
    "masonry",
    "ornate masonry",
    "stone cutting",

    # Monumental & institutional buildings
    "monumental architecture",
    "institutional architecture",
    "ornate public buildings",
    "exhibition hall",
    "terra cotta palace",

    # Urban archaeology & construction history
    "re-grading",
    "excavations",
    "city fires",
    "reconstructions",
    "urban excavation",
    "buried first floor",
    "sunken building",
    "excavated city blocks",
    "subgrade architecture",
    "street elevation",

    # Transportation & infrastructure
    "train",
    "railroad tracks construction",

    # Construction techniques & history
    "rapid construction",
    "missing construction records",
    "lost construction techniques",
    "master craftsmen",
    "architectural sophistication",

    # Historical documentation
    "historical street photography",

   # Scale and proportions (CloudGPT additions)
    "oversized doorways",
    "monumental doorways",
    "tall doorways",
    "high ceiling interiors",
    "floor to ceiling windows",
    "towering windows",
    "architectural scale",
    "nonstandard proportions",
    "monumental scale architecture",

    # Interior architecture
    "grand staircases",
    "monumental staircases",
    "stair riser height",
    "historic staircases",
    "primary staircases",
    "secondary staircases",
    "servant staircases",
    "vaulted interiors",
    "monumental halls",

    # Building modifications
    "building modification records",
    "historic building alterations",
    "lowered doorways",
    "false ceilings",
    "drop ceilings",
    "window resizing",
    "architectural retrofitting",

    # Furniture scale
    "oversized furniture",
    "historic furniture scale",
    "antique furniture dimensions",
    "19th century furniture",
    "museum furniture collections",
]


# French queries for Gallica (French National Library)
GALLICA_QUERIES = [
    # Gothic detailed
    ("cathedrale gothique", "image"),
    ("architecture gothique", "image"),
    ("eglise gothique", "image"),
    ("rosace gothique", "image"),
    ("remplage", "image"),
    ("arc-boutant", "image"),
    ("voute gothique", "image"),

    # Romanesque
    ("architecture romane", "image"),
    ("eglise romane", "image"),

    # Byzantine & Islamic
    ("architecture byzantine", "image"),
    ("architecture islamique", "image"),
    ("geometrie islamique", "image"),

    # Technical
    ("stereotomie", "image"),
    ("coupe de pierre", "image"),
    ("trace geometrique", "image"),
    ("elevation architecturale", "image"),
    ("plan architectural", "image"),

    # Urban & historical
    ("excavations urbaines", "image"),
    ("photographie historique rue", "image"),
    ("reconstruction ville", "image"),
    ("architecture monumentale", "image"),
]


def get_queries_for_source(source: str) -> list:
    """
    Get appropriate queries for a specific source.

    Args:
        source: Source name (e.g., 'met', 'europeana', 'gallica', etc.)

    Returns:
        List of query strings or tuples (for Gallica)
    """
    if source.lower() in ['gallica', 'gallica_direct']:
        return GALLICA_QUERIES
    else:
        return QUERIES
