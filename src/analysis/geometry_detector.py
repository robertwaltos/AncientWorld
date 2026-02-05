"""
Geometry detection module for ancient building images.

Detects circles, ellipses, lines, and other geometric features using
Hough transforms and other computer vision techniques.
"""

import logging
from typing import List, Tuple, Optional, Dict, Any
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np
from scipy import ndimage
from skimage.transform import hough_circle, hough_circle_peaks
from skimage.feature import canny

logger = logging.getLogger(__name__)


@dataclass
class Circle:
    """Represents a detected circle."""
    x: float
    y: float
    radius: float
    confidence: float = 1.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "circle",
            "x": float(self.x),
            "y": float(self.y),
            "radius": float(self.radius),
            "confidence": float(self.confidence),
        }


@dataclass
class Line:
    """Represents a detected line."""
    rho: float
    theta: float
    confidence: float = 1.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "line",
            "rho": float(self.rho),
            "theta": float(self.theta),
            "confidence": float(self.confidence),
        }


@dataclass
class Ellipse:
    """Represents a detected ellipse."""
    x: float
    y: float
    major_axis: float
    minor_axis: float
    angle: float
    confidence: float = 1.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "ellipse",
            "x": float(self.x),
            "y": float(self.y),
            "major_axis": float(self.major_axis),
            "minor_axis": float(self.minor_axis),
            "angle": float(self.angle),
            "confidence": float(self.confidence),
        }


class GeometryDetector:
    """
    Detector for geometric features in images.

    Provides methods for detecting circles, lines, ellipses, and estimating
    image center points for radial structures like rose windows.

    Example:
        >>> detector = GeometryDetector()
        >>> image = cv2.imread("rose_window.jpg")
        >>> circles = detector.detect_circles(image)
        >>> print(f"Found {len(circles)} circles")
    """

    def __init__(
        self,
        min_circle_radius: int = 10,
        max_circle_radius: int = 500,
        circle_threshold: float = 0.5,
        line_threshold: int = 100,
    ):
        """
        Initialize geometry detector.

        Args:
            min_circle_radius: Minimum circle radius to detect
            max_circle_radius: Maximum circle radius to detect
            circle_threshold: Threshold for circle detection (0-1)
            line_threshold: Threshold for line detection
        """
        self.min_circle_radius = min_circle_radius
        self.max_circle_radius = max_circle_radius
        self.circle_threshold = circle_threshold
        self.line_threshold = line_threshold

    def preprocess_image(self, image: np.ndarray) -> np.ndarray:
        """
        Preprocess image for geometry detection.

        Args:
            image: Input image (BGR or grayscale)

        Returns:
            Preprocessed grayscale image
        """
        # Convert to grayscale if needed
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image.copy()

        # Denoise
        gray = cv2.GaussianBlur(gray, (5, 5), 0)

        # Enhance contrast
        gray = cv2.equalizeHist(gray)

        return gray

    def detect_circles(self, image: np.ndarray) -> List[Circle]:
        """
        Detect circles in an image using Hough Circle Transform.

        Args:
            image: Input image (BGR or grayscale)

        Returns:
            List of Circle objects

        Example:
            >>> detector = GeometryDetector()
            >>> image = cv2.imread("chartres_rose.jpg")
            >>> circles = detector.detect_circles(image)
            >>> for circle in circles:
            ...     print(f"Circle at ({circle.x}, {circle.y}), r={circle.radius}")
        """
        gray = self.preprocess_image(image)

        # OpenCV Hough Circle Transform
        circles_cv = cv2.HoughCircles(
            gray,
            cv2.HOUGH_GRADIENT,
            dp=1,
            minDist=50,
            param1=50,
            param2=30,
            minRadius=self.min_circle_radius,
            maxRadius=self.max_circle_radius,
        )

        circles = []
        if circles_cv is not None:
            circles_cv = np.uint16(np.around(circles_cv))
            for circle_data in circles_cv[0, :]:
                x, y, r = circle_data
                circles.append(Circle(x=float(x), y=float(y), radius=float(r)))

        logger.info(f"Detected {len(circles)} circles")
        return circles

    def detect_lines(self, image: np.ndarray) -> List[Line]:
        """
        Detect lines in an image using Hough Line Transform.

        Args:
            image: Input image (BGR or grayscale)

        Returns:
            List of Line objects
        """
        gray = self.preprocess_image(image)

        # Edge detection
        edges = cv2.Canny(gray, 50, 150, apertureSize=3)

        # Hough Line Transform
        lines_cv = cv2.HoughLines(edges, 1, np.pi / 180, self.line_threshold)

        lines = []
        if lines_cv is not None:
            for line_data in lines_cv:
                rho, theta = line_data[0]
                lines.append(Line(rho=float(rho), theta=float(theta)))

        logger.info(f"Detected {len(lines)} lines")
        return lines

    def estimate_center(self, image: np.ndarray, circles: Optional[List[Circle]] = None) -> Tuple[float, float]:
        """
        Estimate the center point of a radial structure (e.g., rose window).

        Args:
            image: Input image
            circles: Pre-detected circles (if None, will detect automatically)

        Returns:
            Tuple of (center_x, center_y)
        """
        if circles is None:
            circles = self.detect_circles(image)

        if not circles:
            # Fallback to image center
            h, w = image.shape[:2]
            return (w / 2, h / 2)

        # Weight by radius (larger circles more important)
        total_weight = 0
        weighted_x = 0
        weighted_y = 0

        for circle in circles:
            weight = circle.radius
            weighted_x += circle.x * weight
            weighted_y += circle.y * weight
            total_weight += weight

        if total_weight == 0:
            h, w = image.shape[:2]
            return (w / 2, h / 2)

        center_x = weighted_x / total_weight
        center_y = weighted_y / total_weight

        logger.info(f"Estimated center: ({center_x:.1f}, {center_y:.1f})")
        return (center_x, center_y)

    def to_polar_coordinates(
        self,
        image: np.ndarray,
        center: Optional[Tuple[float, float]] = None,
    ) -> np.ndarray:
        """
        Convert image to polar coordinates around a center point.

        Useful for analyzing radial symmetry and periodicity.

        Args:
            image: Input image
            center: Center point (x, y). If None, will be estimated.

        Returns:
            Image in polar coordinates
        """
        if center is None:
            center = self.estimate_center(image)

        h, w = image.shape[:2]
        cx, cy = center

        # Determine max radius
        max_radius = int(np.sqrt((w - cx) ** 2 + (h - cy) ** 2))

        # Create polar image
        polar = cv2.linearPolar(
            image,
            (cx, cy),
            max_radius,
            cv2.WARP_FILL_OUTLIERS,
        )

        return polar

    def analyze_geometry(self, image: np.ndarray) -> Dict[str, Any]:
        """
        Perform comprehensive geometry analysis on an image.

        Args:
            image: Input image

        Returns:
            Dictionary containing all detected geometric features

        Example:
            >>> detector = GeometryDetector()
            >>> image = cv2.imread("cathedral.jpg")
            >>> results = detector.analyze_geometry(image)
            >>> print(f"Circles: {len(results['circles'])}")
            >>> print(f"Lines: {len(results['lines'])}")
            >>> print(f"Center: {results['center']}")
        """
        logger.info("Starting comprehensive geometry analysis")

        circles = self.detect_circles(image)
        lines = self.detect_lines(image)
        center = self.estimate_center(image, circles)

        results = {
            "circles": [c.to_dict() for c in circles],
            "lines": [l.to_dict() for l in lines],
            "center": {"x": center[0], "y": center[1]},
            "num_circles": len(circles),
            "num_lines": len(lines),
        }

        logger.info(f"Analysis complete: {len(circles)} circles, {len(lines)} lines")
        return results


