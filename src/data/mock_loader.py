import pandas as pd
import numpy as np
import time

class ADSDataLoader:
    """
    Data Loader for Autonomous Driving/Driver Monitoring Datasets.
    Supports:
    1. Loading CSV files (Impaired Driving Dataset format)
    2. Generating MOCK data for testing
    """
    
    @staticmethod
    def generate_mock_data(duration_sec: int = 60, scenario: str = "sober"):
        """
        Generate mock CAN bus data.
        Scenario: 'sober' or 'drunk'
        """
        hz = 10
        n_samples = duration_sec * hz
        
        # Time
        timestamps = np.linspace(0, duration_sec, n_samples)
        
        # Base Steering (Sine wave for a curve + noise)
        # Curve every 20 seconds
        t = np.linspace(0, duration_sec/5, n_samples)
        
        if scenario == "sober":
            # Smooth steering
            noise = np.random.normal(0, 0.5, n_samples) # Low noise
            steering = np.sin(t) * 10 + noise
            # Consistent speed
            speed = np.random.normal(60, 2, n_samples)
            
        else: # Drunk
            # Erratic steering (High frequency noise + overcorrections)
            noise = np.random.normal(0, 3.0, n_samples) # High noise
            # Random jerks
            jerks = np.random.choice([0, 15, -15], size=n_samples, p=[0.95, 0.025, 0.025])
            steering = np.sin(t) * 10 + noise + jerks
            
            # Variable speed
            speed = 60 + np.cumsum(np.random.normal(0, 1, n_samples))
            
        df = pd.DataFrame({
            "timestamp": timestamps,
            "steering_angle": steering,
            "speed_kmh": speed,
            "scenario": scenario
        })
        
        return df

    @staticmethod
    def load_csv(file_buffer) -> pd.DataFrame:
        """Load CSV and normalize columns"""
        try:
            df = pd.read_csv(file_buffer)
            # Normalize column names
            df.columns = [c.lower().strip() for c in df.columns]
            
            # Mapping common names
            col_map = {
                'steering': 'steering_angle',
                'angle': 'steering_angle',
                'speed': 'speed_kmh',
                'velocity': 'speed_kmh',
                'time': 'timestamp',
                'ts': 'timestamp'
            }
            df = df.rename(columns=col_map)
            
            return df
        except Exception as e:
            return pd.DataFrame()
