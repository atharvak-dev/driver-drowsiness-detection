"""
Multi-Stakeholder Alert Ecosystem
Coordinates alerts to family, police, and ambulance services
"""

import json
import time
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
from enum import Enum
from config.env_config import Config

class IncidentSeverity(Enum):
    MINOR = "minor"
    MODERATE = "moderate"
    SEVERE = "severe"
    CRITICAL = "critical"

@dataclass
class Incident:
    incident_id: str
    timestamp: float
    location: Dict[str, float]
    severity: str
    driver_state: str
    vehicle_speed: float
    airbag_deployed: bool
    verified: bool

class MultiStakeholderAlertSystem:
    def __init__(self, config_path: str = "config/stakeholder_config.json"):
        self.config = self.load_config(config_path)
        self.active_incidents = {}
        
    def load_config(self, config_path: str) -> Dict:
        """Load stakeholder configuration"""
        default_config = {
            "family_contacts": [
                {"name": "Primary Contact", "phone": "+91XXXXXXXXXX", "priority": 1},
                {"name": "Secondary Contact", "phone": "+91XXXXXXXXXX", "priority": 2}
            ],
            "emergency_services": {
                "police": {
                    "api_endpoint": "https://police-emergency.gov.in/api/incident",
                    "api_key": Config.POLICE_API_KEY or "YOUR_POLICE_API_KEY",
                    "enabled": bool(Config.POLICE_API_KEY)
                },
                "ambulance": {
                    "api_endpoint": "https://ambulance-108.gov.in/api/request",
                    "api_key": Config.AMBULANCE_API_KEY or "YOUR_AMBULANCE_API_KEY",
                    "enabled": bool(Config.AMBULANCE_API_KEY)
                }
            },
            "alert_rules": {
                "family_alert_threshold": "moderate",
                "police_alert_threshold": "severe",
                "ambulance_alert_threshold": "critical",
                "auto_verify_critical": True
            }
        }
        
        try:
            with open(config_path, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            import os
            os.makedirs(os.path.dirname(config_path), exist_ok=True)
            with open(config_path, 'w') as f:
                json.dump(default_config, f, indent=2)
            return default_config
    
    def assess_severity(self, driver_state: str, duration: float, 
                       vehicle_speed: float, airbag: bool) -> IncidentSeverity:
        """Assess incident severity"""
        if airbag or vehicle_speed > 80:
            return IncidentSeverity.CRITICAL
        
        if driver_state == "Asleep" and vehicle_speed > 40:
            return IncidentSeverity.SEVERE
        
        if driver_state == "Drunk" or (driver_state == "Drowsy" and duration > 10):
            return IncidentSeverity.SEVERE
        
        if driver_state == "Drowsy" and duration > 5:
            return IncidentSeverity.MODERATE
        
        return IncidentSeverity.MINOR
    
    def create_incident(self, driver_state: str, location: Dict, 
                       vehicle_speed: float = 0, duration: float = 0,
                       airbag_deployed: bool = False) -> Incident:
        """Create incident record"""
        severity = self.assess_severity(driver_state, duration, vehicle_speed, airbag_deployed)
        
        incident = Incident(
            incident_id=f"INC_{int(time.time())}",
            timestamp=time.time(),
            location=location,
            severity=severity.value,
            driver_state=driver_state,
            vehicle_speed=vehicle_speed,
            airbag_deployed=airbag_deployed,
            verified=severity == IncidentSeverity.CRITICAL and self.config["alert_rules"]["auto_verify_critical"]
        )
        
        self.active_incidents[incident.incident_id] = incident
        return incident
    
    def alert_family(self, incident: Incident) -> Dict:
        """Send alert to family contacts (real SMS if configured)"""
        threshold = self.config["alert_rules"]["family_alert_threshold"]
        severity_levels = ["minor", "moderate", "severe", "critical"]
        
        if severity_levels.index(incident.severity) < severity_levels.index(threshold):
            return {"status": "skipped", "reason": "below_threshold"}
        
        from src.utils.sms_service import get_sms_service
        sms_service = get_sms_service()
        
        messages_sent = []
        for contact in self.config["family_contacts"]:
            message = self._create_family_message(incident, contact)
            
            if sms_service.enabled:
                # Send real SMS
                result = sms_service.send_sms(contact['phone'], message)
                print(f"[FAMILY SMS] Sent to {contact['name']}: {result['status']}")
                messages_sent.append({
                    "contact": contact["name"],
                    "phone": contact["phone"],
                    "status": result["status"],
                    "timestamp": time.time()
                })
            else:
                # Mock SMS
                print(f"[MOCK FAMILY ALERT] To {contact['name']} ({contact['phone']})")
                print(f"Message: {message}")
                messages_sent.append({
                    "contact": contact["name"],
                    "phone": contact["phone"],
                    "status": "mocked",
                    "timestamp": time.time()
                })
        
        return {
            "status": "success",
            "messages_sent": len(messages_sent),
            "contacts": messages_sent
        }
    
    def alert_police(self, incident: Incident) -> Dict:
        """Send verified incident to police"""
        threshold = self.config["alert_rules"]["police_alert_threshold"]
        severity_levels = ["minor", "moderate", "severe", "critical"]
        
        if severity_levels.index(incident.severity) < severity_levels.index(threshold):
            return {"status": "skipped", "reason": "below_threshold"}
        
        if not incident.verified:
            return {"status": "skipped", "reason": "not_verified"}
        
        police_config = self.config["emergency_services"]["police"]
        if not police_config["enabled"]:
            return {"status": "disabled", "reason": "police_api_disabled"}
        
        incident_data = {
            "incident_id": incident.incident_id,
            "timestamp": incident.timestamp,
            "location": incident.location,
            "severity": incident.severity,
            "driver_state": incident.driver_state,
            "vehicle_speed": incident.vehicle_speed,
            "verification": "ai_verified"
        }
        
        # Mock API call
        print(f"[POLICE ALERT] Sending to {police_config['api_endpoint']}")
        print(f"Data: {json.dumps(incident_data, indent=2)}")
        
        return {
            "status": "sent",
            "endpoint": police_config["api_endpoint"],
            "incident_id": incident.incident_id,
            "timestamp": time.time()
        }
    
    def request_ambulance(self, incident: Incident) -> Dict:
        """Request ambulance for critical incidents"""
        threshold = self.config["alert_rules"]["ambulance_alert_threshold"]
        severity_levels = ["minor", "moderate", "severe", "critical"]
        
        if severity_levels.index(incident.severity) < severity_levels.index(threshold):
            return {"status": "skipped", "reason": "below_threshold"}
        
        ambulance_config = self.config["emergency_services"]["ambulance"]
        if not ambulance_config["enabled"]:
            return {"status": "disabled", "reason": "ambulance_api_disabled"}
        
        request_data = {
            "incident_id": incident.incident_id,
            "location": incident.location,
            "severity": incident.severity,
            "patient_status": "driver_unresponsive" if incident.driver_state == "Asleep" else "driver_impaired",
            "airbag_deployed": incident.airbag_deployed,
            "priority": "high" if incident.severity == "critical" else "medium"
        }
        
        # Mock API call
        print(f"[AMBULANCE REQUEST] Sending to {ambulance_config['api_endpoint']}")
        print(f"Data: {json.dumps(request_data, indent=2)}")
        
        return {
            "status": "requested",
            "endpoint": ambulance_config["api_endpoint"],
            "incident_id": incident.incident_id,
            "eta_minutes": 8,  # Mock ETA
            "timestamp": time.time()
        }
    
    def trigger_coordinated_response(self, driver_state: str, location: Dict,
                                    vehicle_speed: float = 0, duration: float = 0,
                                    airbag_deployed: bool = False) -> Dict:
        """Trigger coordinated multi-stakeholder response"""
        # Create incident
        incident = self.create_incident(driver_state, location, vehicle_speed, 
                                       duration, airbag_deployed)
        
        print(f"\n🚨 COORDINATED EMERGENCY RESPONSE TRIGGERED 🚨")
        print(f"Incident ID: {incident.incident_id}")
        print(f"Severity: {incident.severity.upper()}")
        print(f"Driver State: {driver_state}")
        print(f"Location: {location['lat']:.4f}, {location['lng']:.4f}")
        print("="*60)
        
        # Execute coordinated response
        responses = {
            "incident": asdict(incident),
            "family_alert": self.alert_family(incident),
            "police_alert": self.alert_police(incident),
            "ambulance_request": self.request_ambulance(incident)
        }
        
        return responses
    
    def _create_family_message(self, incident: Incident, contact: Dict) -> str:
        """Create family alert message"""
        severity_emoji = {
            "minor": "⚠️",
            "moderate": "⚠️",
            "severe": "🚨",
            "critical": "🆘"
        }
        
        emoji = severity_emoji.get(incident.severity, "⚠️")
        
        message = f"""{emoji} GUARDIANRIVE ALERT {emoji}

{contact['name']}, your family member's vehicle has detected a safety concern.

Severity: {incident.severity.upper()}
Driver State: {incident.driver_state}
Location: {incident.location['lat']:.4f}, {incident.location['lng']:.4f}
Speed: {incident.vehicle_speed:.0f} km/h
Time: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(incident.timestamp))}

"""
        
        if incident.severity in ["severe", "critical"]:
            message += "⚠️ Emergency services have been notified.\n"
        
        message += "\nPlease check on them immediately.\n- GuardianDrive AI Safety System"
        
        return message
    
    def get_incident_status(self, incident_id: str) -> Optional[Dict]:
        """Get incident status"""
        if incident_id not in self.active_incidents:
            return None
        
        incident = self.active_incidents[incident_id]
        return asdict(incident)
    
    def resolve_incident(self, incident_id: str):
        """Mark incident as resolved"""
        if incident_id in self.active_incidents:
            del self.active_incidents[incident_id]
            print(f"Incident {incident_id} resolved")