def visualize_geometry(
    image: np.ndarray,
    circles: List[Circle],
    lines: List[Line],
    center: Optional[Tuple[float, float]] = None,
    output_path: Optional[Path] = None,
) -> np.ndarray:
    """
    Visualize detected geometry on an image.

    Args:
        image: Input image
        circles: Detected circles
        lines: Detected lines
        center: Center point to mark
        output_path: Path to save visualization (optional)

    Returns:
        Image with geometry overlaid
    """
    vis = image.copy()

    # Draw circles
    for circle in circles:
        cv2.circle(
            vis,
            (int(circle.x), int(circle.y)),
            int(circle.radius),
            (0, 255, 0),
            2,
        )
        cv2.circle(vis, (int(circle.x), int(circle.y)), 3, (0, 0, 255), -1)

    # Draw lines
    for line in lines:
        rho, theta = line.rho, line.theta
        a = np.cos(theta)
        b = np.sin(theta)
        x0 = a * rho
        y0 = b * rho
        x1 = int(x0 + 1000 * (-b))
        y1 = int(y0 + 1000 * (a))
        x2 = int(x0 - 1000 * (-b))
        y2 = int(y0 - 1000 * (a))
        cv2.line(vis, (x1, y1), (x2, y2), (255, 0, 0), 1)

    # Draw center
    if center:
        cv2.circle(vis, (int(center[0]), int(center[1])), 10, (0, 0, 255), -1)
        cv2.circle(vis, (int(center[0]), int(center[1])), 12, (255, 255, 255), 2)

    if output_path:
        cv2.imwrite(str(output_path), vis)
        logger.info(f"Saved visualization to {output_path}")

    return vis


def main():
    """CLI entry point for geometry detection."""
    import argparse

    parser = argparse.ArgumentParser(description="Detect geometric features in images")
    parser.add_argument("image", type=Path, help="Input image path")
    parser.add_argument("--output", type=Path, help="Output visualization path")
    parser.add_argument("--min-radius", type=int, default=10, help="Minimum circle radius")
    parser.add_argument("--max-radius", type=int, default=500, help="Maximum circle radius")

    args = parser.parse_args()

    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # Load image
    image = cv2.imread(str(args.image))
    if image is None:
        print(f"Error: Could not load image: {args.image}")
        return

    # Detect geometry
    detector = GeometryDetector(
        min_circle_radius=args.min_radius,
        max_circle_radius=args.max_radius,
    )
    results = detector.analyze_geometry(image)

    # Print results
    print(f"\nGeometry Analysis Results:")
    print(f"  Circles detected: {results['num_circles']}")
    print(f"  Lines detected: {results['num_lines']}")
    print(f"  Estimated center: ({results['center']['x']:.1f}, {results['center']['y']:.1f})")

    # Visualize if output path provided
    if args.output:
        circles = [Circle(**c) for c in results["circles"]]
        lines = [Line(**l) for l in results["lines"]]
        center = (results["center"]["x"], results["center"]["y"])
        visualize_geometry(image, circles, lines, center, args.output)
        print(f"\n✓ Visualization saved to {args.output}")


if __name__ == "__main__":
    main()
