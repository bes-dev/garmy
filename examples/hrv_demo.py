#!/usr/bin/env python3
"""HRV Data Demo - Heart Rate Variability Analysis.

===============================================

This example demonstrates how to access HRV (Heart Rate Variability) data
from the Garmin Connect API using the new modern API architecture.

Provides clean access to raw Garmin data, allowing you to perform your own
analysis and interpretation based on your specific needs.

Example output:
    Status: UNBALANCED
    Last night average: 52ms
    Weekly average: 48ms
    Total readings: 78
"""


from garmy import APIClient, AuthClient


def main():
    """Demonstrate modern HRV data access."""
    print("🫀 Garmin HRV Data Demo (Modern API)")
    print("=" * 45)

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
        # Get HRV accessor using modern API
        print("🔍 Getting HRV accessor...")
        hrv_accessor = api_client.metrics.get("hrv")

        if not hrv_accessor:
            print("❌ HRV metric not available")
            return

        print(f"   Accessor type: {type(hrv_accessor)}")

        # Get today's HRV data
        print("\n📊 Fetching today's HRV data...")
        hrv = hrv_accessor.get()

        if not hrv:
            print("❌ No HRV data available for today")
            print("💡 Make sure you:")
            print("   - Wore your device during sleep")
            print("   - Got at least 4 hours of sleep")
            print("   - Have a compatible Garmin device")
            print("   - Are authenticated with valid credentials")
            return

        # Display raw HRV summary data
        print("\n📈 HRV Summary (from Garmin API):")
        print(f"   Date: {hrv.hrv_summary.calendar_date}")
        print(f"   Status: {hrv.hrv_summary.status}")
        print(f"   Last Night Average: {hrv.hrv_summary.last_night_avg}ms")
        print(f"   Weekly Average: {hrv.hrv_summary.weekly_avg}ms")
        print(f"   Peak 5-min Reading: {hrv.hrv_summary.last_night_5_min_high}ms")
        print(f"   Feedback Phrase: {hrv.hrv_summary.feedback_phrase}")

        # Display baseline data
        baseline = hrv.hrv_summary.baseline
        print("\n📏 Baseline Values:")
        print(f"   Low Upper: {baseline.low_upper}ms")
        print(f"   Balanced Range: {baseline.balanced_low}-{baseline.balanced_upper}ms")
        print(f"   Marker Value: {baseline.marker_value:.3f}")

        # Display raw readings sample
        readings_count = len(hrv.hrv_readings)
        print(f"\n📋 Individual Readings ({readings_count} total):")
        if readings_count > 0:
            print("   Time (Local)     | HRV Value")
            print("   -----------------|----------")

            # Show first 5 and last 5 readings
            sample_readings = (
                hrv.hrv_readings[:5] + hrv.hrv_readings[-5:]
                if readings_count > 10
                else hrv.hrv_readings
            )

            for reading in sample_readings:
                time_str = reading.datetime_local.strftime("%H:%M:%S")
                print(f"   {time_str}        | {reading.hrv_value:3d}ms")

            if readings_count > 10:
                print(f"   ... ({readings_count - 10} more readings) ...")

        # Simple statistics (user can implement their own)
        if hrv.hrv_readings:
            values = [r.hrv_value for r in hrv.hrv_readings]
            min_val = min(values)
            max_val = max(values)
            mean_val = sum(values) / len(values)

            print("\n📊 Basic Statistics (calculated from raw data):")
            print(f"   Min: {min_val}ms")
            print(f"   Max: {max_val}ms")
            print(f"   Mean: {mean_val:.1f}ms")
            print(f"   Range: {max_val - min_val}ms")

        # Show timestamp data
        print("\n⏰ Sleep Period Timestamps:")
        if hrv.sleep_start_timestamp_local:
            print(f"   Sleep Start (Local): {hrv.sleep_start_timestamp_local}")
        if hrv.sleep_end_timestamp_local:
            print(f"   Sleep End (Local): {hrv.sleep_end_timestamp_local}")
        if hrv.start_timestamp_local:
            print(f"   Recording Start: {hrv.start_timestamp_local}")
        if hrv.end_timestamp_local:
            print(f"   Recording End: {hrv.end_timestamp_local}")

    except Exception as e:
        print(f"❌ Error fetching HRV data: {e}")
        print("💡 Make sure you're authenticated and have HRV data available")


