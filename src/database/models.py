"""
Database models for AncientWorld.

SQLAlchemy models for buildings, images, and analysis results.
"""

from datetime import datetime
from typing import Optional, List
from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    DateTime,
    Text,
    ForeignKey,
    Boolean,
    JSON,
    create_engine,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, Session
from sqlalchemy.sql import func

Base = declarative_base()


class Building(Base):
    """
    Represents a historical building or structure.
    """

    __tablename__ = "buildings"

    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False, index=True)
    location = Column(String(255), index=True)
    country = Column(String(100), index=True)
    latitude = Column(Float)
    longitude = Column(Float)
    construction_date = Column(String(100))
    architectural_style = Column(String(100), index=True)
    building_type = Column(String(100), index=True)  # cathedral, temple, mosque, etc.
    description = Column(Text)
    unesco_site = Column(Boolean, default=False)
    website = Column(String(500))
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    # Relationships
    images = relationship("Image", back_populates="building", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Building(id={self.id}, name='{self.name}', location='{self.location}')>"


class Image(Base):
    """
    Represents an image of a building or architectural element.
    """

    __tablename__ = "images"

    id = Column(Integer, primary_key=True)
    building_id = Column(Integer, ForeignKey("buildings.id"), nullable=True, index=True)
    filepath = Column(String(500), nullable=False, unique=True)
    url = Column(String(1000))
    title = Column(String(500))
    source = Column(String(100), index=True)  # wikimedia, europeana, etc.
    width = Column(Integer)
    height = Column(Integer)
    file_size = Column(Integer)  # bytes
    format = Column(String(20))  # JPEG, PNG, TIFF
    sha256 = Column(String(64), unique=True, index=True)
    phash = Column(String(32), index=True)  # perceptual hash
    license = Column(String(200))
    author = Column(String(200))
    date_taken = Column(String(100))
    tags = Column(JSON)  # List of tags
    metadata = Column(JSON)  # Additional metadata
    downloaded_at = Column(DateTime, default=func.now())
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    # Relationships
    building = relationship("Building", back_populates="images")
    analyses = relationship("Analysis", back_populates="image", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Image(id={self.id}, title='{self.title}', source='{self.source}')>"


class Analysis(Base):
    """
    Represents analysis results for an image.
    """

    __tablename__ = "analyses"

    id = Column(Integer, primary_key=True)
    image_id = Column(Integer, ForeignKey("images.id"), nullable=False, index=True)
    analysis_type = Column(String(100), nullable=False, index=True)
    # Types: geometry, symmetry, pattern, fourier, color, tracery, sound
    version = Column(String(20))  # Algorithm version
    results = Column(JSON, nullable=False)  # Analysis results as JSON
    confidence = Column(Float)  # Confidence score 0-1
    processing_time = Column(Float)  # seconds
    error_message = Column(Text)  # If analysis failed
    created_at = Column(DateTime, default=func.now())

    # Relationships
    image = relationship("Image", back_populates="analyses")

    def __repr__(self):
        return f"<Analysis(id={self.id}, type='{self.analysis_type}', image_id={self.image_id})>"


class GeometryFeature(Base):
    """
    Specific geometric features detected in images.
    """

    __tablename__ = "geometry_features"

    id = Column(Integer, primary_key=True)
    image_id = Column(Integer, ForeignKey("images.id"), nullable=False, index=True)
    feature_type = Column(String(50), nullable=False, index=True)
    # Types: circle, ellipse, line, arc, polygon
    center_x = Column(Float)
    center_y = Column(Float)
    radius = Column(Float)
    width = Column(Float)
    height = Column(Float)
    angle = Column(Float)  # degrees
    confidence = Column(Float)
    parameters = Column(JSON)  # Additional parameters
    created_at = Column(DateTime, default=func.now())

    def __repr__(self):
        return f"<GeometryFeature(id={self.id}, type='{self.feature_type}')>"


class SymmetryAnalysis(Base):
    """
    Symmetry analysis results for images.
    """

    __tablename__ = "symmetry_analyses"

    id = Column(Integer, primary_key=True)
    image_id = Column(Integer, ForeignKey("images.id"), nullable=False, index=True)
    symmetry_type = Column(String(50), nullable=False)  # rotational, reflective, both
    symmetry_order = Column(Integer)  # n-fold symmetry
    confidence = Column(Float)
    center_x = Column(Float)
    center_y = Column(Float)
    axes = Column(JSON)  # Symmetry axes
    score = Column(Float)  # Symmetry score
    created_at = Column(DateTime, default=func.now())

    def __repr__(self):
        return f"<SymmetryAnalysis(id={self.id}, type='{self.symmetry_type}', order={self.symmetry_order})>"


def init_db(database_url: str) -> Session:
    """
    Initialize database and return session.

    Args:
        database_url: SQLAlchemy database URL

    Returns:
        SQLAlchemy Session object

    Example:
        >>> session = init_db("sqlite:///data/ancientworld.db")
        >>> buildings = session.query(Building).all()
    """
    engine = create_engine(database_url, echo=False)
    Base.metadata.create_all(engine)
    from sqlalchemy.orm import sessionmaker
    Session = sessionmaker(bind=engine)
    return Session()


def create_tables(database_url: str):
    """
    Create all tables in the database.

    Args:
        database_url: SQLAlchemy database URL
    """
    engine = create_engine(database_url, echo=True)
    Base.metadata.create_all(engine)
    print("✓ Database tables created successfully")


if __name__ == "__main__":
    # Create tables in default SQLite database
    create_tables("sqlite:///data/ancientworld.db")
