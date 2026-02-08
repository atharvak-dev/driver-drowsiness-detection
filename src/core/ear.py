"""
Eye Aspect Ratio (EAR) Calculation Module
Production-grade implementation with validation and error handling.
"""
import numpy as np
import logging
from typing import List, Tuple, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class EARResult:
    """Result of EAR calculation."""
    ear: float
    left_ear: float
    right_ear: float
    is_valid: bool
    confidence: float = 1.0
    
    @property
    def eyes_closed(self) -> bool:
        """Check if eyes are likely closed based on EAR."""
        return self.is_valid and self.ear < 0.2


class EARCalculator:
    """
    Eye Aspect Ratio calculator with validation and error handling.
    
    EAR = (||p2-p6|| + ||p3-p5||) / (2 * ||p1-p4||)
    where p1-p6 are the 6 eye landmark points.
    """
    
    # MediaPipe Face Mesh landmark indices for eyes
    LEFT_EYE_INDICES = [362, 385, 387, 263, 373, 380]
    RIGHT_EYE_INDICES = [33, 160, 158, 133, 153, 144]
    
    def __init__(self, min_ear: float = 0.0, max_ear: float = 1.0):
        """
        Initialize EAR calculator.
        
        Args:
            min_ear: Minimum valid EAR value (filter noise)
            max_ear: Maximum valid EAR value (filter outliers)
        """
        self.min_ear = min_ear
        self.max_ear = max_ear
        self._consecutive_failures = 0
        self._max_failures = 10
    
    @staticmethod
    def euclidean_distance(p1: Tuple[float, float], p2: Tuple[float, float]) -> float:
        """
        Calculate Euclidean distance between two points.
        
        Args:
            p1: First point (x, y)
            p2: Second point (x, y)
            
        Returns:
            Euclidean distance
        """
        return np.linalg.norm(np.array(p1) - np.array(p2))
    
    def calculate_single_eye_ear(
        self, 
        landmarks: List[Tuple[int, int]], 
        eye_indices: List[int]
    ) -> Optional[float]:
        """
        Calculate EAR for a single eye.
        
        Args:
            landmarks: List of (x, y) facial landmark coordinates
            eye_indices: List of 6 indices for eye landmarks
            
        Returns:
            EAR value or None if calculation fails
        """
        try:
            if len(eye_indices) != 6:
                logger.warning(f"Invalid eye indices count: {len(eye_indices)}, expected 6")
                return None
            
            # Extract eye landmarks
            eye_points = [landmarks[idx] for idx in eye_indices]
            
            # Calculate vertical distances
            # Points: [outer, top-outer, top-inner, inner, bottom-inner, bottom-outer]
            v1 = self.euclidean_distance(eye_points[1], eye_points[5])
            v2 = self.euclidean_distance(eye_points[2], eye_points[4])
            
            # Calculate horizontal distance
            h = self.euclidean_distance(eye_points[0], eye_points[3])
            
            # Prevent division by zero
            if h < 1e-6:
                logger.debug("Horizontal distance too small, possible detection error")
                return None
            
            ear = (v1 + v2) / (2.0 * h)
            
            # Validate range
            if not (self.min_ear <= ear <= self.max_ear):
                logger.debug(f"EAR out of valid range: {ear}")
                return None
            
            return float(ear)
            
        except (IndexError, TypeError, ValueError) as e:
            logger.debug(f"Error calculating EAR: {e}")
            return None
    
    def calculate_ear(
        self, 
        landmarks: List[Tuple[int, int]],
        left_eye_indices: Optional[List[int]] = None,
        right_eye_indices: Optional[List[int]] = None
    ) -> EARResult:
        """
        Calculate EAR for both eyes.
        
        Args:
            landmarks: List of (x, y) facial landmark coordinates
            left_eye_indices: Optional custom left eye indices
            right_eye_indices: Optional custom right eye indices
            
        Returns:
            EARResult with calculated values and validity
        """
        left_indices = left_eye_indices or self.LEFT_EYE_INDICES
        right_indices = right_eye_indices or self.RIGHT_EYE_INDICES
        
        # Calculate individual eyes
        left_ear = self.calculate_single_eye_ear(landmarks, left_indices)
        right_ear = self.calculate_single_eye_ear(landmarks, right_indices)
        
        # Determine validity and calculate average
        is_valid = (left_ear is not None and right_ear is not None)
        
        if is_valid:
            avg_ear = (left_ear + right_ear) / 2.0
            self._consecutive_failures = 0
            
            # Calculate confidence based on eye symmetry
            eye_diff = abs(left_ear - right_ear)
            confidence = max(0.0, 1.0 - (eye_diff / 0.1))  # 0.1 is max expected diff
            
            return EARResult(
                ear=avg_ear,
                left_ear=left_ear,
                right_ear=right_ear,
                is_valid=True,
                confidence=confidence
            )
        else:
            self._consecutive_failures += 1
            
            if self._consecutive_failures >= self._max_failures:
                logger.warning(
                    f"EAR calculation failed {self._consecutive_failures} consecutive times"
                )
            
            # Return invalid result with fallback values
            return EARResult(
                ear=0.0,
                left_ear=left_ear or 0.0,
                right_ear=right_ear or 0.0,
                is_valid=False,
                confidence=0.0
            )
    
    def validate_landmarks(self, landmarks: List[Tuple[int, int]]) -> bool:
        """
        Validate that landmarks list is properly formatted.
        
        Args:
            landmarks: List of landmark coordinates
            
        Returns:
            True if valid, False otherwise
        """
        try:
            # MediaPipe Face Mesh has 478 landmarks
            if len(landmarks) < 478:
                logger.warning(f"Insufficient landmarks: {len(landmarks)}")
                return False
            
            # Check that all required indices exist and have valid coordinates
            required_indices = set(self.LEFT_EYE_INDICES + self.RIGHT_EYE_INDICES)
            for idx in required_indices:
                if idx >= len(landmarks):
                    return False
                x, y = landmarks[idx]
                if not (isinstance(x, (int, float)) and isinstance(y, (int, float))):
                    return False
            
            return True
            
        except Exception as e:
            logger.debug(f"Landmark validation error: {e}")
            return False


