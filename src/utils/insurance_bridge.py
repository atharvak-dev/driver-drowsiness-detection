"""
Insurance Data Bridge API
Provides secure, verified behavior-based data for insurers
"""

import json
import time
import hashlib
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta

@dataclass
class DrivingSession:
    session_id: str
    start_time: float
    end_time: float
    duration_minutes: float
    distance_km: float
    alerts_triggered: int
    drowsy_events: int
    distraction_events: int
    harsh_brakes: int
    speeding_events: int
    safety_score: float  # 0-100

@dataclass
class DriverProfile:
    driver_id: str
    total_sessions: int
    total_distance_km: float
    total_driving_hours: float
    average_safety_score: float
    risk_category: str  # "low", "medium", "high"
    last_updated: str

class InsuranceDataBridge:
    def __init__(self, driver_id: str):
        self.driver_id = driver_id
        self.sessions = []
        self.api_keys = {}
        
    def generate_api_key(self, insurer_name: str) -> str:
        """Generate secure API key for insurer"""
        key = hashlib.sha256(f"{insurer_name}{time.time()}{self.driver_id}".encode()).hexdigest()
        self.api_keys[key] = {
            "insurer": insurer_name,
            "created": time.time(),
            "active": True
        }
        return key
    
    def verify_api_key(self, api_key: str) -> bool:
        """Verify API key validity"""
        if api_key not in self.api_keys:
            return False
        return self.api_keys[api_key]["active"]
    
    def log_session(self, session: DrivingSession):
        """Log driving session"""
        self.sessions.append(session)
        
        # Keep last 90 days
        cutoff = time.time() - (90 * 24 * 3600)
        self.sessions = [s for s in self.sessions if s.end_time > cutoff]
    
    def calculate_safety_score(self, session: DrivingSession) -> float:
        """Calculate safety score for session"""
        base_score = 100.0
        
        # Deduct points for incidents
        base_score -= session.drowsy_events * 10
        base_score -= session.distraction_events * 8
        base_score -= session.harsh_brakes * 5
        base_score -= session.speeding_events * 7
        base_score -= session.alerts_triggered * 3
        
        return max(0.0, min(100.0, base_score))
    
    def get_driver_profile(self, api_key: str) -> Optional[Dict]:
        """Get driver profile for insurer"""
        if not self.verify_api_key(api_key):
            return None
        
        if not self.sessions:
            return None
        
        total_distance = sum(s.distance_km for s in self.sessions)
        total_hours = sum(s.duration_minutes for s in self.sessions) / 60
        avg_score = sum(s.safety_score for s in self.sessions) / len(self.sessions)
        
        # Determine risk category
        if avg_score >= 85:
            risk_category = "low"
        elif avg_score >= 70:
            risk_category = "medium"
        else:
            risk_category = "high"
        
        profile = DriverProfile(
            driver_id=hashlib.sha256(self.driver_id.encode()).hexdigest()[:16],  # Anonymized
            total_sessions=len(self.sessions),
            total_distance_km=round(total_distance, 2),
            total_driving_hours=round(total_hours, 2),
            average_safety_score=round(avg_score, 2),
            risk_category=risk_category,
            last_updated=datetime.now().isoformat()
        )
        
        return asdict(profile)
    
    def get_monthly_summary(self, api_key: str, month: int, year: int) -> Optional[Dict]:
        """Get monthly driving summary"""
        if not self.verify_api_key(api_key):
            return None
        
        # Filter sessions for month
        month_sessions = [
            s for s in self.sessions
            if datetime.fromtimestamp(s.start_time).month == month
            and datetime.fromtimestamp(s.start_time).year == year
        ]
        
        if not month_sessions:
            return None
        
        return {
            "month": month,
            "year": year,
            "total_trips": len(month_sessions),
            "total_distance_km": round(sum(s.distance_km for s in month_sessions), 2),
            "total_hours": round(sum(s.duration_minutes for s in month_sessions) / 60, 2),
            "average_safety_score": round(sum(s.safety_score for s in month_sessions) / len(month_sessions), 2),
            "total_alerts": sum(s.alerts_triggered for s in month_sessions),
            "drowsy_incidents": sum(s.drowsy_events for s in month_sessions),
            "distraction_incidents": sum(s.distraction_events for s in month_sessions)
        }
    
    def get_premium_recommendation(self, api_key: str) -> Optional[Dict]:
        """Get premium recommendation based on driving behavior"""
        if not self.verify_api_key(api_key):
            return None
        
        profile = self.get_driver_profile(api_key)
        if not profile:
            return None
        
        base_premium = 10000  # Base annual premium in INR
        
        # Adjust based on safety score
        score = profile["average_safety_score"]
        if score >= 90:
            discount = 0.30  # 30% discount
        elif score >= 85:
            discount = 0.20
        elif score >= 75:
            discount = 0.10
        elif score >= 70:
            discount = 0.0
        else:
            discount = -0.20  # 20% surcharge
        
        adjusted_premium = base_premium * (1 - discount)
        
        return {
            "base_premium": base_premium,
            "discount_percentage": round(discount * 100, 1),
            "adjusted_premium": round(adjusted_premium, 2),
            "risk_category": profile["risk_category"],
            "safety_score": profile["average_safety_score"],
            "recommendation": "approved" if score >= 60 else "review_required"
        }
    
    def generate_claims_report(self, api_key: str, incident_timestamp: float) -> Optional[Dict]:
        """Generate instant claims report for incident"""
        if not self.verify_api_key(api_key):
            return None
        
        # Find session at incident time
        incident_session = None
        for session in self.sessions:
            if session.start_time <= incident_timestamp <= session.end_time:
                incident_session = session
                break
        
        if not incident_session:
            return {"status": "no_data", "message": "No driving data for incident time"}
        
        return {
            "incident_timestamp": datetime.fromtimestamp(incident_timestamp).isoformat(),
            "session_id": incident_session.session_id,
            "driver_state_at_incident": "verified",
            "safety_score_before_incident": incident_session.safety_score,
            "alerts_in_session": incident_session.alerts_triggered,
            "drowsy_events_in_session": incident_session.drowsy_events,
            "verification_status": "ai_verified",
            "claim_recommendation": "process" if incident_session.safety_score >= 70 else "investigate"
        }
    
    def revoke_api_key(self, api_key: str):
        """Revoke insurer API access"""
        if api_key in self.api_keys:
            self.api_keys[api_key]["active"] = False
    
    def export_for_insurer(self, api_key: str, filepath: str):
        """Export data for insurer"""
        if not self.verify_api_key(api_key):
            return False
        
        data = {
            "driver_profile": self.get_driver_profile(api_key),
            "premium_recommendation": self.get_premium_recommendation(api_key),
            "export_timestamp": datetime.now().isoformat(),
            "data_period_days": 90
        }
        
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
        
        return True
