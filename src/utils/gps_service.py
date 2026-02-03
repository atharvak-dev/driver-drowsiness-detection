"""
GPS Location Service using MapmyIndia (Mappls) API
Secure implementation with environment variable configuration
"""

import requests
from typing import Dict, Optional
from config.env_config import Config

class GPSLocationService:
    def __init__(self):
        self.api_key = Config.MAPPLS_API_KEY
        if not self.api_key:
            print("⚠️  MAPPLS_API_KEY not configured. Using mock GPS data.")
            self.api_key = None
        
        self.base_url = "https://apis.mappls.com/advancedmaps/v1"
        
    def get_current_location(self) -> Optional[Dict[str, float]]:
        """
        Get current GPS location
        In production, this would interface with actual GPS hardware
        For now, returns browser geolocation or mock data
        """
        # TODO: Implement actual GPS hardware interface
        # For web-based demo, use browser geolocation API
        return self._get_mock_location()
    
    def _get_mock_location(self) -> Dict[str, float]:
        """Mock location for demo purposes"""
        return {
            "lat": 28.6139,
            "lng": 77.2090,
            "accuracy": 10.0,
            "provider": "mock"
        }
    
    def reverse_geocode(self, lat: float, lng: float) -> Optional[Dict]:
        """
        Convert coordinates to address using Mappls API
        """
        try:
            url = f"{self.base_url}/{self.api_key}/rev_geocode"
            params = {
                "lat": lat,
                "lng": lng
            }
            
            response = requests.get(url, params=params, timeout=5)
            response.raise_for_status()
            
            return response.json()
        except Exception as e:
            print(f"Reverse geocoding failed: {e}")
            return None
    
    def get_location_with_address(self) -> Dict:
        """Get location with human-readable address"""
        location = self.get_current_location()
        
        if location:
            address_data = self.reverse_geocode(location["lat"], location["lng"])
            if address_data:
                location["address"] = address_data
        
        return location

# Singleton instance
_gps_service = None

def get_gps_service() -> GPSLocationService:
    """Get GPS service singleton"""
    global _gps_service
    if _gps_service is None:
        _gps_service = GPSLocationService()
    return _gps_service
