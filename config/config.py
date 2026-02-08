import os
from dataclasses import dataclass

# Detection Constants
EAR_THRESHOLD = 0.25
CONSEC_FRAMES = 20

# Model Paths
MODEL_PATH = "models/face_landmarker.task"

# Media Paths
ALARM_FILE = "alarm.mp3"

# Camera Settings
VIDEO_FORMAT = "bgr24"

# Advanced Settings
SMOOTHING_WINDOW = 5
CALIBRATION_FRAMES = 90  # ~3 seconds at 30fps
PERCLOS_WINDOW = 300     # ~10 seconds Rolling Window
PERCLOS_THRESHOLD = 0.3  # 30% Closure Trigger


@dataclass
class DetectionConfig:
    """Configuration for drowsiness detection parameters."""
    ear_threshold: float = EAR_THRESHOLD
    consec_frames: int = CONSEC_FRAMES
    smoothing_window: int = SMOOTHING_WINDOW
    calibration_frames: int = CALIBRATION_FRAMES
    perclos_window: int = PERCLOS_WINDOW
    perclos_threshold: float = PERCLOS_THRESHOLD
    model_path: str = MODEL_PATH
    alarm_file: str = ALARM_FILE
    enable_audio_alerts: bool = True
    alert_cooldown_sec: float = 5.0


@dataclass
class VehicleDynamicsConfig:
    """Configuration for vehicle dynamics analysis."""
    sample_rate_hz: int = 10
    steering_entropy_threshold: float = 0.45
    speed_var_threshold: float = 15.0
    lane_dev_threshold: float = 0.5


@dataclass
class SystemConfig:
    """System-level configuration."""
    detection: DetectionConfig = None
    vehicle: VehicleDynamicsConfig = None
    max_fps: int = 10
    
    def __post_init__(self):
        if self.detection is None:
            self.detection = DetectionConfig()
        if self.vehicle is None:
            self.vehicle = VehicleDynamicsConfig()


# Singleton config instance
_config = None


def get_config() -> SystemConfig:
    """Get or create global configuration instance."""
    global _config
    if _config is None:
        _config = SystemConfig()
    return _config

