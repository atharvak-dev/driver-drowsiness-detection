import numpy as np
import pandas as pd
from scipy.stats import entropy
from typing import List, Optional, Tuple

class VehicleDynamicsAnalyzer:
    """
    Analyzer for Vehicle Dynamics to detect impairment patterns.
    Implements Steering Entropy and other control metrics.
    """
    
    def __init__(self, sample_rate_hz: int = 10):
        self.sample_rate = sample_rate_hz
        
    def calculate_steering_entropy(self, steering_angles: np.array, window_size_sec: float = 30.0) -> float:
        """
        Calculate Steering Entropy (Boer's method approximation).
        High entropy indicates frequent, erratic corrections (common in drunk/drowsy drivers).
        Low entropy indicates smooth, predictable control.
        """
        if len(steering_angles) < self.sample_rate:
            return 0.0
            
        # 1. Prediction Error (Taylor expansion / 2nd order)
        # We predict theta(t+1) based on theta(t), theta(t-1), theta(t-2)
        # Using a simple 2nd order predictor: theta_pred = theta(t) + (theta(t) - theta(t-1))
        # More robust: 2nd order extrapolator
        
        # Calculate 2nd derivative (jerkiness proxy)
        # diff1 = np.diff(steering_angles)
        # diff2 = np.diff(diff1)
        
        # Using Boer's simplified robust method:
        # 1. Resample/Smooth (assuming roughly 10Hz input)
        # 2. Predict next angle
        # 3. Calculate prediction error
        # 4. Bin errors into 9 bins (alpha=0.9 for 90% confidence interval)
        # 5. Calculate Shannon entropy of the distribution
        
        # Simplified Implementation for Prototype:
        # Calculate prediction errors using 2nd order Taylor series
        # theta_p(n+1) = theta(n) + theta'(n)*dt + 0.5*theta''(n)*dt^2
        # Approximated by: theta(n) + (theta(n) - theta(n-1)) for linear
        
        preds = steering_angles[:-1] + (steering_angles[:-1] - np.roll(steering_angles, 1)[:-1])
        actuals = steering_angles[1:]
        errors = actuals - preds
        
        # Remove first few nan/garbage indices
        errors = errors[2:]
        
        if len(errors) == 0:
            return 0.0
            
        # Binning (Boer uses alpha-percentile range)
        p90 = np.percentile(np.abs(errors), 90)
        if p90 == 0: 
            return 0.0
            
        # 9 bins centered around 0
        bins = np.array([-np.inf, -5*p90, -2.5*p90, -1*p90, -0.5*p90, 0.5*p90, 1*p90, 2.5*p90, 5*p90, np.inf])
        
        # Calculate distribution
        counts, _ = np.histogram(errors, bins=bins)
        probs = counts / np.sum(counts)
        
        # Shannon Entropy
        # H = -sum(p * log2(p))
        h = entropy(probs, base=2)
        
        return h

    def calculate_lane_deviation(self, lane_position: np.array) -> float:
        """
        Calculate Standard Deviation of Lateral Lane Position (SDLP).
        High SDLP indicates 'weaving' or inability to maintain center.
        """
        if len(lane_position) == 0:
            return 0.0
            
        return np.std(lane_position)

    def calculate_speed_variability(self, speed_kmh: np.array) -> float:
        """
        Calculate Coefficient of Variation of Speed.
        CV = std_dev / mean
        """
        if len(speed_kmh) == 0:
            return 0.0
            
        mean_speed = np.mean(speed_kmh)
        if mean_speed < 5: # Idle/Parking
            return 0.0
            
        std_dev = np.std(speed_kmh)
        return (std_dev / mean_speed) * 100 # Percentage

    def detect_high_risk_event(self, steering_entropy: float, speed_var: float, lane_dev: float = 0.0) -> str:
        """
        Classify risk based on thresholds (Research Prototype Logic)
        """
        # Thresholds derived from literature (Impaired Driving Dataset)
        ENTROPY_THRESHOLD = 0.45  # Normal is usually < 0.4
        SPEED_VAR_THRESHOLD = 15.0 # Normal < 10%
        LANE_DEV_THRESHOLD = 0.5   # Meters (weaving)
        
        if steering_entropy > ENTROPY_THRESHOLD:
            if speed_var > SPEED_VAR_THRESHOLD or lane_dev > LANE_DEV_THRESHOLD:
               return "HIGH_RISK_IMPAIRMENT"
            return "POSSIBLE_CONTROL_LOSS"
            
        return "NORMAL"
