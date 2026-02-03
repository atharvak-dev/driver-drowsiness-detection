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
        self.ear_threshold = 0.25
        self.mar_threshold = 0.6  # Yawning threshold
        self.perclos_threshold = 0.8  # 80% eye closure
        self.blink_history = []
        self.drowsy_frames = 0
        self.alert_frames = 0
        self.last_blink_time = 0
        
    def calculate_mar(self, mouth_landmarks: List[Tuple[int, int]]) -> float:
        """Calculate Mouth Aspect Ratio for yawning detection"""
        if len(mouth_landmarks) < 6:
            return 0.0
            
        # Vertical distances
        v1 = np.linalg.norm(np.array(mouth_landmarks[1]) - np.array(mouth_landmarks[5]))
        v2 = np.linalg.norm(np.array(mouth_landmarks[2]) - np.array(mouth_landmarks[4]))
        
        # Horizontal distance
        h = np.linalg.norm(np.array(mouth_landmarks[0]) - np.array(mouth_landmarks[3]))
        
        if h == 0:
            return 0.0
            
        return (v1 + v2) / (2.0 * h)
    
    def estimate_head_pose(self, landmarks: List[Tuple[int, int]], 
                          img_shape: Tuple[int, int]) -> Tuple[float, float, float]:
        """Estimate head pose (pitch, yaw, roll) from facial landmarks"""
        if len(landmarks) < 68:
            return (0.0, 0.0, 0.0)
            
        # 3D model points for head pose estimation
        model_points = np.array([
            (0.0, 0.0, 0.0),             # Nose tip
            (0.0, -330.0, -65.0),        # Chin
            (-225.0, 170.0, -135.0),     # Left eye left corner
            (225.0, 170.0, -135.0),      # Right eye right corner
            (-150.0, -150.0, -125.0),    # Left mouth corner
            (150.0, -150.0, -125.0)      # Right mouth corner
        ])
        
        # 2D image points from landmarks
        image_points = np.array([
            landmarks[30],    # Nose tip
            landmarks[8],     # Chin
            landmarks[36],    # Left eye left corner
            landmarks[45],    # Right eye right corner
            landmarks[48],    # Left mouth corner
            landmarks[54]     # Right mouth corner
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
        
        try:
            success, rotation_vector, translation_vector = cv2.solvePnP(
                model_points, image_points, camera_matrix, dist_coeffs)
            
            if success:
                rotation_matrix, _ = cv2.Rodrigues(rotation_vector)
                angles = cv2.RQDecomp3x3(rotation_matrix)[0]
                return tuple(angles)
        except:
            pass
            
        return (0.0, 0.0, 0.0)
    
    def calculate_perclos(self, ear_history: List[float], window_size: int = 30) -> float:
        """Calculate PERCLOS - percentage of eye closure over time window"""
        if len(ear_history) < window_size:
            return 0.0
            
        recent_ears = ear_history[-window_size:]
        closed_count = sum(1 for ear in recent_ears if ear < self.ear_threshold)
        return closed_count / len(recent_ears)
    
    def detect_gaze_deviation(self, eye_landmarks: List[Tuple[int, int]]) -> float:
        """Detect gaze deviation from center"""
        if len(eye_landmarks) < 6:
            return 0.0
            
        # Calculate eye center
        eye_center = np.mean(eye_landmarks, axis=0)
        
        # Calculate pupil position relative to eye corners
        left_corner = eye_landmarks[0]
        right_corner = eye_landmarks[3]
        eye_width = np.linalg.norm(np.array(right_corner) - np.array(left_corner))
        
        if eye_width == 0:
            return 0.0
            
        # Deviation from center (normalized)
        center_x = (left_corner[0] + right_corner[0]) / 2
        deviation = abs(eye_center[0] - center_x) / eye_width
        
        return min(deviation, 1.0)
    
    def update_blink_rate(self, ear: float, current_time: float):
        """Update blink rate calculation"""
        # Detect blink (EAR drops below threshold)
        if ear < self.ear_threshold and len(self.blink_history) > 0:
            if self.blink_history[-1] >= self.ear_threshold:  # Start of blink
                if self.last_blink_time > 0:
                    blink_interval = current_time - self.last_blink_time
                    if blink_interval > 0.1:  # Minimum 100ms between blinks
                        self.last_blink_time = current_time
                else:
                    self.last_blink_time = current_time
        
        # Keep history of last 60 seconds
        self.blink_history.append(ear)
        if len(self.blink_history) > 1800:  # 30 FPS * 60 seconds
            self.blink_history.pop(0)
    
    def classify_driver_state(self, metrics: DriverMetrics) -> DriverState:
        """Classify driver state based on multiple metrics"""
        current_time = time.time()
        
        # Update counters
        if metrics.ear < self.ear_threshold:
            self.drowsy_frames += 1
            self.alert_frames = 0
        else:
            self.alert_frames += 1
            if self.alert_frames > 10:  # Reset after being alert
                self.drowsy_frames = 0
        
        # Classification logic
        if self.drowsy_frames > 90:  # 3 seconds at 30 FPS
            if metrics.perclos > 0.9:
                return DriverState.ASLEEP
            else:
                return DriverState.DROWSY
        
        # Check for intoxication indicators
        if (metrics.gaze_deviation > 0.7 or 
            abs(metrics.head_pose[1]) > 30 or  # Excessive head yaw
            metrics.blink_rate < 5):  # Very low blink rate
            return DriverState.INTOXICATED
        
        return DriverState.SOBER_ALERT
    
    def process_frame(self, landmarks: List[Tuple[int, int]], 
                     img_shape: Tuple[int, int]) -> Tuple[DriverState, DriverMetrics]:
        """Process a single frame and return driver state and metrics"""
        current_time = time.time()
        
        # Calculate EAR for both eyes
        left_eye = landmarks[36:42] if len(landmarks) > 41 else []
        right_eye = landmarks[42:48] if len(landmarks) > 47 else []
        
        left_ear = self.calculate_ear(left_eye) if left_eye else 0.0
        right_ear = self.calculate_ear(right_eye) if right_eye else 0.0
        ear = (left_ear + right_ear) / 2.0 if left_ear and right_ear else 0.0
        
        # Calculate MAR for yawning
        mouth_landmarks = landmarks[48:68] if len(landmarks) > 67 else []
        mar = self.calculate_mar(mouth_landmarks)
        
        # Head pose estimation
        head_pose = self.estimate_head_pose(landmarks, img_shape)
        
        # Update blink rate
        self.update_blink_rate(ear, current_time)
        
        # Calculate PERCLOS
        ear_history = [ear] * 30  # Simplified for demo
        perclos = self.calculate_perclos(ear_history)
        
        # Gaze deviation
        gaze_deviation = 0.0
        if left_eye and right_eye:
            left_gaze = self.detect_gaze_deviation(left_eye)
            right_gaze = self.detect_gaze_deviation(right_eye)
            gaze_deviation = (left_gaze + right_gaze) / 2.0
        
        # Create metrics object
        metrics = DriverMetrics(
            ear=ear,
            mar=mar,
            head_pose=head_pose,
            blink_rate=len([b for b in self.blink_history[-900:] if b < self.ear_threshold]),
            perclos=perclos,
            gaze_deviation=gaze_deviation,
            timestamp=current_time
        )
        
        # Classify state
        state = self.classify_driver_state(metrics)
        
        return state, metrics
    
    def calculate_ear(self, eye_landmarks: List[Tuple[int, int]]) -> float:
        """Calculate Eye Aspect Ratio"""
        if len(eye_landmarks) < 6:
            return 0.0
            
        # Vertical distances
        v1 = np.linalg.norm(np.array(eye_landmarks[1]) - np.array(eye_landmarks[5]))
        v2 = np.linalg.norm(np.array(eye_landmarks[2]) - np.array(eye_landmarks[4]))
        
        # Horizontal distance
        h = np.linalg.norm(np.array(eye_landmarks[0]) - np.array(eye_landmarks[3]))
        
        if h == 0:
            return 0.0
            
        return (v1 + v2) / (2.0 * h)