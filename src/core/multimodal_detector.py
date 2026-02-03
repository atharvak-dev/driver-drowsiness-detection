"""
Enhanced Multi-Modal Driver State Detection
Implements features from the research report for comprehensive driver monitoring
"""

import cv2
import numpy as np
import time
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum

class DriverState(Enum):
    CALIBRATING = "Calibrating..."
    SOBER_ALERT = "Sober & Alert"
    DROWSY = "Sleepy/Drowsy"
    ASLEEP = "Asleep"
    INTOXICATED = "Drunk"

@dataclass
class DriverMetrics:
    ear: float
    mar: float  # Mouth Aspect Ratio for yawning
    head_pose: Tuple[float, float, float]  # pitch, yaw, roll
    blink_rate: float
    perclos: float  # Percentage of eye closure
    gaze_deviation: float
    timestamp: float

class EnhancedDriverDetector:
    def __init__(self):
        # Adaptive Thresholds
        self.ear_threshold = 0.25  # Default, will be updated by calibration
        self.mar_threshold = 0.6
        self.perclos_threshold = 0.8
        
        # Calibration State
        self.is_calibrating = True
        self.calibration_buffer = []
        self.calibration_frames = 0
        self.CALIBRATION_DURATION = 90  # Frames (3 seconds @ 30fps)
        
        # History
        self.blink_history = []
        self.drowsy_frames = 0
        self.alert_frames = 0
        self.last_blink_time = 0
        
        # MediaPipe Indices (Subject's Perspective)
        # Left Eye (Subject's Left, Screen Right)
        self.LEFT_EYE = [362, 385, 387, 263, 373, 380]
        # Right Eye (Subject's Right, Screen Left)
        self.RIGHT_EYE = [33, 160, 158, 133, 153, 144]
        
    def calculate_ear(self, landmarks: List[Tuple[int, int]], indices: List[int]) -> float:
        """Calculate Eye Aspect Ratio using specific indices"""
        try:
            # Vertical distances
            v1 = np.linalg.norm(np.array(landmarks[indices[1]]) - np.array(landmarks[indices[5]]))
            v2 = np.linalg.norm(np.array(landmarks[indices[2]]) - np.array(landmarks[indices[4]]))
            
            # Horizontal distance
            h = np.linalg.norm(np.array(landmarks[indices[0]]) - np.array(landmarks[indices[3]]))
            
            if h == 0:
                return 0.0
                
            return (v1 + v2) / (2.0 * h)
        except (IndexError, TypeError):
            return 0.0

    def calculate_mar(self, landmarks: List[Tuple[int, int]]) -> float:
        """Calculate Mouth Aspect Ratio"""
        try:
            # Vertical distance (Inner lip height: 13-14)
            v = np.linalg.norm(np.array(landmarks[13]) - np.array(landmarks[14]))
            
            # Horizontal distance (Mouth corners: 61-291)
            h = np.linalg.norm(np.array(landmarks[61]) - np.array(landmarks[291]))
            
            if h == 0:
                return 0.0
                
            return v / h
        except (IndexError, TypeError):
            return 0.0
    
    def estimate_head_pose(self, landmarks: List[Tuple[int, int]], 
                          img_shape: Tuple[int, int]) -> Tuple[float, float, float]:
        """Estimate head pose (pitch, yaw, roll) using robust PnP"""
        if not landmarks:
            return (0.0, 0.0, 0.0)
            
        # 3D model points (Generic Human Face)
        model_points = np.array([
            (0.0, 0.0, 0.0),             # Nose tip
            (0.0, -330.0, -65.0),        # Chin
            (-225.0, 170.0, -135.0),     # Left eye left corner
            (225.0, 170.0, -135.0),      # Right eye right corner
            (-150.0, -150.0, -125.0),    # Left Mouth corner
            (150.0, -150.0, -125.0)      # Right mouth corner
        ])
        
        # 2D Image Points from MediaPipe
        # Nose: 1, Chin: 152, LeftEyeCorner: 33, RightEyeCorner: 263, LeftMouth: 61, RightMouth: 291
        # NOTE: 33 is Subject Right/Screen Left. 263 is Subject Left/Screen Right.
        # We must align 3D points with 2D points.
        # 3D Point 2 (Left Eye Left Corner) -> User's Left Eye Outer Corner (263)
        # 3D Point 3 (Right Eye Right Corner) -> User's Right Eye Outer Corner (33)
        try:
            image_points = np.array([
                landmarks[1],    # Nose tip
                landmarks[152],  # Chin
                landmarks[263],  # Left eye outer corner (Subject Left)
                landmarks[33],   # Right eye outer corner (Subject Right)
                landmarks[61],   # Left mouth corner
                landmarks[291]   # Right mouth corner
            ], dtype="double")
            
            # Camera internals
            focal_length = img_shape[1]
            center = (img_shape[1]/2, img_shape[0]/2)
            camera_matrix = np.array([
                [focal_length, 0, center[0]],
                [0, focal_length, center[1]],
                [0, 0, 1]
            ], dtype="double")
            
            dist_coeffs = np.zeros((4,1))
            
            success, rotation_vector, translation_vector = cv2.solvePnP(
                model_points, image_points, camera_matrix, dist_coeffs)
            
            if success:
                rotation_matrix, _ = cv2.Rodrigues(rotation_vector)
                angles, _, _, _, _, _ = cv2.RQDecomp3x3(rotation_matrix)
                
                # Convert to degrees
                pitch = angles[0] * 360
                yaw = angles[1] * 360
                roll = angles[2] * 360
                return (pitch, yaw, roll)
        except Exception:
            pass
            
        return (0.0, 0.0, 0.0)
    
    def calculate_perclos(self, ear_history: List[float], window_size: int = 30) -> float:
        """Calculate PERCLOS"""
        if len(ear_history) < window_size:
            return 0.0
            
        recent_ears = ear_history[-window_size:]
        closed_count = sum(1 for ear in recent_ears if ear < self.ear_threshold)
        return closed_count / len(recent_ears)
    
    def update_blink_rate(self, ear: float, current_time: float):
        """Update blink rate calculation"""
        if self.is_calibrating:
            return

        # Detect blink start
        if ear < self.ear_threshold and len(self.blink_history) > 0:
            if self.blink_history[-1] >= self.ear_threshold:
                if self.last_blink_time > 0:
                    blink_interval = current_time - self.last_blink_time
                    if blink_interval > 0.1:
                        self.last_blink_time = current_time
                else:
                    self.last_blink_time = current_time
        
        self.blink_history.append(ear)
        if len(self.blink_history) > 1800:
            self.blink_history.pop(0)
    
    def classify_driver_state(self, metrics: DriverMetrics) -> DriverState:
        """Classify driver state"""
        if self.is_calibrating:
            return DriverState.CALIBRATING

        current_time = time.time()
        
        # Counts
        if metrics.ear < self.ear_threshold:
            self.drowsy_frames += 1
            self.alert_frames = 0
        else:
            self.alert_frames += 1
            if self.alert_frames > 10:
                self.drowsy_frames = 0
        
        # Drowsy/Asleep Logic
        if self.drowsy_frames > 90:
            if metrics.perclos > 0.9:
                return DriverState.ASLEEP
            else:
                return DriverState.DROWSY
        
        # Intoxication Logic
        intoxication_score = 0
        
        # 1. Excessive Head Movement (Nodding/Bobbing)
        if abs(metrics.head_pose[0]) > 25 or abs(metrics.head_pose[2]) > 25: # Pitch or Roll
             intoxication_score += 1
             
        # 2. Staring (Low Blink Rate) - ONLY after 10s
        # Estimate blink rate from history
        start_time = max(0, len(self.blink_history) - 900)
        recent_history = self.blink_history[start_time:]
        # Count closures generally
        closures = len([e for e in recent_history if e < self.ear_threshold])
        
        if closures < 5 and len(self.blink_history) > 300:
            intoxication_score += 1
            
        if intoxication_score >= 2:
            return DriverState.INTOXICATED
            
        return DriverState.SOBER_ALERT
    
    def process_frame(self, landmarks: List[Tuple[int, int]], 
                     img_shape: Tuple[int, int]) -> Tuple[DriverState, DriverMetrics]:
        """Process frame with auto-calibration"""
        current_time = time.time()
        
        if not landmarks:
            return DriverState.SOBER_ALERT, DriverMetrics(0,0,(0,0,0),0,0,0,current_time)
            
        # Calculate Base Metrics
        left_ear = self.calculate_ear(landmarks, self.LEFT_EYE)
        right_ear = self.calculate_ear(landmarks, self.RIGHT_EYE)
        ear = (left_ear + right_ear) / 2.0
        mar = self.calculate_mar(landmarks)
        head_pose = self.estimate_head_pose(landmarks, img_shape)
        
        # --- CALIBRATION LOGIC ---
        if self.is_calibrating:
            self.calibration_buffer.append(ear)
            self.calibration_frames += 1
            
            if self.calibration_frames >= self.CALIBRATION_DURATION:
                # Finish calibration
                baseline_ear = np.mean(self.calibration_buffer)
                self.ear_threshold = baseline_ear * 0.7  # Threshold is 70% of open-eye EAR
                self.is_calibrating = False
                # Clear buffer
                self.calibration_buffer = []
            
            # Return CALIBRATING state
            return DriverState.CALIBRATING, DriverMetrics(ear, mar, head_pose, 0, 0, 0, current_time)
            
        # --- NORMAL OPERATION ---
        self.update_blink_rate(ear, current_time)
        
        ear_history = [ear] * 30 
        perclos = self.calculate_perclos(ear_history)
        
        # Blink Rate (Approx)
        closures = len([e for e in self.blink_history if e < self.ear_threshold])
        
        metrics = DriverMetrics(
            ear=ear,
            mar=mar,
            head_pose=head_pose,
            blink_rate=closures, 
            perclos=perclos,
            gaze_deviation=0,
            timestamp=current_time
        )
        
        state = self.classify_driver_state(metrics)
        
        return state, metrics