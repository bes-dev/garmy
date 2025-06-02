#!/usr/bin/env python3
"""Respiration Data Demo - Respiratory Rate Analysis.

=================================================

This example demonstrates how to access daily respiration data from Garmin Connect
using the new modern API architecture.

Includes continuous readings, averaged periods, sleep vs waking patterns,
and detailed temporal analysis.

Example output:
    Waking Avg: 14 bpm
    Sleep Avg: 12 bpm
    Range: 8-22 bpm
    Valid Readings: 1,234 measurements
"""

from datetime import datetime

from garmy import APIClient, AuthClient


def format_time(timestamp_ms):
    """Format timestamp as HH:MM."""
    return datetime.fromtimestamp(timestamp_ms / 1000).strftime("%H:%M")


def main():
    """Demonstrate modern Respiration data access."""
    print("🌬️ Garmin Respiration Data Demo (Modern API)")
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
        # Get respiration accessor using modern API
        print("🔍 Getting respiration accessor...")
        resp_accessor = api_client.metrics.get("respiration")

        if not resp_accessor:
            print("❌ Respiration metric not available")
            return

        print(f"   Accessor type: {type(resp_accessor)}")

        # Get today's respiration data
        print("\n📊 Fetching today's respiration data...")
        resp = resp_accessor.get()

        if not resp or not resp.respiration_values_array:
            print("❌ No respiration data available for today")
            print("💡 Make sure you:")
            print("   - Have a compatible Garmin device with respiration tracking")
            print("   - Wore your device throughout the day")
            print("   - Are authenticated with valid credentials")
            print("   - Try a different date: resp_accessor.get('2025-05-28')")
            return

        # Basic respiration information
        print("\n🌬️ Respiration Summary:")
        print(f"   Date: {resp.respiration_summary.calendar_date}")
        print(
            f"   Waking Avg: {resp.respiration_summary.avg_waking_respiration_value} bpm"
        )
        print(
            f"   Sleep Avg: {resp.respiration_summary.avg_sleep_respiration_value} bpm"
        )
        print(f"   Highest: {resp.respiration_summary.highest_respiration_value} bpm")
        print(f"   Lowest: {resp.respiration_summary.lowest_respiration_value} bpm")
        print(f"   Range: {resp.respiration_summary.respiration_range} bpm")
        print(f"   Total Readings: {resp.readings_count} measurements")
        print(f"   Valid Readings: {resp.valid_readings_count} measurements")

        print(
            f"\n🔄 Waking vs Sleep Difference: "
            f"{resp.respiration_summary.waking_vs_sleep_difference} bpm"
        )
        if resp.respiration_summary.waking_vs_sleep_difference > 0:
            print(
                f"   Waking respiration is "
                f"{resp.respiration_summary.waking_vs_sleep_difference} bpm higher than sleep"
            )
        elif resp.respiration_summary.waking_vs_sleep_difference < 0:
            print(
                f"   Sleep respiration is "
                f"{abs(resp.respiration_summary.waking_vs_sleep_difference)} bpm higher than waking"
            )
        else:
            print("   Waking and sleep respiration rates are equal")

        print("\n" + "─" * 60)
        print("RESPIRATION TIMELINE")
        print("─" * 60)

        # Show sleep periods
        if (
            resp.respiration_summary.sleep_start_datetime_local
            and resp.respiration_summary.sleep_end_datetime_local
        ):
            print("😴 Sleep Period:")
            print(
                f"   Start: {resp.respiration_summary.sleep_start_datetime_local.strftime('%H:%M')}"
            )
            print(
                f"   End:   {resp.respiration_summary.sleep_end_datetime_local.strftime('%H:%M')}"
            )

            if (
                resp.respiration_summary.sleep_start_datetime_local
                and resp.respiration_summary.sleep_end_datetime_local
            ):
                sleep_duration = (
                    resp.respiration_summary.sleep_end_datetime_local
                    - resp.respiration_summary.sleep_start_datetime_local
                )
                hours = sleep_duration.total_seconds() / 3600
                print(f"   Duration: {hours:.1f} hours")
            else:
                print("   Duration: Unable to calculate (missing timestamps)")

        # Show first and last valid readings
        valid_readings = [
            r for r in resp.respiration_values_array if len(r) >= 2 and r[1] != -1
        ]
        if valid_readings:
            first_reading = valid_readings[0]
            last_reading = valid_readings[-1]

            print("\n⏰ Data Period:")
            print(f"   Start: {format_time(first_reading[0])} ({first_reading[1]} bpm)")
            print(f"   End:   {format_time(last_reading[0])} ({last_reading[1]} bpm)")

        # Show sample readings throughout the day
        print(f"\n📊 Sample Valid Readings (every {len(valid_readings)//10} readings):")
        step = max(1, len(valid_readings) // 10)
        for i in range(0, len(valid_readings), step):
            reading = valid_readings[i]
            time_str = format_time(reading[0])
            print(f"   {time_str}: {reading[1]} bpm")

        print("\n" + "─" * 60)
        print("RESPIRATION AVERAGES ANALYSIS")
        print("─" * 60)

        # Show averaged data periods
        if resp.respiration_averages_values_array:
            print(f"📈 Averaged Periods: {resp.averages_count} periods")
            print("\n🕐 Hourly Averages:")

            for avg in resp.respiration_averages_values_array:
                if len(avg) >= 4:
                    time_str = format_time(avg[0])
                    avg_val, high_val, low_val = avg[1], avg[2], avg[3]
                    if high_val is not None and low_val is not None:
                        span = high_val - low_val
                        print(
                            f"   {time_str}: {avg_val:.1f} bpm "
                            f"(range: {low_val}-{high_val}, "
                            f"span: {span} bpm)"
                        )
                    else:
                        print(
                            f"   {time_str}: {avg_val:.1f} bpm "
                            f"(range data unavailable)"
                        )
        else:
            print("No averaged respiration data available")

        print("\n" + "─" * 60)
        print("RESPIRATION PATTERNS")
        print("─" * 60)

        # Analyze patterns in valid readings
        if valid_readings:
            # Group readings by ranges
            ranges = {
                "Very Low (≤10 bpm)": 0,
                "Low (11-13 bpm)": 0,
                "Normal (14-16 bpm)": 0,
                "High (17-19 bpm)": 0,
                "Very High (≥20 bpm)": 0,
            }

            for reading in valid_readings:
                value = reading[1]  # Respiration value is at index 1
                if value <= 10:
                    ranges["Very Low (≤10 bpm)"] += 1
                elif value <= 13:
                    ranges["Low (11-13 bpm)"] += 1
                elif value <= 16:
                    ranges["Normal (14-16 bpm)"] += 1
                elif value <= 19:
                    ranges["High (17-19 bpm)"] += 1
                else:
                    ranges["Very High (≥20 bpm)"] += 1

            total_valid = len(valid_readings)
            print("💨 Respiration Distribution:")
            for range_name, count in ranges.items():
                percentage = (count / total_valid) * 100
                print(f"   {range_name}: {count} readings ({percentage:.1f}%)")

        print("\n" + "─" * 60)
        print("DATA QUALITY ANALYSIS")
        print("─" * 60)

        # Analyze data quality
        invalid_count = resp.readings_count - resp.valid_readings_count
        valid_percentage = (resp.valid_readings_count / resp.readings_count) * 100

        print("📊 Data Quality:")
        print(
            f"   Valid readings: {resp.valid_readings_count} ({valid_percentage:.1f}%)"
        )
        print(f"   Invalid readings: {invalid_count} ({100-valid_percentage:.1f}%)")

        if invalid_count > 0:
            print(
                "   Note: Invalid readings (-1) indicate measurement gaps or sensor issues"
            )

        print("\n" + "─" * 60)
        print("RAW API DATA ACCESS")
        print("─" * 60)

        print("🔧 Available raw data fields:")
        print(
            f"   • respiration_values_array: "
            f"{len(resp.respiration_values_array)} individual readings"
        )
        print(
            f"   • respiration_averages_values_array: "
            f"{len(resp.respiration_averages_values_array)} averaged periods"
        )
        print(
            f"   • respiration_value_descriptors_dto_list: "
            f"{len(resp.respiration_value_descriptors_dto_list)} format descriptors"
        )
        print(
            f"   • respiration_version: {resp.respiration_summary.respiration_version}"
        )
        print("   • Sleep timestamps: GMT and local timezone support")

        # Show raw descriptor formats
        if resp.respiration_value_descriptors_dto_list:
            print("\n📋 Readings Data Format:")
            for desc in resp.respiration_value_descriptors_dto_list:
                print(f"   Index {desc.get('index', 'N/A')}: {desc.get('key', 'N/A')}")

        if resp.respiration_averages_value_descriptor_dto_list:
            print("\n📋 Averages Data Format:")
            for desc in resp.respiration_averages_value_descriptor_dto_list:
                index = desc.get("respiration_averages_value_descriptor_index", "N/A")
                key = desc.get("respiration_averages_value_description_key", "N/A")
                print(f"   Index {index}: {key}")

        print("\n💡 Tip: All data comes directly from Garmin's wellness service API")
        print(
            "    Use this raw data to create your own respiration analysis and insights"
        )

    except Exception as e:
        print(f"❌ Error retrieving respiration data: {e}")
        print("💡 Make sure you're authenticated and have respiration data available")


def weekly_respiration_trends():
    """Demonstrate weekly respiration trends analysis."""
    print("\n📅 Weekly Respiration Trends")
    print("=" * 35)

    try:
        # Create clients and factory
        auth_client = AuthClient()
        api_client = APIClient(
            auth_client=auth_client
        )  # Metrics are auto-discovered when first accessed
        resp_accessor = api_client.metrics.get("respiration")
        if not resp_accessor:
            print("❌ Respiration metric not available")
            return

        # Get respiration data for the last 7 days
        print("🚀 Fetching 7 days of respiration data...")
        weekly_data = resp_accessor.list(days=7)

        if not weekly_data:
            print("❌ No weekly respiration data available")
            return

        print("   Date       | Waking | Sleep | Range | Valid%")
        print("   -----------|--------|-------|-------|-------")

        for resp in weekly_data:
            if resp.respiration_summary:
                summary = resp.respiration_summary
                waking = summary.avg_waking_respiration_value
                sleep = summary.avg_sleep_respiration_value
                range_val = summary.respiration_range
                valid_pct = (
                    (resp.valid_readings_count / resp.readings_count * 100)
                    if resp.readings_count > 0
                    else 0
                )

                print(
                    f"   {summary.calendar_date} | {waking:>6} | {sleep:>5} | "
                    f"{range_val:>5} | {valid_pct:>5.1f}%"
                )

        # Weekly insights
        valid_summaries = [
            r.respiration_summary for r in weekly_data if r.respiration_summary
        ]
        if len(valid_summaries) > 1:
            waking_values = [
                s.avg_waking_respiration_value
                for s in valid_summaries
                if s.avg_waking_respiration_value is not None
            ]
            sleep_values = [
                s.avg_sleep_respiration_value
                for s in valid_summaries
                if s.avg_sleep_respiration_value is not None
            ]

            if waking_values and sleep_values:
                avg_waking = sum(waking_values) / len(waking_values)
                avg_sleep = sum(sleep_values) / len(sleep_values)

                print("\n📊 Weekly Averages:")
                print(f"   Waking: {avg_waking:.1f} bpm")
                print(f"   Sleep: {avg_sleep:.1f} bpm")
                print(f"   Difference: {avg_waking - avg_sleep:.1f} bpm")

                if avg_waking - avg_sleep > 3:
                    print("   💤 Good sleep respiration efficiency")
                else:
                    print("   ⚖️ Stable respiration patterns")
            else:
                print("\n📊 Weekly Averages:")
                print("   Insufficient data for weekly analysis")

    except Exception as e:
        print(f"❌ Error fetching weekly respiration data: {e}")


def raw_respiration_data():
    """Demonstrate accessing raw respiration API response."""
    print("\n🔍 Raw Respiration API Response")
    print("=" * 40)

    try:
        # Create clients and factory
        auth_client = AuthClient()
        api_client = APIClient(
            auth_client=auth_client
        )  # Metrics are auto-discovered when first accessed
        resp_accessor = api_client.metrics.get("respiration")
        if not resp_accessor:
            print("❌ Respiration metric not available")
            return

        raw_data = resp_accessor.raw()

        if raw_data:
            print("Raw API keys:", list(raw_data.keys()))

            # Show respiration summary structure
            if "respirationSummary" in raw_data:
                summary = raw_data["respirationSummary"]
                print(f"Summary keys: {list(summary.keys())}")
                print(f"Calendar date: {summary.get('calendarDate')}")
                print(f"Waking avg: {summary.get('avgWakingRespirationValue')} bpm")
                print(f"Sleep avg: {summary.get('avgSleepRespirationValue')} bpm")

            # Show readings structure
            if "respirationValuesArray" in raw_data:
                readings = raw_data["respirationValuesArray"]
                print(f"\nReadings: {len(readings)} measurements")
                if len(readings) > 0:
                    print(f"First reading format: {readings[0]}")
                    print("Structure: [timestamp_ms, respiration_bpm]")
        else:
            print("❌ No raw data available")

    except Exception as e:
        print(f"❌ Error fetching raw respiration data: {e}")


if __name__ == "__main__":
    # Run all demos
    main()
    weekly_respiration_trends()
    raw_respiration_data()

    print("\n💡 Modern API Notes:")
    print("   • Explicit client creation: AuthClient() and APIClient()")
    print("   • Use api_client.metrics for direct metric access")
    print("   • Respiration uses standard MetricAccessor")
    print("   • Methods: .get(), .list(), .raw()")
    print("   • Direct class imports: from garmy import Respiration")
    print("\n💡 Respiration Data Notes:")
    print("   • All data comes directly from Garmin's wellness service API")
    print("   • Measurements in breaths per minute (bpm)")
    print("   • Sleep vs waking patterns show autonomic nervous system state")
    print("   • Use this raw data for your own respiratory analysis")
