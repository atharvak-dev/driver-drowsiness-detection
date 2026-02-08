"""
Unit Tests for Vehicle Dynamics Analyzer
"""
import unittest
import numpy as np
from src.core.vehicle_dynamics import VehicleDynamicsAnalyzer, VehicleMetrics


class TestVehicleDynamicsAnalyzer(unittest.TestCase):
    """Test cases for vehicle dynamics analyzer."""
    
    def setUp(self):
        """Setup test fixtures."""
        self.analyzer = VehicleDynamicsAnalyzer(
            sample_rate_hz=10,
            min_samples=30
        )
    
    def test_validate_input_valid(self):
        """Test input validation with valid data."""
        data = np.random.randn(100)
        is_valid = self.analyzer.validate_input(data, "test_data")
        self.assertTrue(is_valid)
    
    def test_validate_input_insufficient_samples(self):
        """Test input validation with insufficient samples."""
        data = np.random.randn(10)
        is_valid = self.analyzer.validate_input(data, "test_data")
        self.assertFalse(is_valid)
    
    def test_validate_input_with_nan(self):
        """Test input validation with NaN values."""
        data = np.array([1.0, 2.0, np.nan, 4.0] * 10)
        is_valid = self.analyzer.validate_input(data, "test_data")
        self.assertFalse(is_valid)
    
    def test_calculate_steering_entropy_normal(self):
        """Test steering entropy calculation with normal driving."""
        # Simulate smooth steering (low entropy)
        t = np.linspace(0, 10, 100)
        steering = 5 * np.sin(0.5 * t)  # Smooth sinusoidal steering
        
        entropy = self.analyzer.calculate_steering_entropy(steering)
        
        self.assertIsInstance(entropy, float)
        self.assertGreaterEqual(entropy, 0.0)
        self.assertLessEqual(entropy, 5.0)
    
    def test_calculate_steering_entropy_erratic(self):
        """Test steering entropy calculation with erratic driving."""
        # Simulate erratic steering (high entropy)
        np.random.seed(42)
        steering = np.random.randn(100) * 20  # Random steering
        
        entropy = self.analyzer.calculate_steering_entropy(steering)
        
        self.assertGreater(entropy, 0.0)
    
    def test_calculate_lane_deviation(self):
        """Test lane deviation calculation."""
        # Simulate lane position with some weaving
        lane_pos = np.array([0.1, 0.15, 0.2, -0.1, -0.05, 0.0] * 20)
        
        sdlp = self.analyzer.calculate_lane_deviation(lane_pos)
        
        self.assertIsInstance(sdlp, float)
        self.assertGreater(sdlp, 0.0)
    
    def test_calculate_speed_variability(self):
        """Test speed variability calculation."""
        # Simulate relatively stable speed
        speed = np.array([100.0, 102.0, 98.0, 101.0, 99.0] * 20)
        
        cv = self.analyzer.calculate_speed_variability(speed)
        
        self.assertIsInstance(cv, float)
        self.assertGreater(cv, 0.0)
        self.assertLess(cv, 100.0)  # Should be reasonable
    
    def test_calculate_speed_variability_low_speed(self):
        """Test speed variability with low speed (should return 0)."""
        speed = np.array([2.0, 3.0, 2.5, 2.8] * 10)
        
        cv = self.analyzer.calculate_speed_variability(speed)
        
        self.assertEqual(cv, 0.0)  # Too slow, should skip
    
    def test_calculate_risk_score(self):
        """Test risk score calculation."""
        entropy = 0.5
        speed_var = 10.0
        lane_dev = 0.3
        
        risk = self.analyzer.calculate_risk_score(entropy, speed_var, lane_dev)
        
        self.assertIsInstance(risk, float)
        self.assertGreaterEqual(risk, 0.0)
        self.assertLessEqual(risk, 1.0)
    
    def test_classify_risk_level_normal(self):
        """Test risk classification for normal driving."""
        level = self.analyzer.classify_risk_level(
            risk_score=0.2,
            steering_entropy=0.3,
            speed_var=5.0,
            lane_dev=0.2
        )
        
        self.assertEqual(level, "NORMAL")
    
    def test_classify_risk_level_high_risk(self):
        """Test risk classification for high risk."""
        level = self.analyzer.classify_risk_level(
            risk_score=0.8,
            steering_entropy=0.6,
            speed_var=20.0,
            lane_dev=0.7
        )
        
        self.assertIn(level, ["HIGH_RISK", "CRITICAL"])
    
    def test_analyze_with_all_data(self):
        """Test full analysis with all sensor data."""
        np.random.seed(42)
        
        steering = np.random.randn(100) * 10
        lane_pos = np.random.randn(100) * 0.3
        speed = 100 + np.random.randn(100) * 5
        
        metrics = self.analyzer.analyze(
            steering_angles=steering,
            lane_position=lane_pos,
            speed_kmh=speed
        )
        
        self.assertIsInstance(metrics, VehicleMetrics)
        self.assertTrue(metrics.is_valid)
        self.assertGreater(metrics.sample_count, 0)
        self.assertIn(metrics.risk_level, ["NORMAL", "POSSIBLE_IMPAIRMENT", "HIGH_RISK", "CRITICAL"])
    
    def test_analyze_with_partial_data(self):
        """Test analysis with only some sensor data."""
        steering = np.random.randn(100) * 10
        
        metrics = self.analyzer.analyze(steering_angles=steering)
        
        self.assertIsInstance(metrics, VehicleMetrics)
        self.assertGreater(len(metrics.warnings), 0)
    
    def test_get_statistics(self):
        """Test statistics retrieval."""
        # Run some analyses
        for _ in range(5):
            self.analyzer.analyze(
                steering_angles=np.random.randn(100) * 10
            )
        
        stats = self.analyzer.get_statistics()
        
        self.assertEqual(stats["total_analyses"], 5)
        self.assertIn("thresholds", stats)
    
    def test_reset(self):
        """Test analyzer reset."""
        self.analyzer.analyze(steering_angles=np.random.randn(100) * 10)
        self.analyzer.reset()
        
        stats = self.analyzer.get_statistics()
        self.assertEqual(stats["total_analyses"], 0)
        self.assertIsNone(stats["last_metrics"])


class TestVehicleMetrics(unittest.TestCase):
    """Test cases for VehicleMetrics dataclass."""
    
    def test_to_dict(self):
        """Test conversion to dictionary."""
        metrics = VehicleMetrics(
            steering_entropy=0.5,
            lane_deviation=0.3,
            speed_variability=10.0,
            risk_score=0.6,
            risk_level="POSSIBLE_IMPAIRMENT",
            sample_count=100,
            is_valid=True
        )
        
        data = metrics.to_dict()
        
        self.assertIsInstance(data, dict)
        self.assertEqual(data["steering_entropy"], 0.5)
        self.assertEqual(data["risk_level"], "POSSIBLE_IMPAIRMENT")
        self.assertIn("timestamp", data)


if __name__ == '__main__':
    unittest.main()
