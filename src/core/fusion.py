"""
Multi-Modal Impairment Detection System
Fuses visual drowsiness detection with vehicle dynamics analysis.
"""
import numpy as np
import logging
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from src.core.vehicle_dynamics import VehicleDynamicsAnalyzer, VehicleMetrics

logger = logging.getLogger(__name__)


class AlertLevel(Enum):
    """Alert severity levels."""
    NONE = 0
    WARNING = 1
    DANGER = 2
    CRITICAL = 3


class ImpairmentType(Enum):
    """Types of detected impairment."""
    NONE = "none"
    DROWSINESS = "drowsiness"
    INTOXICATION = "intoxication"
    FATIGUE = "fatigue"
    DISTRACTION = "distraction"
    COMBINED = "combined"


@dataclass
class DetectionEvent:
    """Container for a detection event."""
    timestamp: datetime
    alert_level: AlertLevel
    ear_value: float
    perclos: float
    frame_count: int
    reason: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "alert_level": self.alert_level.name,
            "ear_value": self.ear_value,
            "perclos": self.perclos,
            "frame_count": self.frame_count,
            "reason": self.reason,
            "metadata": self.metadata
        }


@dataclass
class FusedDetection:
    """Result of multi-modal fusion."""
    timestamp: datetime
    impairment_type: ImpairmentType
    confidence: float  # 0-1
    alert_level: AlertLevel
    visual_score: float  # 0-1
    vehicle_score: float  # 0-1
    combined_score: float  # 0-1
    
    # Component results
    visual_event: Optional[DetectionEvent] = None
    vehicle_metrics: Optional[VehicleMetrics] = None
    
    # Reasoning
    primary_indicators: List[str] = field(default_factory=list)
    secondary_indicators: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "impairment_type": self.impairment_type.value,
            "confidence": self.confidence,
            "alert_level": self.alert_level.name,
            "visual_score": self.visual_score,
            "vehicle_score": self.vehicle_score,
            "combined_score": self.combined_score,
            "primary_indicators": self.primary_indicators,
            "secondary_indicators": self.secondary_indicators,
            "visual_event": self.visual_event.to_dict() if self.visual_event else None,
            "vehicle_metrics": self.vehicle_metrics.to_dict() if self.vehicle_metrics else None
        }