class EARSmoother:
    """Temporal smoothing for EAR values to reduce noise."""
    
    def __init__(self, window_size: int = 5):
        """
        Initialize smoother.
        
        Args:
            window_size: Number of frames to average
        """
        self.window_size = window_size
        self.buffer: List[float] = []
    
    def add(self, ear: float) -> float:
        """
        Add new EAR value and return smoothed result.
        
        Args:
            ear: New EAR value
            
        Returns:
            Smoothed EAR value
        """
        self.buffer.append(ear)
        
        # Keep only last N values
        if len(self.buffer) > self.window_size:
            self.buffer.pop(0)
        
        return np.mean(self.buffer)
    
    def reset(self) -> None:
        """Clear the buffer."""
        self.buffer.clear()
    
    @property
    def is_ready(self) -> bool:
        """Check if enough samples for reliable smoothing."""
        return len(self.buffer) >= self.window_size // 2


# Backward compatibility functions
def euclidean(p1, p2):
    """Calculate Euclidean distance between two points."""
    return np.linalg.norm(np.array(p1) - np.array(p2))


def calculate_ear(landmarks, eye_indices):
    """
    Calculate Eye Aspect Ratio (EAR) for a given eye.
    
    Args:
        landmarks: List of (x, y) coordinates for facial landmarks.
        eye_indices: List of indices for the specific eye (6 points).
        
    Returns:
        float: The calculated EAR value.
    """
    # Calculate vertical eye distances
    v1 = euclidean(landmarks[eye_indices[1]], landmarks[eye_indices[5]])
    v2 = euclidean(landmarks[eye_indices[2]], landmarks[eye_indices[4]])
    
    # Calculate horizontal eye distance
    h = euclidean(landmarks[eye_indices[0]], landmarks[eye_indices[3]])

    # Prevent division by zero
    if h == 0:
        return 0.0

    ear = (v1 + v2) / (2.0 * h)
    return ear
