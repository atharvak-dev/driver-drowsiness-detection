import os

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
