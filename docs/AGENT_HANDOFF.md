# Agent Handoff Documentation

## Project: AncientWorld - Ancient Buildings Image Analysis Platform

**Last Updated**: 2026-02-05
**Version**: 0.1.0
**Status**: Phase 1 - Foundation

---

## Table of Contents
1. [Project Overview](#project-overview)
2. [Architecture](#architecture)
3. [Agent Responsibilities](#agent-responsibilities)
4. [Current Status](#current-status)
5. [Next Steps](#next-steps)
6. [Code Conventions](#code-conventions)
7. [Testing Requirements](#testing-requirements)
8. [Deployment Procedures](#deployment-procedures)
9. [Known Issues](#known-issues)
10. [Resources](#resources)

---

## Project Overview

### Mission
Build a comprehensive platform to download, analyze, and extract insights from images of ancient buildings and structures using advanced image processing, mathematical analysis, and pattern recognition.

### Key Capabilities
- **Multi-source web crawling** from cultural heritage repositories
- **Advanced image analysis** (geometry, symmetry, patterns)
- **Mathematical analysis** (Fourier transforms, topology, symbolic geometry)
- **Pattern recognition** and ML-based classification
- **Sound/acoustic analysis** from geometric structures
- **REST API** and web dashboard for data access

### Target Users
- Architectural historians
- Researchers in medieval/ancient architecture
- Art historians studying Gothic tracery, rose windows, Islamic geometric patterns
- Digital humanities scholars
- Conservation specialists

---

## Architecture

### High-Level Components

```
┌─────────────────────────────────────────────────────────┐
│                    User Interfaces                      │
│          (CLI, Web Dashboard, API Clients)              │
└─────────────────────────────────────────────────────────┘
                          ↑
                          │
┌─────────────────────────────────────────────────────────┐
│                      REST API Layer                     │
│              (FastAPI - endpoints, auth)                │
└─────────────────────────────────────────────────────────┘
                          ↑
                          │
┌──────────────┬──────────────────┬──────────────────────┐
│   Crawlers   │     Analysis     │      Database        │
│              │                  │                      │
│ - Wikimedia  │ - Geometry       │ - SQLAlchemy ORM     │
│ - Europeana  │ - Symmetry       │ - PostgreSQL         │
│ - IIIF       │ - Patterns       │ - Migrations         │
│ - Gallica    │ - Fourier        │ - Queries            │
│ - LOC        │ - Sound          │                      │
└──────────────┴──────────────────┴──────────────────────┘
                          ↑
                          │
                   ┌──────────────┐
                   │  Data Store  │
                   │  (Files, DB) │
                   └──────────────┘
```

### Directory Structure
```
AncientWorld/
├── src/
│   ├── crawlers/          # Web scraping modules
│   │   ├── base_crawler.py
│   │   ├── wikimedia_crawler.py
│   │   ├── europeana_crawler.py
│   │   ├── iiif_crawler.py
│   │   ├── gallica_crawler.py
│   │   └── loc_crawler.py
│   ├── analysis/          # Image analysis
│   │   ├── geometry_detector.py
│   │   ├── symmetry_analyzer.py
│   │   ├── pattern_recognition.py
│   │   ├── fourier_analysis.py
│   │   ├── color_analysis.py
│   │   ├── tracery_analyzer.py
│   │   └── sound_analysis.py
│   ├── database/          # Data persistence
│   │   ├── models.py
│   │   ├── queries.py
│   │   └── migrations/
│   ├── api/               # REST API
│   │   ├── main.py
│   │   ├── routes/
│   │   ├── schemas.py
│   │   └── auth.py
│   ├── ui/                # User interfaces
│   │   ├── cli/
│   │   └── web/
│   └── utils/             # Shared utilities
│       ├── config_loader.py
│       ├── logger.py
│       ├── image_utils.py
│       └── file_utils.py
├── docs/                  # Documentation
├── tests/                 # Test suites
├── config/                # Configuration files
├── data/                  # Data storage
└── notebooks/             # Jupyter notebooks
```

---

## Agent Responsibilities

### 1. **Crawler Agent**
**Responsibility**: Acquire images and metadata from various sources

**Key Tasks**:
- Implement API-based scrapers (Wikimedia, Europeana)
- Implement IIIF manifest harvesters
- Handle rate limiting and politeness policies
- Deduplicate images using perceptual hashing
- Store metadata alongside images
- Respect robots.txt and licensing

**Key Files**:
- `src/crawlers/wikimedia_crawler.py`
- `src/crawlers/europeana_crawler.py`
- `src/crawlers/iiif_crawler.py`

**Dependencies**:
- scrapy, requests, beautifulsoup4
- imagehash (for deduplication)
- iiif, piffle (for IIIF support)

---

### 2. **Analysis Agent**
**Responsibility**: Extract features and insights from images

**Key Tasks**:
- Implement geometry detection (circles, lines, ellipses)
- Implement symmetry analysis (rotational, reflective)
- Implement Fourier analysis for periodicity
- Implement pattern recognition and matching
- Implement color analysis
- Create specialized analyzers (tracery, acoustic properties)

**Key Files**:
- `src/analysis/geometry_detector.py`
- `src/analysis/symmetry_analyzer.py`
- `src/analysis/pattern_recognition.py`
- `src/analysis/fourier_analysis.py`

**Dependencies**:
- opencv-python, scikit-image
- numpy, scipy, sympy
- torch, tensorflow (for ML-based recognition)
- gudhi (for topological analysis)

---

### 3. **Database Agent**
**Responsibility**: Design and manage data persistence

**Key Tasks**:
- Design SQLAlchemy models (Building, Image, AnalysisResult, etc.)
- Implement database migrations
- Create efficient queries
- Implement caching strategies
- Handle database backups

**Key Files**:
- `src/database/models.py`
- `src/database/queries.py`
- `src/database/migrations/`

**Dependencies**:
- sqlalchemy, alembic
- psycopg2-binary (PostgreSQL)

---

### 4. **API Agent**
**Responsibility**: Expose data and functionality via REST API

**Key Tasks**:
- Design REST endpoints
- Implement authentication/authorization
- Create Pydantic schemas for validation
- Implement pagination and filtering
- Add API documentation (OpenAPI/Swagger)

**Key Files**:
- `src/api/main.py`
- `src/api/routes/`
- `src/api/schemas.py`

**Dependencies**:
- fastapi, uvicorn
- pydantic

---

### 5. **UI Agent**
**Responsibility**: Create user interfaces

**Key Tasks**:
- Implement CLI commands
- Create web dashboard (Streamlit or Flask)
- Implement visualization tools
- Create interactive exploration tools

**Key Files**:
- `src/ui/cli/`
- `src/ui/web/`

**Dependencies**:
- click, typer, rich (CLI)
- streamlit, plotly (web dashboard)

---

## Current Status

### ✅ Completed
- [x] Git repository initialization
- [x] Project structure created
- [x] Requirements.txt with all dependencies
- [x] README.md with comprehensive documentation
- [x] Agent handoff documentation
- [x] .gitignore configuration

### 🔄 In Progress
- [ ] Web crawler implementation
- [ ] Database schema design
- [ ] Image analysis modules

### 📋 Pending
- [ ] REST API endpoints
- [ ] Web dashboard
- [ ] ML-based classification
- [ ] Comprehensive testing
- [ ] Deployment automation

---

## Next Steps

### Immediate (Week 1-2)
1. **Implement Base Crawler Framework**
   - Create `BaseCrawler` abstract class
   - Implement Scrapy pipelines for images
   - Set up deduplication logic

2. **Implement Wikimedia Crawler**
   - MediaWiki API integration
   - Image metadata extraction
   - License information capture

3. **Database Schema Design**
   - Define SQLAlchemy models
   - Create initial migration
   - Set up PostgreSQL database

4. **Basic Image Preprocessing**
   - Image loading utilities
   - Normalization functions
   - Format conversion

### Short-term (Week 3-4)
1. **Geometry Detection**
   - Hough circle/line detection
   - Center point estimation
   - Polar coordinate transformation

2. **Symmetry Analysis**
   - Rotational symmetry detection
   - Symmetry order estimation
   - Symmetry scoring functions

3. **CLI Interface**
   - Basic commands for crawling
   - Commands for analysis
   - Progress reporting

### Medium-term (Month 2-3)
1. **Advanced Analysis**
   - Fourier analysis implementation
   - Pattern recognition
   - Topological data analysis

2. **REST API**
   - Core endpoints
   - Authentication
   - API documentation

3. **Web Dashboard**
   - Image browser
   - Analysis visualization
   - Query interface

---

## Code Conventions

### Python Style
- Follow PEP 8
- Use type hints for all function signatures
- Maximum line length: 100 characters
- Use `black` for formatting
- Use `flake8` for linting

### Documentation
- All modules must have docstrings
- All classes and public methods must have docstrings
- Use Google-style docstrings
- Include usage examples in docstrings

### Example:
```python
def detect_circles(image: np.ndarray, min_radius: int = 10, max_radius: int = 500) -> List[Circle]:
    """
    Detect circles in an image using Hough Circle Transform.

    Args:
        image: Input grayscale image as numpy array
        min_radius: Minimum circle radius to detect
        max_radius: Maximum circle radius to detect

    Returns:
        List of Circle objects with (x, y, radius) parameters

    Example:
        >>> image = cv2.imread('rose_window.jpg', cv2.IMREAD_GRAYSCALE)
        >>> circles = detect_circles(image, min_radius=50, max_radius=300)
        >>> print(f"Found {len(circles)} circles")
    """
    pass
```

### Naming Conventions
- Classes: `PascalCase` (e.g., `GeometryDetector`)
- Functions/methods: `snake_case` (e.g., `detect_symmetry`)
- Constants: `UPPER_SNAKE_CASE` (e.g., `DEFAULT_THRESHOLD`)
- Private methods: prefix with `_` (e.g., `_preprocess_image`)

### Error Handling
- Use custom exceptions for domain-specific errors
- Always log errors with context
- Provide helpful error messages
- Use try-except blocks for external API calls

```python
class ImageProcessingError(Exception):
    """Base exception for image processing errors."""
    pass

class CircleDetectionError(ImageProcessingError):
    """Raised when circle detection fails."""
    pass
```

### Logging
- Use the configured logger from `src/utils/logger.py`
- Log levels:
  - DEBUG: Detailed diagnostic information
  - INFO: General informational messages
  - WARNING: Warning messages for recoverable issues
  - ERROR: Error messages for failures
  - CRITICAL: Critical errors requiring immediate attention

```python
import logging
logger = logging.getLogger(__name__)

logger.info("Starting circle detection")
logger.warning("Image resolution below recommended threshold")
logger.error("Failed to detect circles", exc_info=True)
```

---

## Testing Requirements

### Test Coverage
- Minimum 80% code coverage
- All public APIs must have tests
- Critical analysis functions must have extensive tests

### Test Types
1. **Unit Tests**: Test individual functions and classes
2. **Integration Tests**: Test component interactions
3. **End-to-End Tests**: Test complete workflows

### Test Organization
```
tests/
├── unit/
│   ├── test_geometry_detector.py
│   ├── test_symmetry_analyzer.py
│   └── test_crawlers.py
├── integration/
│   ├── test_crawler_to_db.py
│   └── test_analysis_pipeline.py
├── e2e/
│   └── test_full_workflow.py
└── fixtures/
    └── sample_images/
```

### Running Tests
```bash
# Run all tests
pytest tests/

# Run with coverage
pytest tests/ --cov=src --cov-report=html

# Run specific test file
pytest tests/unit/test_geometry_detector.py

# Run with verbose output
pytest tests/ -v
```

---

## Deployment Procedures

### Development Environment
1. Clone repository
2. Create virtual environment
3. Install dependencies: `pip install -r requirements.txt`
4. Set up configuration: `cp config/.env.example config/.env`
5. Initialize database: `alembic upgrade head`
6. Run tests: `pytest tests/`

### Production Environment
1. Use Docker for containerization
2. Set up PostgreSQL database
3. Configure environment variables
4. Set up reverse proxy (nginx)
5. Enable SSL/TLS
6. Configure logging and monitoring
7. Set up backups

### Git Workflow
1. Create feature branch: `git checkout -b feature/your-feature`
2. Make changes and test
3. Commit with descriptive messages
4. Push to GitHub: `git push origin feature/your-feature`
5. Create pull request
6. After review and approval, merge to main
7. Tag releases: `git tag -a v0.1.0 -m "Release v0.1.0"`

### Update Procedures
After completing each task:
1. Commit changes with descriptive message
2. Update this handoff document with current status
3. Push to GitHub
4. Update project roadmap in README.md

---

## Known Issues

### Current Limitations
1. No Europeana API key yet (need to register)
2. IIIF implementation not yet tested with all sources
3. Large image processing may cause memory issues
4. No distributed processing yet (single machine only)

### Future Considerations
1. **Scalability**: Implement distributed crawling and processing
2. **Performance**: Optimize image processing pipeline
3. **Storage**: Implement cloud storage for large datasets
4. **Security**: Add comprehensive authentication/authorization
5. **Monitoring**: Add application monitoring and alerting

---

## Resources

### Documentation Links
- [OpenCV Documentation](https://docs.opencv.org/)
- [scikit-image Documentation](https://scikit-image.org/docs/stable/)
- [IIIF API Specification](https://iiif.io/api/image/3.0/)
- [Scrapy Documentation](https://docs.scrapy.org/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [SQLAlchemy Documentation](https://docs.sqlalchemy.org/)

### Key Research Papers
- Hough Circle Transform: Duda & Hart (1972)
- SIFT Features: Lowe (1999)
- Persistent Homology: Edelsbrunner et al. (2002)

### Cultural Heritage APIs
- [Wikimedia Commons API](https://commons.wikimedia.org/wiki/Commons:API)
- [Europeana API](https://www.europeana.eu/en/apis)
- [Library of Congress API](https://www.loc.gov/apis/)
- [IIIF Resources](https://iiif.io/)

### External Tools
- ImageJ/Fiji: For manual image analysis exploration
- QGIS: For geographic visualization of building locations
- Blender: For 3D reconstruction experiments

---

## Contact and Support

### Project Maintainer
- GitHub: https://github.com/robertwaltos/AncientWorld

### GitHub Repository
- Repository: https://github.com/robertwaltos/AncientWorld
- Issues: https://github.com/robertwaltos/AncientWorld/issues
- Wiki: https://github.com/robertwaltos/AncientWorld/wiki

### Getting Help
1. Check documentation in `docs/`
2. Search existing GitHub issues
3. Review code comments and docstrings
4. Create new issue with detailed description

---

## Handoff Checklist

When handing off to another agent/developer:

- [ ] Review this document completely
- [ ] Check current status section
- [ ] Review known issues
- [ ] Check requirements.txt is up to date
- [ ] Verify all tests pass
- [ ] Check code follows conventions
- [ ] Review recent commits
- [ ] Update roadmap if needed
- [ ] Ensure all documentation is current
- [ ] Note any API keys or credentials needed

---

**Document Version**: 1.0
**Last Updated By**: Initial Setup Agent
**Next Review Date**: 2026-02-12
