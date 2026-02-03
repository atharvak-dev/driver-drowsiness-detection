"""
Test Twilio SMS Integration
Sends a test message to verify configuration
"""

from config.env_config import Config
from src.utils.sms_service import get_sms_service

def test_twilio():
    print("=" * 60)
    print("TWILIO SMS SERVICE TEST")
    print("=" * 60)
    
    # Check configuration
    print("\nConfiguration:")
    print(f"  Account SID: {Config.TWILIO_ACCOUNT_SID[:10] if Config.TWILIO_ACCOUNT_SID else 'Not set'}...")
    print(f"  Phone Number: {Config.TWILIO_PHONE_NUMBER or 'Not set'}")
    print(f"  Messaging Service: {Config.TWILIO_MESSAGING_SERVICE_SID[:10] if Config.TWILIO_MESSAGING_SERVICE_SID else 'Not set'}...")
    
    # Initialize service
    sms_service = get_sms_service()
    
    if not sms_service.enabled:
        print("\n⚠️  Twilio not configured or library not installed")
        print("\nTo enable:")
        print("  1. Add credentials to .env file")
        print("  2. Run: pip install twilio")
        return
    
    print("\n✅ Twilio service initialized")
    
    # Test message
    test_number = input("\nEnter phone number to test (e.g., +919518377949): ").strip()
    if not test_number:
        print("No number provided. Skipping test.")
        return
    
    print(f"\nSending test message to {test_number}...")
    
    result = sms_service.send_sms(
        to_number=test_number,
        message="🚗 GuardianDrive AI Test Alert\n\nThis is a test message from your driver safety system. If you receive this, SMS alerts are working correctly!"
    )
    
    print("\nResult:")
    print(f"  Status: {result['status']}")
    if result['status'] == 'sent':
        print(f"  Message SID: {result['sid']}")
        print("  ✅ SMS sent successfully!")
    else:
        print(f"  Error: {result.get('error', 'Unknown error')}")
    
    print("\n" + "=" * 60)

if __name__ == "__main__":
    test_twilio()
