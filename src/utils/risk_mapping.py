"""
Predictive Risk Mapping System
Aggregates anonymous driving data to create dynamic micro-risk zone heatmaps
"""

import json
import time
from typing import Dict, List, Tuple
from dataclasses import dataclass, asdict
from collections import defaultdict
import hashlib

@dataclass
class RiskEvent:
    location_hash: str  # Anonymized location
    risk_type: str  # "drowsy", "distracted", "harsh_brake", "swerve"
    severity: int  # 1-5
    timestamp: float
    weather: str
    time_of_day: str

class RiskMappingSystem:
    def __init__(self, grid_size: float = 0.01):  # ~1km grid
        self.grid_size = grid_size
        self.risk_data = defaultdict(lambda: {"count": 0, "severity_sum": 0, "events": []})
        self.heatmap_cache = {}
        
    def anonymize_location(self, lat: float, lng: float) -> str:
        """Convert GPS to anonymized grid hash"""
        grid_lat = round(lat / self.grid_size) * self.grid_size
        grid_lng = round(lng / self.grid_size) * self.grid_size
        return hashlib.sha256(f"{grid_lat:.4f},{grid_lng:.4f}".encode()).hexdigest()[:16]
    
    def log_risk_event(self, lat: float, lng: float, risk_type: str, 
                      severity: int, weather: str = "clear"):
        """Log anonymous risk event"""
        location_hash = self.anonymize_location(lat, lng)
        hour = time.localtime().tm_hour
        time_of_day = "night" if hour < 6 or hour > 20 else "day"
        
        event = RiskEvent(
            location_hash=location_hash,
            risk_type=risk_type,
            severity=severity,
            timestamp=time.time(),
            weather=weather,
            time_of_day=time_of_day
        )
        
        self.risk_data[location_hash]["count"] += 1
        self.risk_data[location_hash]["severity_sum"] += severity
        self.risk_data[location_hash]["events"].append(asdict(event))
        
        # Keep only last 1000 events per zone
        if len(self.risk_data[location_hash]["events"]) > 1000:
            self.risk_data[location_hash]["events"].pop(0)
    
    def get_risk_score(self, lat: float, lng: float) -> Dict:
        """Get risk score for location"""
        location_hash = self.anonymize_location(lat, lng)
        data = self.risk_data[location_hash]
        
        if data["count"] == 0:
            return {"risk_level": "unknown", "score": 0, "incidents": 0}
        
        avg_severity = data["severity_sum"] / data["count"]
        
        # Calculate risk level
        if avg_severity >= 4:
            risk_level = "critical"
        elif avg_severity >= 3:
            risk_level = "high"
        elif avg_severity >= 2:
            risk_level = "medium"
        else:
            risk_level = "low"
        
        return {
            "risk_level": risk_level,
            "score": avg_severity,
            "incidents": data["count"],
            "location_hash": location_hash
        }
    
    def generate_heatmap_data(self, center_lat: float, center_lng: float, 
                             radius_km: float = 5) -> List[Dict]:
        """Generate heatmap data for area"""
        heatmap = []
        grid_count = int(radius_km / (self.grid_size * 111))  # ~111km per degree
        
        for i in range(-grid_count, grid_count + 1):
            for j in range(-grid_count, grid_count + 1):
                lat = center_lat + (i * self.grid_size)
                lng = center_lng + (j * self.grid_size)
                
                risk_info = self.get_risk_score(lat, lng)
                if risk_info["incidents"] > 0:
                    heatmap.append({
                        "lat": lat,
                        "lng": lng,
                        "risk_level": risk_info["risk_level"],
                        "score": risk_info["score"],
                        "incidents": risk_info["incidents"]
                    })
        
        return heatmap
    
    def export_data(self, filepath: str):
        """Export anonymized data for analysis"""
        export_data = {
            "grid_size": self.grid_size,
            "total_zones": len(self.risk_data),
            "zones": dict(self.risk_data)
        }
        
        with open(filepath, 'w') as f:
            json.dump(export_data, f, indent=2)
    
    def get_statistics(self) -> Dict:
        """Get overall statistics"""
        total_incidents = sum(d["count"] for d in self.risk_data.values())
        high_risk_zones = sum(1 for d in self.risk_data.values() 
                             if d["count"] > 0 and d["severity_sum"]/d["count"] >= 3)
        
        return {
            "total_zones_monitored": len(self.risk_data),
            "total_incidents": total_incidents,
            "high_risk_zones": high_risk_zones,
            "data_points": sum(len(d["events"]) for d in self.risk_data.values())
        }
