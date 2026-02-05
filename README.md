# AncientWorld

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.10%2B-blue)
![Status](https://img.shields.io/badge/status-in%20development-yellow)

## Overview

**AncientWorld** is a comprehensive platform for downloading, analyzing, and understanding images of ancient buildings and structures. The system combines advanced image processing, mathematical analysis, pattern recognition, and machine learning to extract insights from historical architecture images.

## Features

### Data Acquisition
- **Multi-source Web Crawling**: Automated scrapers for:
  - Wikimedia Commons (MediaWiki API)
  - Europeana (cultural heritage aggregator)
  - IIIF-compliant repositories (Gallica, Library of Congress, British Library, V&A)
  - Library of Congress Prints & Photographs
  - British Library digitized manuscripts

### Image Analysis
- **Geometry Detection**: Circles, ellipses, lines, arcs using Hough transforms
- **Symmetry Analysis**: Rotational and reflective symmetry detection
- **Pattern Recognition**: Identify repeating motifs and structural elements
- **Fourier Analysis**: Frequency domain analysis for periodicity detection
- **Tracery Analysis**: Specialized Gothic tracery and rose window analysis
- **Color Analysis**: Palette extraction and color distribution

### Mathematical Analysis
- **Topological Data Analysis**: Using GUDHI for persistent homology
- **Symbolic Geometry**: SymPy-based geometric reasoning
- **Frequency Analysis**: FFT-based angular and radial analysis
- **Symmetry Groups**: Mathematical classification of symmetry

### Sound and Acoustic Analysis
- Analysis of acoustic properties derived from geometric structures
- Resonance pattern detection
- Harmonic analysis of architectural proportions

## Project Structure

```
AncientWorld/
├── src/
│   ├── crawlers/          # Web scrapers for various sources
│   ├── analysis/          # Image analysis and pattern recognition
│   ├── database/          # Database models and queries
│   ├── api/              # REST API endpoints
│   ├── ui/               # User interfaces (CLI, Web)
│   └── utils/            # Utility functions and helpers
├── docs/                 # Documentation and handoff documents
├── tests/                # Unit and integration tests
├── config/               # Configuration files
├── data/                 # Data storage
│   ├── raw/             # Raw downloaded images
│   ├── processed/       # Processed images
│   ├── images/          # Organized image database
│   └── cache/           # Temporary cache
├── notebooks/            # Jupyter notebooks for exploration
└── BEST_PRACTICES/       # Development best practices

```

## Installation

### Prerequisites
- Python 3.10 or higher
- Git
- Virtual environment tool (venv, conda, etc.)

### Setup

1. Clone the repository:
```bash
git clone https://github.com/robertwaltos/AncientWorld.git
cd AncientWorld
```

2. Create and activate a virtual environment:
```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

# Linux/Mac
source .venv/bin/activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Configure environment variables:
```bash
cp config/.env.example config/.env
# Edit config/.env with your API keys
```

## Quick Start

### 1. Run Web Crawler
```bash
# Crawl Wikimedia Commons for rose windows
python -m src.crawlers.wikimedia_crawler --query "rose window" --limit 100

# Crawl from IIIF sources
python -m src.crawlers.iiif_crawler --source gallica --query "rosace"
```

### 2. Analyze Images
```bash
# Analyze geometry of a single image
python -m src.analysis.geometry_detector --image data/raw/chartres_rose.jpg

# Batch analyze all downloaded images
python -m src.analysis.batch_analyzer --input data/raw/ --output data/processed/
```

### 3. Launch API Server
```bash
uvicorn src.api.main:app --reload
```

### 4. Start Web UI
```bash
streamlit run src/ui/web/dashboard.py
```

## Key Technologies

### Image Processing
- **OpenCV**: Feature detection, Hough transforms, geometric analysis
- **scikit-image**: Edge detection, segmentation, circular transforms
- **Pillow**: Image I/O and basic operations

### Scientific Computing
- **NumPy**: Array operations and numerical computing
- **SciPy**: FFT, optimization, signal processing
- **SymPy**: Symbolic mathematics and geometry

### Machine Learning
- **PyTorch**: Deep learning for pattern recognition
- **scikit-learn**: Classical ML algorithms
- **GUDHI**: Topological data analysis

### Web Scraping
- **Scrapy**: High-performance web crawling framework
- **Requests**: HTTP library for API interactions
- **Beautiful Soup**: HTML parsing

### Database
- **SQLAlchemy**: ORM for database management
- **PostgreSQL**: Primary database (SQLite for development)

## Research Sources

The platform is designed to work with the following image sources:

1. **Gallica (BnF)**: 19th/20th century photographs and architectural plates
2. **Library of Congress**: Early 20th-century photography and design drawings
3. **V&A Collections**: High-quality stained glass photography
4. **IIIF Resources**: High-resolution zoomable images with consistent metadata
5. **British Library**: Medieval manuscripts and early-modern diagrams

## Analysis Workflow

1. **Acquisition**: Download high-resolution images via web crawlers
2. **Preprocessing**: Clean, normalize, and enhance images
3. **Detection**: Extract geometric features (circles, lines, symmetry)
4. **Analysis**: Apply mathematical and frequency analysis
5. **Pattern Recognition**: Identify motifs and structural patterns
6. **Classification**: Categorize by architecture style, period, location
7. **Visualization**: Generate reports and visual summaries
8. **Storage**: Index results in database with metadata

## Key Algorithms

### Rose Window Analysis Pipeline
1. Convert to polar coordinates around window center
2. Apply FFT to detect angular periodicity
3. Use Hough transforms for circles and lines
4. Estimate symmetry order (n-fold rotational symmetry)
5. Extract tracery pattern parameters

### Symmetry Detection
1. Find image center point
2. Generate rotated copies at angles 360°/n
3. Compute correlation scores
4. Identify symmetry group classification

### Pattern Matching
1. Extract keypoints using ORB/SIFT
2. Match features across different buildings
3. Cluster similar motifs
4. Build pattern library

## Configuration

Create a `config/.env` file:

```env
# API Keys
EUROPEANA_API_KEY=your_key_here
WIKIMEDIA_USER_AGENT=AncientWorld/0.1

# Database
DATABASE_URL=postgresql://user:pass@localhost/ancientworld

# Crawling
DOWNLOAD_DELAY=1.0
CONCURRENT_REQUESTS=2
IMAGES_STORE=data/images

# Analysis
MIN_IMAGE_WIDTH=800
MIN_IMAGE_HEIGHT=800
```

## Agent Handoff Documentation

See [docs/AGENT_HANDOFF.md](docs/AGENT_HANDOFF.md) for detailed documentation on:
- Agent responsibilities and workflows
- Task delegation procedures
- Code conventions and standards
- Testing requirements
- Deployment procedures

## Contributing

This is an active research project. Contributions are welcome!

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests: `pytest tests/`
5. Submit a pull request

## License

MIT License - see [LICENSE](LICENSE) file for details

## Citations

### Key Resources
- IIIF Image API Documentation: https://iiif.io/api/image/3.0/
- OpenCV Feature Detection: https://docs.opencv.org/4.x/db/d27/tutorial_py_table_of_contents_feature2d.html
- scikit-image Hough Transforms: https://scikit-image.org/docs/stable/auto_examples/edges/plot_circular_elliptical_hough_transform.html
- GUDHI Documentation: https://gudhi.inria.fr/python/latest/

## Contact

Project maintained by the AncientWorld Team
- GitHub: https://github.com/robertwaltos/AncientWorld
- Issues: https://github.com/robertwaltos/AncientWorld/issues

## Roadmap

### Phase 1: Foundation (Current)
- [x] Project structure setup
- [x] Core dependencies installation
- [ ] Basic web crawlers
- [ ] Database schema
- [ ] Image preprocessing pipeline

### Phase 2: Analysis
- [ ] Geometry detection implementation
- [ ] Symmetry analysis
- [ ] Pattern recognition
- [ ] Fourier analysis

### Phase 3: Advanced Features
- [ ] ML-based classification
- [ ] Topological data analysis
- [ ] Sound analysis integration
- [ ] Advanced visualization

### Phase 4: Production
- [ ] REST API
- [ ] Web dashboard
- [ ] Documentation
- [ ] Deployment automation

## Acknowledgments

This project builds on research and resources from:
- Bibliothèque nationale de France (Gallica)
- Library of Congress
- Victoria and Albert Museum
- Europeana Foundation
- IIIF Consortium
