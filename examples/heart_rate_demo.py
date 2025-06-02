#!/usr/bin/env python3
"""Heart Rate Data Demo - Comprehensive Heart Rate Analysis.

========================================================

This example demonstrates how to access daily heart rate data from Garmin Connect
using the new modern API architecture.

Includes continuous readings, resting heart rate trends, and daily statistics.
Provides direct access to Garmin's wellness service data for custom analytics.

Example output:
    Date: 2025-05-28
    Resting HR: 52 bpm
    Max HR: 178 bpm
    Average HR: 82.3 bpm
    Total Readings: 1,440 measurements
"""

from datetime import datetime

from garmy import APIClient, AuthClient


def format_time(timestamp_ms):
    """Format timestamp as HH:MM."""
    return datetime.fromtimestamp(timestamp_ms / 1000).strftime("%H:%M")


def main():
    """Demonstrate modern Heart Rate data access."""
    print("❤️ Garmin Heart Rate Data Demo (Modern API)")
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
        # Get heart rate accessor using modern API
        print("🔍 Getting heart rate accessor...")
        hr_accessor = api_client.metrics.get("heart_rate")

        if not hr_accessor:
            print("❌ Heart rate metric not available")
            return

        print(f"   Accessor type: {type(hr_accessor)}")

        # Get today's heart rate data
        print("\n📊 Fetching heart rate data...")
        hr = hr_accessor.get()

        if not hr or not hr.heart_rate_values_array:
            print("❌ No heart rate data available for today")
            print("💡 Make sure you:")
            print("   - Wore your device throughout the day")
            print("   - Have a compatible Garmin device")
            print("   - Are authenticated with valid credentials")
            print("   - Try a different date: hr_accessor.get('2025-05-28')")
            return

        # Basic heart rate information
        print("\n📈 Heart Rate Summary:")
        print(f"   Date: {hr.heart_rate_summary.calendar_date}")
        print(f"   Resting Heart Rate: {hr.heart_rate_summary.resting_heart_rate} bpm")
        print(f"   Max Heart Rate: {hr.heart_rate_summary.max_heart_rate} bpm")
        print(f"   Min Heart Rate: {hr.heart_rate_summary.min_heart_rate} bpm")
        print(f"   Average Heart Rate: {hr.average_heart_rate:.1f} bpm")
        print(f"   Heart Rate Range: {hr.heart_rate_summary.heart_rate_range} bpm")
        print(f"   Total Readings: {hr.readings_count} measurements")

        print(
            f"   7-Day Average: {hr.heart_rate_summary.last_seven_days_avg_resting_heart_rate} bpm"
        )

        trend_diff = (
            hr.heart_rate_summary.resting_heart_rate
            - hr.heart_rate_summary.last_seven_days_avg_resting_heart_rate
        )
        if trend_diff > 0:
            print(f"   Current is {trend_diff} bpm higher than average")
        elif trend_diff < 0:
            print(f"   Current is {abs(trend_diff)} bpm lower than average")
        else:
            print("   Current matches the 7-day average")

        print("\n⏰ Heart Rate Timeline:")

        # Show first and last readings
        first_reading = hr.heart_rate_values_array[0]
        last_reading = hr.heart_rate_values_array[-1]

        print("   Data Period:")
        print(f"     Start: {format_time(first_reading[0])} ({first_reading[1]} bpm)")
        print(f"     End:   {format_time(last_reading[0])} ({last_reading[1]} bpm)")

        # Show sample readings throughout the day
        print(
            f"   Sample Readings (every {len(hr.heart_rate_values_array)//10} readings):"
        )
        step = max(1, len(hr.heart_rate_values_array) // 10)
        for i in range(0, len(hr.heart_rate_values_array), step):
            reading = hr.heart_rate_values_array[i]
            time_str = format_time(reading[0])
            print(f"     {time_str}: {reading[1]} bpm")

        print("\n🎆 Heart Rate Zones Analysis:")

        # Simple heart rate zone analysis (based on typical zones)
        resting = hr.heart_rate_summary.resting_heart_rate
        max_hr = hr.heart_rate_summary.max_heart_rate

        # Estimate zones (simplified)
        zone1_upper = resting + (max_hr - resting) * 0.6  # Active recovery
        zone2_upper = resting + (max_hr - resting) * 0.7  # Aerobic base
        zone3_upper = resting + (max_hr - resting) * 0.8  # Aerobic
        zone4_upper = resting + (max_hr - resting) * 0.9  # Lactate threshold

        zone_counts = {
            "Resting": 0,
            "Zone 1": 0,
            "Zone 2": 0,
            "Zone 3": 0,
            "Zone 4": 0,
            "Zone 5": 0,
        }

        for reading in hr.heart_rate_values_array:
            if len(reading) >= 2:
                hr_value = reading[1]  # Heart rate value is at index 1
                if hr_value <= resting + 10:
                    zone_counts["Resting"] += 1
                elif hr_value <= zone1_upper:
                    zone_counts["Zone 1"] += 1
                elif hr_value <= zone2_upper:
                    zone_counts["Zone 2"] += 1
                elif hr_value <= zone3_upper:
                    zone_counts["Zone 3"] += 1
                elif hr_value <= zone4_upper:
                    zone_counts["Zone 4"] += 1
                else:
                    zone_counts["Zone 5"] += 1

        total_readings = len(hr.heart_rate_values_array)
        print("   Time in Heart Rate Zones:")
        for zone, count in zone_counts.items():
            percentage = (count / total_readings) * 100
            print(f"     {zone}: {count} readings ({percentage:.1f}%)")

        print("\n🔧 Raw API Data Access:")
        print("   Available raw data fields:")
        print(
            f"   • heart_rate_values_array: {len(hr.heart_rate_values_array)} individual readings"
        )
        print(
            f"   • heart_rate_value_descriptors: "
            f"{len(hr.heart_rate_value_descriptors)} format descriptors"
        )
        print(f"   • user_profile_pk: {hr.heart_rate_summary.user_profile_pk}")
        print("   • Data timestamps: GMT and local timezone support")

        # Show raw descriptor format
        if hr.heart_rate_value_descriptors:
            print("   Raw Data Format:")
            for desc in hr.heart_rate_value_descriptors:
                print(
                    f"     Index {desc.get('index', 'N/A')}: {desc.get('key', 'N/A')}"
                )

        print("\n💡 Tip: All data comes directly from Garmin's wellness service API")
        print(
            "    Use this raw data to create your own heart rate analysis and insights"
        )

    except Exception as e:
        print(f"❌ Error retrieving heart rate data: {e}")
        print("💡 Make sure you're authenticated and have heart rate data available")


def weekly_heart_rate_trends():
    """Demonstrate accessing multiple days of heart rate data."""
    print("\n📅 Weekly Heart Rate Trends")
    print("=" * 35)

    try:
        # Create clients and factory
        auth_client = AuthClient()
        api_client = APIClient(
            auth_client=auth_client
        )  # Metrics are auto-discovered when first accessed
        hr_accessor = api_client.metrics.get("heart_rate")
        if not hr_accessor:
            print("❌ Heart rate metric not available")
            return

        # Get heart rate data for the last 7 days
        print("🚀 Fetching 7 days of heart rate data...")
        weekly_data = hr_accessor.list(days=7)

        if not weekly_data:
            print("❌ No heart rate data available for the past week")
            return

        print("   Date       | Resting | Max | Avg | Readings")
        print("   -----------|---------|-----|-----|----------")

        for hr in weekly_data:
            if (
                hr.heart_rate_summary
                and hr.heart_rate_summary.resting_heart_rate is not None
                and hr.heart_rate_summary.max_heart_rate is not None
            ):
                summary = hr.heart_rate_summary
                resting = summary.resting_heart_rate
                max_hr = summary.max_heart_rate
                avg_hr = hr.average_heart_rate
                readings = hr.readings_count

                avg_hr_str = f"{avg_hr:3.0f}" if avg_hr is not None else " - "
                readings_str = f"{readings}" if readings is not None else " - "
                print(
                    f"   {summary.calendar_date} | {resting:>7} | {max_hr:>3} | "
                    f"{avg_hr_str:>3} | {readings_str:>8}"
                )

        # Weekly insights
        if len(weekly_data) > 1:
            # Collect resting heart rates with more robust checking
            resting_hrs = []
            for hr in weekly_data:
                if (
                    hr.heart_rate_summary
                    and hasattr(hr.heart_rate_summary, "resting_heart_rate")
                    and hr.heart_rate_summary.resting_heart_rate is not None
                ):
                    resting_hrs.append(hr.heart_rate_summary.resting_heart_rate)

            if len(resting_hrs) >= 2:  # Need at least 2 days for meaningful insights
                avg_resting = sum(resting_hrs) / len(resting_hrs)
                min_resting = min(resting_hrs)
                max_resting = max(resting_hrs)

                print(f"\n📊 Weekly Resting HR Insights ({len(resting_hrs)} days):")
                print(f"   Average: {avg_resting:.1f} bpm")
                print(f"   Range: {min_resting}-{max_resting} bpm")

                if max_resting - min_resting > 10:
                    print("   ⚠️ Large variation detected - consider recovery")
                elif max_resting - min_resting < 5:
                    print("   ✅ Consistent resting HR - good recovery pattern")
                else:
                    print("   📈 Normal variation within healthy range")
            elif len(resting_hrs) == 1:
                print(
                    f"\n📊 Weekly Resting HR: {resting_hrs[0]} bpm (only 1 day available)"
                )
            else:
                print("\n📊 No resting HR data available for insights")

    except Exception as e:
        print(f"❌ Error fetching weekly heart rate data: {e}")


def raw_heart_rate_data():
    """Demonstrate accessing raw heart rate API response."""
    print("\n🔍 Raw Heart Rate API Response")
    print("=" * 40)

    try:
        # Create clients and factory
        auth_client = AuthClient()
        api_client = APIClient(
            auth_client=auth_client
        )  # Metrics are auto-discovered when first accessed
        hr_accessor = api_client.metrics.get("heart_rate")
        if not hr_accessor:
            print("❌ Heart rate metric not available")
            return

        # Get raw JSON response without any parsing
        raw_data = hr_accessor.raw()

        if raw_data:
            print("Raw API keys:", list(raw_data.keys()))

            # Show heart rate summary structure
            if "heartRateSummary" in raw_data:
                hr_summary = raw_data["heartRateSummary"]
                print(f"HR summary keys: {list(hr_summary.keys())}")
                print(f"Calendar date: {hr_summary.get('calendarDate')}")
                print(f"Resting HR: {hr_summary.get('restingHeartRate')} bpm")
                print(f"Max HR: {hr_summary.get('maxHeartRate')} bpm")

            # Show heart rate values structure
            if "heartRateValuesArray" in raw_data:
                hr_values = raw_data["heartRateValuesArray"]
                print(f"\nHR readings: {len(hr_values)} measurements")
                if len(hr_values) > 0:
                    print(f"First reading format: {hr_values[0]}")
                    print("Reading structure: [timestamp_ms, heart_rate_bpm]")

            # Show descriptors
            if "heartRateValueDescriptors" in raw_data:
                descriptors = raw_data["heartRateValueDescriptors"]
                print(f"Value descriptors: {descriptors}")
        else:
            print("❌ No raw data available")

    except Exception as e:
        print(f"❌ Error fetching raw heart rate data: {e}")


if __name__ == "__main__":
    # Run all demos
    main()
    weekly_heart_rate_trends()
    raw_heart_rate_data()

    print("\n💡 Modern API Notes:")
    print("   • Explicit client creation: AuthClient() and APIClient()")
    print("   • Use api_client.metrics for direct metric access")
    print("   • Heart Rate uses standard MetricAccessor")
    print("   • Methods: .get(), .list(), .raw()")
    print("   • Direct class imports: from garmy import HeartRate")
