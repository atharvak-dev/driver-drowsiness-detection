"""
Twilio SMS Alert Service
Sends real SMS alerts to emergency contacts
"""

from typing import Dict, List, Optional
from config.env_config import Config

class TwilioSMSService:
    def __init__(self):
        self.account_sid = Config.TWILIO_ACCOUNT_SID
        self.auth_token = Config.TWILIO_AUTH_TOKEN
        self.phone_number = Config.TWILIO_PHONE_NUMBER
        self.messaging_service_sid = Config.TWILIO_MESSAGING_SERVICE_SID
        self.enabled = bool(self.account_sid and self.auth_token)
        
        if self.enabled:
            try:
                from twilio.rest import Client
                self.client = Client(self.account_sid, self.auth_token)
            except ImportError:
                print("⚠️  Twilio library not installed. Run: pip install twilio")
                self.enabled = False
    
    def send_sms(self, to_number: str, message: str) -> Dict:
        """Send SMS to a phone number"""
        if not self.enabled:
            return {"status": "disabled", "message": "Twilio not configured"}
        
        try:
            # Use messaging service if available, otherwise use phone number
            if self.messaging_service_sid:
                msg = self.client.messages.create(
                    to=to_number,
                    messaging_service_sid=self.messaging_service_sid,
                    body=message
                )
            else:
                msg = self.client.messages.create(
                    to=to_number,
                    from_=self.phone_number,
                    body=message
                )
            
            return {
                "status": "sent",
                "sid": msg.sid,
                "to": to_number,
                "message": message[:50] + "..."
            }
        except Exception as e:
            return {
                "status": "failed",
                "error": str(e),
                "to": to_number
            }
    
    def send_alert(self, contacts: List[Dict], alert_message: str) -> List[Dict]:
        """Send alert to multiple contacts"""
        results = []
        for contact in contacts:
            result = self.send_sms(contact['phone'], alert_message)
            result['contact_name'] = contact['name']
            results.append(result)
        return results

# Singleton instance
_sms_service = None

def get_sms_service() -> TwilioSMSService:
    """Get SMS service singleton"""
    global _sms_service
    if _sms_service is None:
        _sms_service = TwilioSMSService()
    return _sms_service
