"""
Vehicle Dynamics Analyzer for Impairment Detection
Production-grade implementation with robust error handling and validation.
"""
import numpy as np
from scipy.stats import entropy
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


@dataclass
class VehicleMetrics:
    """Container for calculated vehicle dynamics metrics."""
    steering_entropy: float = 0.0
    lane_deviation: float = 0.0
    speed_variability: float = 0.0
    risk_score: float = 0.0
    risk_level: str = "NORMAL"
    timestamp: datetime = field(default_factory=datetime.now)
    sample_count: int = 0
    is_valid: bool = True
    warnings: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging/serialization."""
        return {
            "steering_entropy": self.steering_entropy,
            "lane_deviation": self.lane_deviation,
            "speed_variability": self.speed_variability,
            "risk_score": self.risk_score,
            "risk_level": self.risk_level,
            "timestamp": self.timestamp.isoformat(),
            "sample_count": self.sample_count,
            "is_valid": self.is_valid,
            "warnings": self.warnings
        }


class VehicleDynamicsAnalyzer:
    """
    Analyzer for vehicle dynamics to detect impairment patterns.
    
    Implements:
    - Steering Entropy (Boer's method)
    - Standard Deviation of Lateral Position (SDLP)
    - Speed Variability (Coefficient of Variation)
    - Multi-metric risk assessment
    """
    
    def __init__(
        self,
        sample_rate_hz: int = 10,
        steering_entropy_threshold: float = 0.45,
        speed_var_threshold: float = 15.0,
        lane_dev_threshold: float = 0.5,
        min_samples: int = 30
    ):
        """
        Initialize analyzer.
        
        Args:
            sample_rate_hz: Sampling rate for input data
            steering_entropy_threshold: Threshold for high entropy (impairment)
            speed_var_threshold: Speed variation threshold (%)
            lane_dev_threshold: Lane deviation threshold (meters)
            min_samples: Minimum samples required for valid analysis
        """
        self.sample_rate = sample_rate_hz
        self.steering_entropy_threshold = steering_entropy_threshold
        self.speed_var_threshold = speed_var_threshold
        self.lane_dev_threshold = lane_dev_threshold
        self.min_samples = min_samples
        
        # State tracking
        self._last_metrics: Optional[VehicleMetrics] = None
        self._analysis_count = 0
        
    def validate_input(
        self, 
        data: np.ndarray, 
        name: str,
        min_value: Optional[float] = None,
        max_value: Optional[float] = None
    ) -> bool:
        """
        Validate input data array.
        
        Args:
            data: Input data array
            name: Name of the data (for logging)
            min_value: Optional minimum allowed value
            max_value: Optional maximum allowed value
            
        Returns:
            True if valid, False otherwise
        """
        try:
            if not isinstance(data, np.ndarray):
                data = np.array(data)
            
            if len(data) == 0:
                logger.warning(f"{name}: Empty data array")
                return False
            
            if len(data) < self.min_samples:
                logger.debug(
                    f"{name}: Insufficient samples ({len(data)} < {self.min_samples})"
                )
                return False
            
            if np.any(np.isnan(data)) or np.any(np.isinf(data)):
                logger.warning(f"{name}: Contains NaN or Inf values")
                return False
            
            if min_value is not None and np.any(data < min_value):
                logger.warning(f"{name}: Values below minimum ({min_value})")
                return False
                
            if max_value is not None and np.any(data > max_value):
                logger.warning(f"{name}: Values above maximum ({max_value})")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Validation error for {name}: {e}")
            return False
    
    def calculate_steering_entropy(
        self, 
        steering_angles: np.ndarray,
        return_components: bool = False,
        window_size_sec: float = 30.0
    ) -> float:
        """
        Calculate Steering Entropy using Boer's method approximation.
        
        High entropy indicates erratic, unpredictable steering (impairment).
        Low entropy indicates smooth, consistent control.
        
        Args:
            steering_angles: Array of steering angles in degrees
            return_components: If True, return (entropy, prediction_errors)
            window_size_sec: Window size for analysis (unused, kept for compatibility)
            
        Returns:
            Steering entropy value (bits)
        """
        try:
            if not self.validate_input(
                steering_angles, 
                "steering_angles",
                min_value=-540,  # ~1.5 full rotations
                max_value=540
            ):
                return 0.0
            
            # Convert to numpy array if needed
            angles = np.asarray(steering_angles, dtype=np.float64)
            
            # Remove outliers using IQR method
            q1, q3 = np.percentile(angles, [25, 75])
            iqr = q3 - q1
            lower_bound = q1 - 1.5 * iqr
            upper_bound = q3 + 1.5 * iqr
            angles = angles[(angles >= lower_bound) & (angles <= upper_bound)]
            
            if len(angles) < self.min_samples:
                logger.debug("Insufficient samples after outlier removal")
                return 0.0
            
            # Calculate prediction errors using 2nd-order predictor
            if len(angles) < 3:
                return 0.0
            
            # Calculate first derivative (steering rate)
            d1 = np.diff(angles)
            
            # Predict next angle
            predictions = angles[1:-1] + d1[:-1]
            actuals = angles[2:]
            errors = actuals - predictions
            
            if len(errors) == 0:
                return 0.0
            
            # Normalize errors using 90th percentile (Boer's alpha method)
            p90 = np.percentile(np.abs(errors), 90)
            
            if p90 < 1e-6:  # Nearly constant steering
                return 0.0
            
            # Create 9 bins for error distribution
            bins = np.array([
                -np.inf, -5*p90, -2.5*p90, -p90, -0.5*p90,
                0.5*p90, p90, 2.5*p90, 5*p90, np.inf
            ])
            
            # Calculate histogram
            counts, _ = np.histogram(errors, bins=bins)
            
            # Avoid log(0) by adding small epsilon
            counts = counts + 1e-10
            probs = counts / np.sum(counts)
            
            # Calculate Shannon Entropy
            h = entropy(probs, base=2)
            
            if return_components:
                return h, errors
            
            return float(h)
            
        except Exception as e:
            logger.error(f"Error calculating steering entropy: {e}", exc_info=True)
            return 0.0
    
    def calculate_lane_deviation(self, lane_position: np.ndarray) -> float:
        """
        Calculate Standard Deviation of Lateral Lane Position (SDLP).
        
        High SDLP indicates weaving or inability to maintain lane center.
        
        Args:
            lane_position: Array of lateral positions relative to lane center (meters)
            
        Returns:
            SDLP value (meters)
        """
        try:
            if not self.validate_input(
                lane_position,
                "lane_position",
                min_value=-5.0,  # Realistic lane bounds
                max_value=5.0
            ):
                return 0.0
            
            position = np.asarray(lane_position, dtype=np.float64)
            
            # Remove bias (systematic offset) before calculating deviation
            centered = position - np.mean(position)
            
            sdlp = float(np.std(centered))
            
            return sdlp
            
        except Exception as e:
            logger.error(f"Error calculating lane deviation: {e}")
            return 0.0
    
    def calculate_speed_variability(self, speed_kmh: np.ndarray) -> float:
        """
        Calculate Coefficient of Variation (CV) of speed.
        
        CV = (std_dev / mean) * 100
        
        Args:
            speed_kmh: Array of speed values in km/h
            
        Returns:
            Speed variability as percentage
        """
        try:
            if not self.validate_input(
                speed_kmh,
                "speed_kmh",
                min_value=0.0,
                max_value=300.0  # Realistic max
            ):
                return 0.0
            
            speed = np.asarray(speed_kmh, dtype=np.float64)
            
            mean_speed = np.mean(speed)
            
            # Skip if vehicle is stopped or very slow
            if mean_speed < 5.0:
                logger.debug("Speed too low for variability calculation")
                return 0.0
            
            std_speed = np.std(speed)
            cv = (std_speed / mean_speed) * 100.0
            
            return float(cv)
            
        except Exception as e:
            logger.error(f"Error calculating speed variability: {e}")
            return 0.0
    
    def calculate_risk_score(
        self,
        steering_entropy: float,
        speed_var: float,
        lane_dev: float
    ) -> float:
        """
        Calculate composite risk score (0-1 scale).
        
        Uses weighted combination of normalized metrics.
        
        Args:
            steering_entropy: Steering entropy value
            speed_var: Speed variability percentage
            lane_dev: Lane deviation (SDLP)
            
        Returns:
            Risk score between 0 (normal) and 1 (high risk)
        """
        # Normalize each metric to 0-1 scale
        entropy_norm = min(1.0, steering_entropy / 1.0)  # Max entropy ~1.0
        speed_norm = min(1.0, speed_var / 30.0)  # Max CV ~30%
        lane_norm = min(1.0, lane_dev / 1.0)  # Max SDLP ~1m
        
        # Weighted combination (steering is most indicative)
        weights = {
            'entropy': 0.5,
            'speed': 0.25,
            'lane': 0.25
        }
        
        risk_score = (
            weights['entropy'] * entropy_norm +
            weights['speed'] * speed_norm +
            weights['lane'] * lane_norm
        )
        
        return float(np.clip(risk_score, 0.0, 1.0))
    
    def classify_risk_level(
        self,
        risk_score: float,
        steering_entropy: float,
        speed_var: float,
        lane_dev: float
    ) -> str:
        """
        Classify risk level based on metrics.
        
        Args:
            risk_score: Composite risk score
            steering_entropy: Steering entropy value
            speed_var: Speed variability
            lane_dev: Lane deviation
            
        Returns:
            Risk level: NORMAL, POSSIBLE_IMPAIRMENT, HIGH_RISK, CRITICAL
        """
        # Critical: Multiple severe indicators
        if (steering_entropy > self.steering_entropy_threshold * 1.5 and
            (speed_var > self.speed_var_threshold or 
             lane_dev > self.lane_dev_threshold)):
            return "CRITICAL"
        
        # High risk: Entropy threshold exceeded
        if steering_entropy > self.steering_entropy_threshold:
            if speed_var > self.speed_var_threshold or lane_dev > self.lane_dev_threshold:
                return "HIGH_RISK"
            return "POSSIBLE_IMPAIRMENT"
        
        # Medium risk: Composite score elevated
        if risk_score > 0.6:
            return "POSSIBLE_IMPAIRMENT"
        
        return "NORMAL"
    
    def detect_high_risk_event(
        self, 
        steering_entropy: float, 
        speed_var: float, 
        lane_dev: float = 0.0
    ) -> str:
        """
        Classify risk based on thresholds (backward compatibility method).
        
        Returns:
            Risk level string
        """
        risk_score = self.calculate_risk_score(steering_entropy, speed_var, lane_dev)
        return self.classify_risk_level(risk_score, steering_entropy, speed_var, lane_dev)
    
    def analyze(
        self,
        steering_angles: Optional[np.ndarray] = None,
        lane_position: Optional[np.ndarray] = None,
        speed_kmh: Optional[np.ndarray] = None
    ) -> VehicleMetrics:
        """
        Perform comprehensive vehicle dynamics analysis.
        
        Args:
            steering_angles: Array of steering angles (degrees)
            lane_position: Array of lateral positions (meters)
            speed_kmh: Array of speeds (km/h)
            
        Returns:
            VehicleMetrics with analysis results
        """
        metrics = VehicleMetrics(timestamp=datetime.now())
        warnings = []
        
        try:
            # Calculate individual metrics
            if steering_angles is not None:
                metrics.steering_entropy = self.calculate_steering_entropy(steering_angles)
                metrics.sample_count = len(steering_angles)
            else:
                warnings.append("No steering data provided")
            
            if lane_position is not None:
                metrics.lane_deviation = self.calculate_lane_deviation(lane_position)
            else:
                warnings.append("No lane position data provided")
            
            if speed_kmh is not None:
                metrics.speed_variability = self.calculate_speed_variability(speed_kmh)
            else:
                warnings.append("No speed data provided")
            
            # Calculate composite metrics
            metrics.risk_score = self.calculate_risk_score(
                metrics.steering_entropy,
                metrics.speed_variability,
                metrics.lane_deviation
            )
            
            metrics.risk_level = self.classify_risk_level(
                metrics.risk_score,
                metrics.steering_entropy,
                metrics.speed_variability,
                metrics.lane_deviation
            )
            
            metrics.warnings = warnings
            metrics.is_valid = len(warnings) < 3  # At least one metric available
            
            self._last_metrics = metrics
            self._analysis_count += 1
            
            if self._analysis_count % 100 == 0:
                logger.info(f"Completed {self._analysis_count} vehicle dynamics analyses")
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error in vehicle dynamics analysis: {e}", exc_info=True)
            metrics.is_valid = False
            metrics.warnings.append(f"Analysis failed: {str(e)}")
            return metrics
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get analyzer statistics."""
        return {
            "total_analyses": self._analysis_count,
            "last_metrics": self._last_metrics.to_dict() if self._last_metrics else None,
            "thresholds": {
                "steering_entropy": self.steering_entropy_threshold,
                "speed_variability": self.speed_var_threshold,
                "lane_deviation": self.lane_dev_threshold
            }
        }
    
    def reset(self) -> None:
        """Reset analyzer state."""
        self._last_metrics = None
        self._analysis_count = 0
        logger.info("Vehicle dynamics analyzer reset")
