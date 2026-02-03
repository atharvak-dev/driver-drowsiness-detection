"""
Environment Configuration Test
Verifies that .env file is properly loaded and configured
"""

from config.env_config import Config
from src.utils.gps_service import get_gps_service

def test_env_config():
    print("=" * 60)
    print("GUARDIANDRIVE AI - ENVIRONMENT CONFIGURATION TEST")
    print("=" * 60)
    
    # Test MapmyIndia API
    print("\nMapmyIndia (Mappls) API:")
    if Config.MAPPLS_API_KEY:
        print(f"   [OK] API Key: {Config.MAPPLS_API_KEY[:10]}...{Config.MAPPLS_API_KEY[-4:]}")
        print("   [OK] Status: Configured")
        
        # Test GPS service
        try:
            gps = get_gps_service()
            location = gps.get_current_location()
            print(f"   [OK] GPS Service: Working")
            print(f"   Location: {location['lat']:.4f}, {location['lng']:.4f}")
        except Exception as e:
            print(f"   [WARN] GPS Service Error: {e}")
    else:
        print("   [WARN] API Key: Not configured")
        print("   [INFO] GPS will use mock data")
    
    # Test Twilio
    print("\nTwilio SMS Service:")
    if Config.TWILIO_ACCOUNT_SID and Config.TWILIO_AUTH_TOKEN:
        print(f"   [OK] Account SID: {Config.TWILIO_ACCOUNT_SID[:10]}...")
        print("   [OK] Status: Configured")
    else:
        print("   [WARN] Status: Not configured (optional)")
        print("   [INFO] SMS alerts will be mocked")
    
    # Test Email
    print("\nEmail Service:")
    if Config.SMTP_USERNAME and Config.SMTP_PASSWORD:
        print(f"   [OK] SMTP Server: {Config.SMTP_SERVER}:{Config.SMTP_PORT}")
        print(f"   [OK] Username: {Config.SMTP_USERNAME}")
        print("   [OK] Status: Configured")
    else:
        print("   [WARN] Status: Not configured (optional)")
        print("   [INFO] Email alerts will be mocked")
    
    # Test Emergency Services
    print("\nEmergency Services:")
    if Config.POLICE_API_KEY:
        print(f"   [OK] Police API: Configured")
    else:
        print("   [WARN] Police API: Not configured (optional)")
    
    if Config.AMBULANCE_API_KEY:
        print(f"   [OK] Ambulance API: Configured")
    else:
        print("   [WARN] Ambulance API: Not configured (optional)")
    
    # Summary
    print("\n" + "=" * 60)
    print("CONFIGURATION SUMMARY")
    print("=" * 60)
    
    required_configured = bool(Config.MAPPLS_API_KEY)
    optional_count = sum([
        bool(Config.TWILIO_ACCOUNT_SID),
        bool(Config.SMTP_USERNAME),
        bool(Config.POLICE_API_KEY),
        bool(Config.AMBULANCE_API_KEY)
    ])
    
    print(f"\n[OK] Required Services: {'Configured' if required_configured else 'Missing'}")
    print(f"[INFO] Optional Services: {optional_count}/4 configured")
    
    if required_configured:
        print("\n[SUCCESS] Your GuardianDrive AI is ready to use!")
        print("   Run: python run_app.py")
    else:
        print("\n[WARN] Running in DEMO MODE")
        print("   - GPS will use mock data (Delhi coordinates)")
        print("   - All features work, but with simulated data")
        print("\n[TIP] To enable GPS features:")
        print("   1. Add MAPPLS_API_KEY to .env file")
        print("   2. See ENV_SETUP.md for details")
    
    print("\n" + "=" * 60)

if __name__ == "__main__":
    test_env_config()
