#!/usr/bin/env python3
"""Stress Data Demo - Stress Level Analysis.

=======================================

This example demonstrates how to access stress level data from the
Garmin Connect API using the new modern API architecture.

Stress tracking monitors your body's stress response throughout the day
using heart rate variability analysis from compatible Garmin devices.

Example output:
    Date: 2025-05-29
    Average stress: 32
    Max stress: 67
    Total readings: 142
"""


from garmy import APIClient, AuthClient


def main():
    """Demonstrate modern Stress data access."""
    print("😰 Garmin Stress Data Demo (Modern API)")
    print("=" * 50)

    # Create clients explicitly
    print("🔧 Creating Garpy clients...")
    auth_client = AuthClient()
    api_client = APIClient(auth_client=auth_client)
    # Metrics are auto-discovered when first accessed
    # Authenticate (you'll need to implement your preferred auth method)
    print("📱 To access data, authenticate first:")
    print("   auth_client.login('your_email@example.com', 'your_password')")
    print()

    try:
        # Get stress accessor using modern API
        print("🔍 Getting stress accessor...")
        stress_accessor = api_client.metrics.get("stress")

        if not stress_accessor:
            print("❌ Stress metric not available")
            return

        print(f"   Accessor type: {type(stress_accessor)}")

        # Get today's stress data
        print("\n📊 Fetching today's stress data...")
        stress = stress_accessor.get()

        if not stress:
            print("❌ No stress data available for today")
            print("💡 Make sure you:")
            print("   - Wore your device throughout the day")
            print("   - Have a compatible Garmin device with stress tracking")
            print("   - Device has heart rate monitoring enabled")
            print("   - Are authenticated with valid credentials")
            return

        # Display raw stress summary
        print("\n📈 Stress Summary (from Garmin API):")
        print(f"   Date: {stress.calendar_date}")
        print(f"   User Profile: {stress.user_profile_pk}")
        print(f"   Average stress: {stress.avg_stress_level}")
        print(f"   Maximum stress: {stress.max_stress_level}")
        print(f"   Total readings: {len(stress.stress_readings)}")

        # Display readings sample
        if stress.stress_readings:
            current_reading = stress.stress_readings[-1]

            print("\n📊 Current Status:")
            print(f"   Level: {current_reading.stress_level}")
            print(f"   Category: {current_reading.stress_category}")
            print(f"   Time: {current_reading.datetime.strftime('%H:%M:%S')}")
            # Using direct comparison instead of removed property
            is_rest = current_reading.stress_level == -1
            print(f"   Is rest period: {is_rest}")

            # Show sample readings
            print("\n📋 Sample Readings:")
            print("   Time     | Level | Category")
            print("   ---------|-------|----------")

            # Show every 20th reading or sample if too many
            sample_readings = (
                stress.stress_readings[::20]
                if len(stress.stress_readings) > 20
                else stress.stress_readings
            )

            for reading in sample_readings[:10]:  # Limit to 10 for display
                time_str = reading.datetime.strftime("%H:%M")
                reading_is_rest = reading.stress_level == -1
                level_str = "Rest" if reading_is_rest else f"{reading.stress_level:2d}"
                print(f"   {time_str}     | {level_str:5s} | {reading.stress_category}")

            if len(stress.stress_readings) > 20:
                print(
                    f"   ... ({len(stress.stress_readings) - len(sample_readings)} "
                    f"more readings) ..."
                )

        # Basic statistics (user can implement their own)
        if stress.stress_readings:
            # Count by category
            category_counts = {}
            stress_levels = []

            for reading in stress.stress_readings:
                category = reading.stress_category
                category_counts[category] = category_counts.get(category, 0) + 1

                # Using direct comparison instead of removed property
                if reading.stress_level != -1:
                    stress_levels.append(reading.stress_level)

            print("\n📊 Category Distribution (calculated from raw data):")
            for category, count in category_counts.items():
                percentage = (count / len(stress.stress_readings)) * 100
                print(f"   {category}: {count} readings ({percentage:.1f}%)")

            if stress_levels:
                print("\n📈 Active Period Statistics:")
                print(f"   Min stress: {min(stress_levels)}")
                print(f"   Max stress: {max(stress_levels)}")
                print(f"   Range: {max(stress_levels) - min(stress_levels)}")
                print(f"   Active readings: {len(stress_levels)}")

                # High stress periods
                high_stress_count = sum(1 for level in stress_levels if level > 60)
                if high_stress_count > 0:
                    print(f"   High stress periods (>60): {high_stress_count}")

    except Exception as e:
        print(f"❌ Error fetching stress data: {e}")
        print("💡 Make sure you're authenticated and have stress data available")