class MultiModalDetector:
    """
    Fuses visual drowsiness detection with vehicle dynamics analysis.
    
    Combines:
    - Eye Aspect Ratio (EAR) and PERCLOS from camera
    - Steering entropy, lane deviation, speed variability from vehicle sensors
    
    Enables detection of:
    - Drowsiness (micro-sleep, fatigue)
    - Intoxication (erratic control)
    - General impairment
    """
    
    # Default thresholds
    DEFAULT_STEERING_ENTROPY_THRESHOLD = 0.45
    DEFAULT_SPEED_VAR_THRESHOLD = 15.0
    DEFAULT_LANE_DEV_THRESHOLD = 0.5
    DEFAULT_CONSEC_FRAMES = 20
    
    def __init__(
        self,
        enable_visual: bool = True,
        enable_vehicle: bool = True,
        fusion_strategy: str = "weighted"
    ):
        """
        Initialize multi-modal detector.
        
        Args:
            enable_visual: Enable visual (camera) detection
            enable_vehicle: Enable vehicle dynamics detection
            fusion_strategy: Fusion strategy ("weighted", "max", "bayesian")
        """
        self.enable_visual = enable_visual
        self.enable_vehicle = enable_vehicle
        self.fusion_strategy = fusion_strategy
        
        # Visual detector is managed externally (for streamlit-webrtc compatibility)
        self.visual_detector = None
        
        # Initialize vehicle analyzer
        self.vehicle_analyzer = VehicleDynamicsAnalyzer(
            sample_rate_hz=10,
            steering_entropy_threshold=self.DEFAULT_STEERING_ENTROPY_THRESHOLD,
            speed_var_threshold=self.DEFAULT_SPEED_VAR_THRESHOLD,
            lane_dev_threshold=self.DEFAULT_LANE_DEV_THRESHOLD
        ) if enable_vehicle else None
        
        # Fusion weights (can be learned/tuned)
        self.weights = {
            "visual": 0.6,  # Visual is more direct for drowsiness
            "vehicle": 0.4  # Vehicle adds context
        }
        
        # State
        self._last_fusion: Optional[FusedDetection] = None
        self._fusion_count = 0
        
        logger.info(
            f"Multi-modal detector initialized - "
            f"Visual: {enable_visual}, Vehicle: {enable_vehicle}, "
            f"Strategy: {fusion_strategy}"
        )
    
    def process_vehicle_data(
        self,
        steering_angles: Optional[np.ndarray] = None,
        lane_position: Optional[np.ndarray] = None,
        speed_kmh: Optional[np.ndarray] = None
    ) -> Optional[VehicleMetrics]:
        """
        Process vehicle sensor data.
        
        Args:
            steering_angles: Array of steering angles
            lane_position: Array of lateral positions
            speed_kmh: Array of speeds
            
        Returns:
            Vehicle metrics
        """
        if not self.enable_vehicle or self.vehicle_analyzer is None:
            return None
        
        metrics = self.vehicle_analyzer.analyze(
            steering_angles=steering_angles,
            lane_position=lane_position,
            speed_kmh=speed_kmh
        )
        
        return metrics if metrics.is_valid else None
    
    def fuse_detections(
        self,
        visual_event: Optional[DetectionEvent] = None,
        vehicle_metrics: Optional[VehicleMetrics] = None
    ) -> Optional[FusedDetection]:
        """
        Fuse visual and vehicle detections.
        
        Args:
            visual_event: Visual detection event
            vehicle_metrics: Vehicle dynamics metrics
            
        Returns:
            Fused detection result
        """
        if visual_event is None and vehicle_metrics is None:
            return None
        
        # Calculate individual scores
        visual_score = self._calculate_visual_score(visual_event)
        vehicle_score = self._calculate_vehicle_score(vehicle_metrics)
        
        # Fuse scores
        if self.fusion_strategy == "weighted":
            combined_score = self._weighted_fusion(visual_score, vehicle_score)
        elif self.fusion_strategy == "max":
            combined_score = max(visual_score, vehicle_score)
        elif self.fusion_strategy == "bayesian":
            combined_score = self._bayesian_fusion(visual_score, vehicle_score)
        else:
            combined_score = (visual_score + vehicle_score) / 2
        
        # Determine impairment type
        impairment_type, confidence = self._classify_impairment(
            visual_event, vehicle_metrics, combined_score
        )
        
        # Determine alert level
        alert_level = self._determine_alert_level(
            combined_score, visual_event, vehicle_metrics
        )
        
        # Collect indicators
        primary, secondary = self._collect_indicators(
            visual_event, vehicle_metrics
        )
        
        fusion = FusedDetection(
            timestamp=datetime.now(),
            impairment_type=impairment_type,
            confidence=confidence,
            alert_level=alert_level,
            visual_score=visual_score,
            vehicle_score=vehicle_score,
            combined_score=combined_score,
            visual_event=visual_event,
            vehicle_metrics=vehicle_metrics,
            primary_indicators=primary,
            secondary_indicators=secondary
        )
        
        self._last_fusion = fusion
        self._fusion_count += 1
        
        if fusion.alert_level != AlertLevel.NONE:
            logger.warning(
                f"Impairment detected - Type: {impairment_type.value}, "
                f"Confidence: {confidence:.2f}, Alert: {alert_level.name}"
            )
        
        return fusion
    
    def _calculate_visual_score(self, event: Optional[DetectionEvent]) -> float:
        """Calculate normalized score from visual detection (0-1)."""
        if event is None:
            return 0.0
        
        # Map alert level to score
        alert_scores = {
            AlertLevel.NONE: 0.0,
            AlertLevel.WARNING: 0.4,
            AlertLevel.DANGER: 0.7,
            AlertLevel.CRITICAL: 1.0
        }
        
        base_score = alert_scores.get(event.alert_level, 0.0)
        
        # Adjust based on PERCLOS
        perclos_factor = min(1.0, event.perclos / 0.3)  # 30% PERCLOS = max
        
        # Combine
        score = base_score * 0.7 + perclos_factor * 0.3
        
        return float(np.clip(score, 0.0, 1.0))
    
    def _calculate_vehicle_score(self, metrics: Optional[VehicleMetrics]) -> float:
        """Calculate normalized score from vehicle metrics (0-1)."""
        if metrics is None or not metrics.is_valid:
            return 0.0
        
        # Use the pre-calculated risk score
        return float(np.clip(metrics.risk_score, 0.0, 1.0))
    
    def _weighted_fusion(self, visual_score: float, vehicle_score: float) -> float:
        """Weighted average fusion."""
        # Adjust weights if one modality is missing
        if visual_score == 0.0 and vehicle_score > 0.0:
            return vehicle_score
        if vehicle_score == 0.0 and visual_score > 0.0:
            return visual_score
        
        combined = (
            self.weights["visual"] * visual_score +
            self.weights["vehicle"] * vehicle_score
        )
        
        return float(np.clip(combined, 0.0, 1.0))
    
    def _bayesian_fusion(self, visual_score: float, vehicle_score: float) -> float:
        """
        Bayesian fusion treating scores as probabilities.
        P(impaired | both) ∝ P(both | impaired) / P(both | normal)
        """
        # Prior probability of impairment (can be learned)
        prior = 0.05
        
        # Likelihood ratios (simplified)
        if visual_score > 0 and vehicle_score > 0:
            # Both positive - strong evidence
            likelihood_ratio = 10.0
        elif visual_score > 0 or vehicle_score > 0:
            # One positive - moderate evidence
            likelihood_ratio = 3.0
        else:
            # Both zero - no evidence
            return 0.0
        
        # Posterior probability
        posterior = (prior * likelihood_ratio) / (
            prior * likelihood_ratio + (1 - prior)
        )
        
        # Scale by max individual score
        scaled = posterior * max(visual_score, vehicle_score)
        
        return float(np.clip(scaled, 0.0, 1.0))
    
    def _classify_impairment(
        self,
        visual_event: Optional[DetectionEvent],
        vehicle_metrics: Optional[VehicleMetrics],
        combined_score: float
    ) -> tuple:
        """
        Classify type of impairment.
        
        Returns:
            (impairment_type, confidence)
        """
        if combined_score < 0.3:
            return ImpairmentType.NONE, 0.0
        
        # Check patterns
        has_visual = visual_event is not None
        has_vehicle = vehicle_metrics is not None and vehicle_metrics.is_valid
        
        if not has_visual and not has_vehicle:
            return ImpairmentType.NONE, 0.0
        
        # Drowsiness: Strong visual signal (PERCLOS, micro-sleep)
        if has_visual and visual_event.perclos > 0.15:
            if has_vehicle and vehicle_metrics.risk_level != "NORMAL":
                return ImpairmentType.COMBINED, combined_score
            return ImpairmentType.DROWSINESS, combined_score * 0.9
        
        # Intoxication: Strong vehicle signal without visual
        if has_vehicle and vehicle_metrics.steering_entropy > 0.5:
            if not has_visual or visual_event.alert_level == AlertLevel.NONE:
                return ImpairmentType.INTOXICATION, combined_score * 0.7
        
        # Fatigue: Moderate signals from both
        if has_visual and has_vehicle:
            if (visual_event.perclos > 0.10 and 
                vehicle_metrics.risk_score > 0.4):
                return ImpairmentType.FATIGUE, combined_score * 0.8
        
        # General impairment
        if combined_score > 0.5:
            return ImpairmentType.COMBINED, combined_score * 0.6
        
        return ImpairmentType.NONE, 0.0
    
    def _determine_alert_level(
        self,
        combined_score: float,
        visual_event: Optional[DetectionEvent],
        vehicle_metrics: Optional[VehicleMetrics]
    ) -> AlertLevel:
        """Determine alert level from fused score."""
        # Critical: High combined score OR both modalities critical
        if combined_score >= 0.8:
            return AlertLevel.CRITICAL
        
        if (visual_event and visual_event.alert_level == AlertLevel.CRITICAL and
            vehicle_metrics and vehicle_metrics.risk_level == "CRITICAL"):
            return AlertLevel.CRITICAL
        
        # Danger: Medium-high score
        if combined_score >= 0.6:
            return AlertLevel.DANGER
        
        # Warning: Low-medium score
        if combined_score >= 0.4:
            return AlertLevel.WARNING
        
        return AlertLevel.NONE
    
    def _collect_indicators(
        self,
        visual_event: Optional[DetectionEvent],
        vehicle_metrics: Optional[VehicleMetrics]
    ) -> tuple:
        """Collect primary and secondary indicators."""
        primary = []
        secondary = []
        
        # Visual indicators
        if visual_event:
            if visual_event.perclos > 0.2:
                primary.append(f"High PERCLOS ({visual_event.perclos:.1%})")
            elif visual_event.perclos > 0.1:
                secondary.append(f"Elevated PERCLOS ({visual_event.perclos:.1%})")
            
            if visual_event.frame_count >= self.DEFAULT_CONSEC_FRAMES:
                primary.append(f"Micro-sleep ({visual_event.frame_count} frames)")
            elif visual_event.frame_count > 0:
                secondary.append(f"Eyes closing ({visual_event.frame_count} frames)")
        
        # Vehicle indicators
        if vehicle_metrics and vehicle_metrics.is_valid:
            if vehicle_metrics.steering_entropy > self.DEFAULT_STEERING_ENTROPY_THRESHOLD:
                primary.append(
                    f"High steering entropy ({vehicle_metrics.steering_entropy:.2f})"
                )
            elif vehicle_metrics.steering_entropy > self.DEFAULT_STEERING_ENTROPY_THRESHOLD * 0.8:
                secondary.append(
                    f"Elevated steering entropy ({vehicle_metrics.steering_entropy:.2f})"
                )
            
            if vehicle_metrics.lane_deviation > self.DEFAULT_LANE_DEV_THRESHOLD:
                primary.append(f"Lane weaving ({vehicle_metrics.lane_deviation:.2f}m)")
            
            if vehicle_metrics.speed_variability > self.DEFAULT_SPEED_VAR_THRESHOLD:
                secondary.append(
                    f"Speed instability ({vehicle_metrics.speed_variability:.1f}%)"
                )
        
        return primary, secondary
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get detector statistics."""
        stats = {
            "fusion_count": self._fusion_count,
            "fusion_strategy": self.fusion_strategy,
            "weights": self.weights,
            "last_fusion": self._last_fusion.to_dict() if self._last_fusion else None
        }
        
        if self.vehicle_analyzer:
            stats["vehicle"] = self.vehicle_analyzer.get_statistics()
        
        return stats
    
    def reset(self) -> None:
        """Reset all detectors."""
        if self.vehicle_analyzer:
            self.vehicle_analyzer.reset()
        self._last_fusion = None
        self._fusion_count = 0
        logger.info("Multi-modal detector reset")