def weekly_hrv_data():
    """Demonstrate accessing multiple days of HRV data."""
    print("\n📅 Weekly HRV Data")
    print("=" * 25)

    try:
        # Create clients and factory
        auth_client = AuthClient()
        api_client = APIClient(
            auth_client=auth_client
        )  # Metrics are auto-discovered when first accessed
        # Get HRV data for the last 7 days
        hrv_accessor = api_client.metrics.get("hrv")
        if not hrv_accessor:
            print("❌ HRV metric not available")
            return

        print("🚀 Fetching 7 days of HRV data...")
        weekly_data = hrv_accessor.list(days=7)

        if not weekly_data:
            print("❌ No HRV data available for the past week")
            return

        print("   Date       | Status      | Avg HRV | Weekly Avg")
        print("   -----------|-------------|---------|------------")

        for hrv in weekly_data:
            date_str = hrv.hrv_summary.calendar_date
            status = hrv.hrv_summary.status
            last_night = hrv.hrv_summary.last_night_avg
            weekly_avg = hrv.hrv_summary.weekly_avg

            print(
                f"   {date_str} | {status:11s} | {last_night:3d}ms   | {weekly_avg:3d}ms"
            )

    except Exception as e:
        print(f"❌ Error fetching weekly HRV data: {e}")


def raw_api_data():
    """Demonstrate accessing completely raw API response."""
    print("\n🔍 Raw HRV API Response")
    print("=" * 30)

    try:
        # Create clients and factory
        auth_client = AuthClient()
        api_client = APIClient(
            auth_client=auth_client
        )  # Metrics are auto-discovered when first accessed
        # Get raw JSON response without any parsing
        hrv_accessor = api_client.metrics.get("hrv")
        if not hrv_accessor:
            print("❌ HRV metric not available")
            return

        raw_data = hrv_accessor.raw()

        if raw_data:
            print("Raw API keys:", list(raw_data.keys()))
            print(f"User Profile PK: {raw_data.get('userProfilePk')}")

            hrv_summary = raw_data.get("hrvSummary", {})
            print(f"Raw HRV Summary keys: {list(hrv_summary.keys())}")
            print(f"Calendar date: {hrv_summary.get('calendarDate')}")
            print(f"Status: {hrv_summary.get('status')}")
            print(f"Last night avg: {hrv_summary.get('lastNightAvg')}ms")

            readings = raw_data.get("hrvReadings", [])
            print(f"\nRaw readings count: {len(readings)}")
            if readings:
                print(f"First reading structure: {list(readings[0].keys())}")
                print(
                    f"First reading: timestamp={readings[0].get('readingTimeLocal')}, "
                    f"value={readings[0].get('hrvValue')}ms"
                )
        else:
            print("❌ No raw data available")

    except Exception as e:
        print(f"❌ Error fetching raw HRV data: {e}")


def hrv_status_analysis():
    """Demonstrate HRV status analysis over time."""
    print("\n📊 HRV Status Analysis")
    print("=" * 30)

    try:
        # Create clients and factory
        auth_client = AuthClient()
        api_client = APIClient(
            auth_client=auth_client
        )  # Metrics are auto-discovered when first accessed
        hrv_accessor = api_client.metrics.get("hrv")
        if not hrv_accessor:
            print("❌ HRV metric not available")
            return

        # Get multiple days of data for trend analysis
        print("🚀 Fetching HRV trend data...")
        trend_data = hrv_accessor.list(days=14)

        if not trend_data:
            print("❌ No HRV trend data available")
            return

        # Analyze status patterns
        status_counts = {}
        total_days = len(trend_data)

        for hrv in trend_data:
            status = hrv.hrv_summary.status
            status_counts[status] = status_counts.get(status, 0) + 1

        print(f"\n📈 HRV Status Distribution (last {total_days} days):")
        for status, count in sorted(
            status_counts.items(), key=lambda x: x[1], reverse=True
        ):
            percentage = (count / total_days) * 100
            print(f"   {status}: {count} days ({percentage:.1f}%)")

        # Show recent trend
        if len(trend_data) >= 3:
            recent_statuses = [hrv.hrv_summary.status for hrv in trend_data[:3]]
            print(f"\n🕰️ Recent Trend (last 3 days): {' → '.join(recent_statuses)}")

            # Simple trend analysis
            balanced_count = sum(
                1 for status in recent_statuses if status == "BALANCED"
            )
            if balanced_count >= 2:
                print("   ✅ Good recovery pattern")
            elif balanced_count == 0:
                print("   ⚠️ Consider recovery focus")
            else:
                print("   📈 Mixed recovery pattern")

    except Exception as e:
        print(f"❌ Error in HRV status analysis: {e}")


if __name__ == "__main__":
    # Run all demos
    main()
    weekly_hrv_data()
    raw_api_data()
    hrv_status_analysis()

    print("\n💡 Modern API Notes:")
    print("   • Explicit client creation: AuthClient() and APIClient()")
    print("   • Use api_client.metrics for direct metric access")
    print("   • HRV uses standard MetricAccessor")
    print("   • Methods: .get(), .list(), .raw()")
    print("   • Direct class imports: from garmy import HRV")
    print("\n💡 Data Analysis Notes:")
    print("   • All data comes directly from Garmin Connect API")
    print("   • Status values: BALANCED, UNBALANCED, POOR, etc.")
    print("   • HRV values are in milliseconds")
    print("   • Baseline ranges are personalized by Garmin")
    print("   • Use this raw data for your own analysis and insights")