def weekly_stress_data():
    """Demonstrate accessing multiple days of stress data."""
    print("\n📅 Weekly Stress Trends")
    print("=" * 30)

    try:
        # Create clients and factory
        auth_client = AuthClient()
        api_client = APIClient(
            auth_client=auth_client
        )  # Metrics are auto-discovered when first accessed
        stress_accessor = api_client.metrics.get("stress")
        if not stress_accessor:
            print("❌ Stress metric not available")
            return

        # Get stress data for the last 7 days
        print("🚀 Fetching 7 days of stress data...")
        weekly_data = stress_accessor.list(days=7)

        if not weekly_data:
            print("❌ No stress data available for the past week")
            return

        print("   Date       | Avg | Max | Readings | Rest %")
        print("   -----------|----|-----|----------|--------")

        for stress in weekly_data:
            if stress.stress_readings:
                # Using direct comparison instead of removed property
                rest_count = sum(
                    1 for r in stress.stress_readings if r.stress_level == -1
                )
                rest_percentage = (rest_count / len(stress.stress_readings)) * 100

                print(
                    f"   {stress.calendar_date} | {stress.avg_stress_level:2d}  | "
                    f"{stress.max_stress_level:2d}  | {len(stress.stress_readings):8d} | "
                    f"{rest_percentage:5.1f}%"
                )
            else:
                print(f"   {stress.calendar_date} | No data available")

        # Weekly insights
        if len(weekly_data) > 1:
            avg_stress_levels = [
                s.avg_stress_level
                for s in weekly_data
                if s.avg_stress_level is not None
            ]
            if avg_stress_levels:
                weekly_avg = sum(avg_stress_levels) / len(avg_stress_levels)
                print("\n📊 Weekly Insights:")
                print(f"   Average stress level: {weekly_avg:.1f}")

                high_stress_days = sum(1 for level in avg_stress_levels if level > 50)
                if high_stress_days > 0:
                    print(f"   ⚠️ High stress days: {high_stress_days}")
                else:
                    print("   ✅ Manageable stress levels throughout the week")

    except Exception as e:
        print(f"❌ Error fetching weekly stress data: {e}")


def raw_api_data():
    """Demonstrate accessing completely raw API response."""
    print("\n🔍 Raw Stress API Response")
    print("=" * 35)

    try:
        # Create clients and factory
        auth_client = AuthClient()
        api_client = APIClient(
            auth_client=auth_client
        )  # Metrics are auto-discovered when first accessed
        # Get raw JSON response without any parsing
        stress_accessor = api_client.metrics.get("stress")
        if not stress_accessor:
            print("❌ Stress metric not available")
            return

        raw_data = stress_accessor.raw()

        if raw_data:
            print("Raw API keys:", list(raw_data.keys()))
            print(f"Calendar date: {raw_data.get('calendarDate')}")
            print(f"User Profile PK: {raw_data.get('userProfilePk')}")
            print(f"Average stress: {raw_data.get('avgStressLevel')}")
            print(f"Max stress: {raw_data.get('maxStressLevel')}")

            stress_values = raw_data.get("stressValuesArray", [])
            print(f"Raw stress values count: {len(stress_values)}")
            if stress_values:
                print(f"First reading raw: {stress_values[0]}")
                print("Raw format: [timestamp, stress_level]")
        else:
            print("❌ No raw data available")

    except Exception as e:
        print(f"❌ Error fetching raw data: {e}")


def stress_correlation_analysis():
    """Demonstrate stress correlation analysis with other metrics."""
    print("\n🔗 Stress Correlation Analysis")
    print("=" * 35)

    try:
        # Create clients and factory
        auth_client = AuthClient()
        api_client = APIClient(
            auth_client=auth_client
        )  # Metrics are auto-discovered when first accessed
        # Fetch multiple related metrics
        print("🚀 Fetching stress, HRV, and sleep data...")

        # Get metric accessors
        stress_accessor = api_client.metrics.get("stress")
        hrv_accessor = api_client.metrics.get("hrv")
        sleep_accessor = api_client.metrics.get("sleep")

        # Execute data fetching
        stress_data = stress_accessor.get() if stress_accessor else None
        hrv_data = hrv_accessor.get() if hrv_accessor else None
        sleep_data = sleep_accessor.get() if sleep_accessor else None

        print("\n📊 Cross-metric Analysis:")

        # Stress analysis
        if not isinstance(stress_data, Exception) and stress_data:
            print(
                f"   Stress: Avg {stress_data.avg_stress_level}, Max {stress_data.max_stress_level}"
            )
        else:
            print("   Stress: No data or error")

        # HRV analysis
        if not isinstance(hrv_data, Exception) and hrv_data:
            print(
                f"   HRV: Status {hrv_data.hrv_summary.status}, "
                f"Avg {hrv_data.hrv_summary.last_night_avg}ms"
            )
        else:
            print("   HRV: No data or error")

        # Sleep analysis
        if not isinstance(sleep_data, Exception) and sleep_data:
            print(
                f"   Sleep: {sleep_data.sleep_duration_hours:.1f}h, "
                f"Stress {sleep_data.sleep_summary.avg_sleep_stress}"
            )
        else:
            print("   Sleep: No data or error")

        # Simple correlation insight
        if (
            not isinstance(stress_data, Exception)
            and stress_data
            and not isinstance(hrv_data, Exception)
            and hrv_data
        ):
            print("\n💡 Quick Insight:")
            if stress_data.avg_stress_level > 40 and hrv_data.hrv_summary.status in [
                "UNBALANCED",
                "LOW",
            ]:
                print("   High stress correlates with poor HRV status")
            else:
                print("   Stress and HRV levels appear balanced")

    except Exception as e:
        print(f"❌ Correlation analysis failed: {e}")


if __name__ == "__main__":
    # Run all demos
    main()
    weekly_stress_data()
    raw_api_data()
    stress_correlation_analysis()

    print("\n💡 Modern API Notes:")
    print("   • Explicit client creation: AuthClient() and APIClient()")
    print("   • Use api_client.metrics for direct metric access")
    print("   • Stress uses standard MetricAccessor")
    print("   • Methods: .get(), .list(), .raw()")
    print("   • Direct class imports: from garmy import Stress")
    print("\n💡 Data Analysis Notes:")
    print("   • All data comes directly from Garmin Connect API")
    print(
        "   • Stress levels: -1 (rest), 0-24 (low), 25-49 (medium), 50-74 (high), 75+ (very high)"
    )
    print("   • Measurements based on heart rate variability")
    print("   • Timestamps are Unix time in milliseconds")
    print("   • Use this raw data for your own stress analysis")
