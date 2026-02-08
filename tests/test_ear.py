"""
Unit Tests for EAR Calculator
"""
import unittest
import numpy as np
from src.core.ear import EARCalculator, EARSmoother


class TestEARCalculator(unittest.TestCase):
    """Test cases for EAR calculator."""
    
    def setUp(self):
        """Setup test fixtures."""
        self.calculator = EARCalculator()
        
        # Create mock landmarks (simplified face mesh)
        self.mock_landmarks = [(i * 10, i * 10) for i in range(500)]
        
    def test_euclidean_distance(self):
        """Test Euclidean distance calculation."""
        p1 = (0, 0)
        p2 = (3, 4)
        distance = self.calculator.euclidean_distance(p1, p2)
        self.assertAlmostEqual(distance, 5.0, places=5)
    
    def test_calculate_single_eye_ear_valid(self):
        """Test EAR calculation for single eye with valid data."""
        eye_indices = [0, 1, 2, 3, 4, 5]
        
        # Create landmarks with known geometry
        landmarks = [
            (0, 5),    # outer
            (2, 7),    # top-outer
            (4, 7),    # top-inner
            (6, 5),    # inner
            (4, 3),    # bottom-inner
            (2, 3)     # bottom-outer
        ]
        
        ear = self.calculator.calculate_single_eye_ear(landmarks, eye_indices)
        self.assertIsNotNone(ear)
        self.assertGreater(ear, 0)
        self.assertLess(ear, 1)
    
    def test_calculate_single_eye_ear_invalid_indices(self):
        """Test EAR calculation with invalid number of indices."""
        eye_indices = [0, 1, 2]  # Only 3 instead of 6
        ear = self.calculator.calculate_single_eye_ear(self.mock_landmarks, eye_indices)
        self.assertIsNone(ear)
    
    def test_calculate_ear_both_eyes(self):
        """Test EAR calculation for both eyes."""
        result = self.calculator.calculate_ear(self.mock_landmarks)
        
        # Should return result even if calculation fails
        self.assertIsNotNone(result)
        self.assertIsInstance(result.ear, float)
        self.assertIsInstance(result.is_valid, bool)
    
    def test_validate_landmarks_valid(self):
        """Test landmark validation with valid data."""
        is_valid = self.calculator.validate_landmarks(self.mock_landmarks)
        self.assertTrue(is_valid)
    
    def test_validate_landmarks_insufficient(self):
        """Test landmark validation with insufficient landmarks."""
        short_landmarks = [(0, 0)] * 100
        is_valid = self.calculator.validate_landmarks(short_landmarks)
        self.assertFalse(is_valid)


class TestEARSmoother(unittest.TestCase):
    """Test cases for EAR smoother."""
    
    def setUp(self):
        """Setup test fixtures."""
        self.smoother = EARSmoother(window_size=5)
    
    def test_initial_state(self):
        """Test initial smoother state."""
        self.assertFalse(self.smoother.is_ready)
        self.assertEqual(len(self.smoother.buffer), 0)
    
    def test_add_values(self):
        """Test adding values to smoother."""
        values = [0.3, 0.32, 0.31, 0.33, 0.30]
        
        for val in values:
            smoothed = self.smoother.add(val)
        
        self.assertTrue(self.smoother.is_ready)
        self.assertEqual(len(self.smoother.buffer), 5)
        self.assertAlmostEqual(smoothed, np.mean(values), places=5)
    
    def test_window_limit(self):
        """Test that buffer doesn't exceed window size."""
        for i in range(10):
            self.smoother.add(float(i))
        
        self.assertEqual(len(self.smoother.buffer), 5)
        # Should contain last 5 values: [5, 6, 7, 8, 9]
        self.assertEqual(self.smoother.buffer, [5.0, 6.0, 7.0, 8.0, 9.0])
    
    def test_reset(self):
        """Test smoother reset."""
        self.smoother.add(0.3)
        self.smoother.add(0.32)
        self.smoother.reset()
        
        self.assertEqual(len(self.smoother.buffer), 0)
        self.assertFalse(self.smoother.is_ready)


if __name__ == '__main__':
    unittest.main()
