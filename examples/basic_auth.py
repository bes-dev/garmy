#!/usr/bin/env python3
"""Basic Authentication Example.

============================

This example demonstrates how to authenticate with Garmin Connect
using email and password with the new simplified API.
"""

from garmy import APIClient, AuthClient


def test_api_calls(api_client):
    """Test API calls after authentication."""
    print("\n🚀 Testing API calls...")

    try:
        # Metrics are auto-discovered when first accessed
        # Test multiple metric requests
        print("   📊 Testing Sleep data...")
        sleep_accessor = api_client.metrics.get("sleep")
        if not sleep_accessor:
            print("   ❌ Sleep metric not available")
        else:
            sleep_data = sleep_accessor.get()
            if sleep_data:
                print(f"   ✅ Sleep: {sleep_data.sleep_duration_hours:.1f} hours")
            else:
                print("   ⚪ Sleep: No data for today")

        print("   🔋 Testing Body Battery data...")
        bb_accessor = api_client.metrics.get("body_battery")
        if not bb_accessor:
            print("   ❌ Body Battery metric not available")
        else:
            bb_data = bb_accessor.get()
            if bb_data and bb_data.body_battery_readings:
                latest_reading = bb_data.body_battery_readings[-1]
                print(f"   ✅ Body Battery: {latest_reading.level}%")
            else:
                print("   ⚪ Body Battery: No data for today")

        print("   😌 Testing Stress data...")
        stress_accessor = api_client.metrics.get("stress")
        if not stress_accessor:
            print("   ❌ Stress metric not available")
        else:
            stress_data = stress_accessor.get()
            if stress_data:
                print(f"   ✅ Stress: {stress_data.avg_stress_level}/100")
            else:
                print("   ⚪ Stress: No data for today")

    except Exception as e:
        print(f"   ❌ API test failed: {e}")


def main():
    """Demonstrate basic authentication flow."""
    print("🔐 Garpy Basic Authentication Example")
    print("=" * 40)

    # Get credentials from user
    email = input("Enter your Garmin Connect email: ").strip()
    password = input("Enter your password: ").strip()

    if not email or not password:
        print("❌ Email and password are required")
        return

    try:
        print(f"\n🔄 Logging in as {email}...")

        # Create clients with new API
        auth_client = AuthClient()
        api_client = APIClient(auth_client=auth_client)

        # Attempt login
        result = auth_client.login(email, password)

        # Check if MFA is required
        if isinstance(result, tuple) and result[0] == "needs_mfa":
            print("🔑 Multi-factor authentication required")
            mfa_code = input("Enter your MFA code: ").strip()

            if mfa_code:
                # Complete MFA authentication
                auth_client.resume_login(mfa_code, result[1])
                print("✅ MFA authentication successful!")
            else:
                print("❌ MFA code required")
                return

        # Get user information
        username = api_client.username
        profile = api_client.profile

        print("\n✅ Successfully logged in!")
        print(f"👤 Username: {username}")

        if profile:
            display_name = profile.get("displayName", "Unknown")
            print(f"📝 Display Name: {display_name}")

        # Show authentication status
        print("\n🔍 Authentication Status:")
        try:
            oauth1_status = (
                "✅ Valid" if auth_client.token_manager.oauth1_token else "❌ Missing"
            )
            oauth2_status = (
                "✅ Valid"
                if (
                    auth_client.token_manager.oauth2_token
                    and not auth_client.token_manager.oauth2_token.expired
                )
                else "❌ Invalid/Expired"
            )
            print(f"   OAuth1 Token: {oauth1_status}")
            print(f"   OAuth2 Token: {oauth2_status}")
        except Exception as token_error:
            print(f"   ❌ Token status check failed: {token_error}")

        # Test API calls
        test_api_calls(api_client)

        print("\n💡 You can now use garmy with the new API:")
        print("   # Create clients")
        print("   auth = AuthClient()")
        print("   api = APIClient(auth_client=auth)")
        print("   ")
        print("   # Use metrics directly")
        print("   data = api.metrics['sleep'].get()")
        print("   weekly = api.metrics['sleep'].list(days=7)")

    except Exception as e:
        print(f"❌ Authentication failed: {e}")
        print("💡 Check your credentials and try again")


if __name__ == "__main__":
    main()
