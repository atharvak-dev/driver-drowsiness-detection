import cv2
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
import av
import threading
from streamlit_webrtc import VideoProcessorBase

# Local imports
import collections
import numpy as np
from config.config import (EAR_THRESHOLD, CONSEC_FRAMES, MODEL_PATH, ALARM_FILE, 
                           SMOOTHING_WINDOW, CALIBRATION_FRAMES, 
                           PERCLOS_WINDOW, PERCLOS_THRESHOLD)
from src.core.ear import calculate_ear
from src.utils.audio import play_alarm_sound

class DrowsinessDetector(VideoProcessorBase):
    def __init__(self):
        # Load Face Landmarker
        try:
            base_options = python.BaseOptions(model_asset_path=MODEL_PATH)
            options = vision.FaceLandmarkerOptions(base_options=base_options,
                                                   output_face_blendshapes=True,
                                                   output_facial_transformation_matrixes=False,
                                                   num_faces=1)
            self.detector = vision.FaceLandmarker.create_from_options(options)
        except Exception as e:
            print(f"Error initializing MediaPipe FaceLandmarker: {e}")
            raise e

        self.frame_count = 0
        self.drowsy = False
        self.alarm_thread = None
        self.ear_history = collections.deque(maxlen=SMOOTHING_WINDOW)
        
        # Calibration
        self.is_calibrating = True
        self.calibration_frames = 0
        self.calibration_data = []
        self.ear_threshold = EAR_THRESHOLD  # Start with default, update after calibration
        
        # PERCLOS
        self.closed_history = collections.deque(maxlen=PERCLOS_WINDOW)

    def recv(self, frame):
        try:
            img = frame.to_ndarray(format="bgr24")
            img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=img_rgb)
            detection_result = self.detector.detect(mp_image)
            
            if detection_result.face_landmarks:
                for face_landmarks in detection_result.face_landmarks:
                    h, w, _ = img.shape
                    # face_landmarks is already a list of landmarks in Tasks API
                    landmarks = [(int(l.x * w), int(l.y * h)) for l in face_landmarks]

                    # Left and right eye indices (MediaPipe Face Mesh)
                    left_eye = [362, 385, 387, 263, 373, 380]
                    right_eye = [33, 160, 158, 133, 153, 144]

                    left_ear = calculate_ear(landmarks, left_eye)
                    right_ear = calculate_ear(landmarks, right_eye)
                    raw_ear = (left_ear + right_ear) / 2.0

                    # Smoothing
                    self.ear_history.append(raw_ear)
                    ear = np.mean(self.ear_history)
                    
                    # Visualize eye landmarks for debugging
                    for idx in left_eye:
                        cv2.circle(img, landmarks[idx], 2, (0, 255, 0), -1)
                    for idx in right_eye:
                        cv2.circle(img, landmarks[idx], 2, (0, 255, 0), -1)

                    if self.is_calibrating:
                        self.calibration_data.append(ear)
                        self.calibration_frames += 1
                        
                        progress = int((self.calibration_frames / CALIBRATION_FRAMES) * 100)
                        cv2.putText(img, f"CALIBRATING... {progress}%", (30, 60),
                                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 2)
                        cv2.putText(img, "Please look straight ahead", (30, 100),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)

                        if self.calibration_frames >= CALIBRATION_FRAMES:
                            baseline_ear = np.mean(self.calibration_data)
                            # Set threshold to 80% of baseline
                            self.ear_threshold = baseline_ear * 0.8
                            self.is_calibrating = False
                            print(f"Calibration Complete. Baseline: {baseline_ear:.3f}, New Threshold: {self.ear_threshold:.3f}")
                    
                    else:
                        # Normal Detection Logic
                        is_closed = ear < self.ear_threshold
                        self.closed_history.append(1 if is_closed else 0)
                        
                        # Calculate PERCLOS
                        perclos = np.mean(self.closed_history) if len(self.closed_history) > 0 else 0
                        
                        if is_closed:
                            self.frame_count += 1
                        else:
                            self.frame_count = 0
                            self.drowsy = False

                        # Trigger ALARM if Micro-Sleep (Time) OR Fatigue (PERCLOS)
                        if self.frame_count >= CONSEC_FRAMES or perclos > PERCLOS_THRESHOLD:
                            self.drowsy = True
                            
                            reason = "MICRO-SLEEP!" if self.frame_count >= CONSEC_FRAMES else "FATIGUE DETECTED!"
                            cv2.putText(img, reason, (30, 60),
                                        cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 0, 255), 3)
                            
                            # Play alarm in separate thread
                            if self.alarm_thread is None or not self.alarm_thread.is_alive():
                                self.alarm_thread = threading.Thread(target=play_alarm_sound, args=(ALARM_FILE,))
                                self.alarm_thread.start()
                        else:
                            cv2.putText(img, f"EAR: {ear:.2f} | Thresh: {self.ear_threshold:.2f}", (30, 30),
                                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
                            cv2.putText(img, f"PERCLOS: {perclos:.2%}", (30, 60),
                                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

            return av.VideoFrame.from_ndarray(img, format="bgr24")
        except Exception as e:
            print(f"Error in processing frame: {e}")
            return frame
