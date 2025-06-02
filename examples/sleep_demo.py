#!/usr/bin/env python3
"""Sleep Data Demo - Comprehensive Sleep Analysis.

==============================================

This example demonstrates how to access comprehensive sleep data from Garmin Connect
using the new modern API architecture.

Includes sleep stages, SpO2, respiration, and detailed temporal readings.
Provides direct access to Garmin's sleep service data for custom analytics.

Example output:
    Date: 2025-05-28
    Sleep Time: 7h 32m
    Sleep Efficiency: 87.2%
    Deep Sleep: 1h 45m (23.2%)
    Average SpO2: 96%
"""

from datetime import datetime

from garmy import APIClient, AuthClient


def format_duration(seconds):
    """Format seconds as hours:minutes."""
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    return f"{hours}h {minutes}m"


def main():
    """Demonstrate modern Sleep data access."""
    print("😴 Garmin Sleep Data Demo (Modern API)")
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
        # Get sleep accessor using modern API
        print("🔍 Getting sleep accessor...")
        sleep_accessor = api_client.metrics.get("sleep")

        if not sleep_accessor:
            print("❌ Sleep metric not available")
            return

        print(f"   Accessor type: {type(sleep_accessor)}")

        # Get today's sleep data (or try a specific date)
        print("\n📊 Fetching sleep data...")
        # sleep = sleep_accessor.get()
        sleep = sleep_accessor.get("2025-05-28")  # Example date

        if not sleep or not sleep.sleep_summary:
            print("❌ No sleep data available for today")
            print("💡 Make sure you:")
            print("   - Wore your device during sleep")
            print("   - Have a compatible Garmin device")
            print("   - Are authenticated with valid credentials")
            print("   - Try a different date: sleep_accessor.get('2025-05-28')")
            return

        summary = sleep.sleep_summary

        # Basic sleep information
        print("\n📈 Sleep Summary:")
        print(f"   Date: {summary.calendar_date}")
        print(f"   Sleep Start: {summary.sleep_start_datetime_local.strftime('%H:%M')}")
        print(f"   Sleep End: {summary.sleep_end_datetime_local.strftime('%H:%M')}")
        print(f"   Total Sleep Time: {format_duration(summary.sleep_time_seconds)}")
        print(f"   Sleep Efficiency: {summary.sleep_efficiency_percentage:.1f}%")
        print(f"   Times Awake: {summary.awake_count}")

        print("\n🌙 Sleep Stages Breakdown:")

        # Sleep stages
        print(
            f"   Deep Sleep:  {format_duration(summary.deep_sleep_seconds)} "
            f"({sleep.deep_sleep_percentage:.1f}%)"
        )
        print(
            f"   Light Sleep: {format_duration(summary.light_sleep_seconds)} "
            f"({sleep.light_sleep_percentage:.1f}%)"
        )
        print(
            f"   REM Sleep:   {format_duration(summary.rem_sleep_seconds)} "
            f"({sleep.rem_sleep_percentage:.1f}%)"
        )
        print(
            f"   Awake Time:  {format_duration(summary.awake_sleep_seconds)} "
            f"({sleep.awake_percentage:.1f}%)"
        )

        print("\n🫁 Physiological Measurements:")

        # SpO2 data
        if summary.average_sp_o2_value:
            print(f"   Average SpO2: {summary.average_sp_o2_value}%")
            print(f"   Lowest SpO2:  {summary.lowest_sp_o2_value}%")
            print(f"   Highest SpO2: {summary.highest_sp_o2_value}%")
            print(f"   SpO2 Readings: {sleep.spo2_readings_count} measurements")
        else:
            print("   SpO2: No data available")

        # Respiration data
        if summary.average_respiration_value:
            print(f"   Average Respiration: {summary.average_respiration_value} bpm")
            print(f"   Lowest Respiration:  {summary.lowest_respiration_value} bpm")
            print(f"   Highest Respiration: {summary.highest_respiration_value} bpm")
            print(
                f"   Respiration Readings: {sleep.respiration_readings_count} measurements"
            )
        else:
            print("   Respiration: No data available")

        # Stress during sleep
        if summary.avg_sleep_stress:
            print(f"   Average Sleep Stress: {summary.avg_sleep_stress}")

        print("\n🏆 Sleep Quality Insights:")

        # Sleep scores and feedback
        if summary.sleep_scores:
            scores = summary.sleep_scores
            print("   Sleep Scores:")
            if isinstance(scores, dict):
                for key, value in scores.items():
                    if isinstance(value, dict):
                        # Try different possible fields in the score object
                        qualifier = (
                            value.get("qualifier_key")  # Snake case version
                            or value.get("qualifierKey")  # Camel case version
                            or value.get("value")
                            or value.get("score")
                            or value.get("percentage")
                            or "N/A"
                        )
                        print(f"     {key.replace('_', ' ').title()}: {qualifier}")
                    elif value is not None:
                        print(f"     {key.replace('_', ' ').title()}: {value}")
                    else:
                        print(f"     {key.replace('_', ' ').title()}: N/A")
        else:
            print("   Sleep Scores: No scores available")

        if summary.sleep_score_feedback:
            print(f"   Feedback: {summary.sleep_score_feedback}")

        if summary.sleep_score_insight:
            print(f"   Insight: {summary.sleep_score_insight}")

        print("\n📊 Detailed Temporal Data:")

        # Show sample of SpO2 readings
        if sleep.wellness_epoch_spo2_data_dto_list:
            print("   SpO2 Readings (first 5):")
            for _i, reading in enumerate(sleep.wellness_epoch_spo2_data_dto_list[:5]):

                # Use correct field names from debug output
                timestamp = reading.get("epoch_timestamp", "")
                if timestamp:
                    try:
                        # Parse ISO format timestamp like "2025-05-28T20:14:00.0"
                        if isinstance(timestamp, str) and "T" in timestamp:
                            # Remove the .0 at the end if present and parse
                            timestamp_clean = timestamp.split(".")[0]
                            dt = datetime.fromisoformat(timestamp_clean)
                            time_str = dt.strftime("%H:%M:%S")
                        else:
                            time_str = "Invalid format"
                    except Exception:
                        time_str = "Invalid time"
                else:
                    time_str = "No timestamp"

                # Use correct field names
                value = reading.get("spo2_reading", 0)
                confidence_str = (
                    f" (confidence: {reading.get('reading_confidence', 0):.2f})"
                    if reading.get("reading_confidence")
                    else ""
                )
                print(f"     {time_str}: {value}%{confidence_str}")

            if len(sleep.wellness_epoch_spo2_data_dto_list) > 5:
                print(
                    f"     ... and {len(sleep.wellness_epoch_spo2_data_dto_list) - 5} more readings"
                )

        # Show sample of respiration readings
        if sleep.wellness_epoch_respiration_data_dto_list:
            print("   Respiration Readings (first 5):")
            for _i, reading in enumerate(
                sleep.wellness_epoch_respiration_data_dto_list[:5]
            ):

                # Use correct field names from debug output
                timestamp = reading.get("start_time_gmt", 0)
                if timestamp:
                    try:
                        # Convert to int if it's a string
                        if isinstance(timestamp, str):
                            timestamp = int(timestamp)

                        if timestamp > 0:
                            if timestamp > 1e12:  # Likely milliseconds
                                time_str = datetime.fromtimestamp(
                                    timestamp / 1000
                                ).strftime("%H:%M:%S")
                            else:  # Likely seconds
                                time_str = datetime.fromtimestamp(timestamp).strftime(
                                    "%H:%M:%S"
                                )
                        else:
                            time_str = "No timestamp"
                    except Exception:
                        time_str = "Invalid time"
                else:
                    time_str = "No timestamp"

                # Use correct field names
                value = reading.get("respiration_value", 0)
                print(f"     {time_str}: {value} bpm")

            if len(sleep.wellness_epoch_respiration_data_dto_list) > 5:
                print(
                    f"     ... and "
                    f"{len(sleep.wellness_epoch_respiration_data_dto_list) - 5} more readings"
                )

        print("\n🔧 Raw API Data Access:")
        print("   Available raw data fields:")
        print(
            f"   • sleep_summary: Main sleep summary with {len(vars(summary))} fields"
        )
        print(
            f"   • wellness_epoch_spo2_data_dto_list: "
            f"{len(sleep.wellness_epoch_spo2_data_dto_list)} SpO2 readings"
        )
        print(
            f"   • wellness_epoch_respiration_data_dto_list: "
            f"{len(sleep.wellness_epoch_respiration_data_dto_list)} respiration readings"
        )

        # Check for additional fields
        additional_fields = [
            attr
            for attr in dir(sleep)
            if not attr.startswith("_")
            and attr
            not in [
                "sleep_summary",
                "wellness_epoch_spo2_data_dto_list",
                "wellness_epoch_respiration_data_dto_list",
            ]
            and not callable(getattr(sleep, attr))
        ]

        if additional_fields:
            print(f"   • Additional fields: {', '.join(additional_fields)}")

        print("\n💡 Tip: All data comes directly from Garmin's sleep service API")
        print("    Use this raw data to create your own sleep analysis and insights")

    except Exception as e:
        print(f"❌ Error retrieving sleep data: {e}")
        print("💡 Make sure you're authenticated and have sleep data available")


def weekly_sleep_trends():
    """Demonstrate accessing multiple days of sleep data."""
    print("\n📅 Weekly Sleep Trends")
    print("=" * 30)

    try:
        # Create clients and factory
        auth_client = AuthClient()
        api_client = APIClient(
            auth_client=auth_client
        )  # Metrics are auto-discovered when first accessed
        sleep_accessor = api_client.metrics.get("sleep")
        if not sleep_accessor:
            print("❌ Sleep metric not available")
            return

        # Get sleep data for the last 7 days
        print("🚀 Fetching 7 days of sleep data...")
        weekly_data = sleep_accessor.list(days=7)

        if not weekly_data:
            print("❌ No sleep data available for the past week")
            return

        print("   Date       | Duration | Efficiency | Deep% | REM%")
        print("   -----------|----------|------------|-------|------")

        for sleep in weekly_data:
            if sleep.sleep_summary:
                summary = sleep.sleep_summary
                duration = format_duration(summary.sleep_time_seconds)
                efficiency = f"{summary.sleep_efficiency_percentage:.1f}%"
                deep_pct = f"{sleep.deep_sleep_percentage:.1f}%"
                rem_pct = f"{sleep.rem_sleep_percentage:.1f}%"

                print(
                    f"   {summary.calendar_date} | {duration:>8} | {efficiency:>10} | "
                    f"{deep_pct:>5} | {rem_pct:>4}"
                )

    except Exception as e:
        print(f"❌ Error fetching weekly sleep data: {e}")


def raw_sleep_data():
    """Demonstrate accessing raw sleep API response."""
    print("\n🔍 Raw Sleep API Response")
    print("=" * 35)

    try:
        # Create clients and factory
        auth_client = AuthClient()
        api_client = APIClient(
            auth_client=auth_client
        )  # Metrics are auto-discovered when first accessed
        sleep_accessor = api_client.metrics.get("sleep")
        if not sleep_accessor:
            print("❌ Sleep metric not available")
            return

        # Get raw JSON response without any parsing
        raw_data = sleep_accessor.raw()

        if raw_data:
            print("Raw API keys:", list(raw_data.keys()))

            # Show sleep summary structure
            if "sleepSummary" in raw_data:
                sleep_summary = raw_data["sleepSummary"]
                print(f"Sleep summary keys: {list(sleep_summary.keys())}")
                print(f"Calendar date: {sleep_summary.get('calendarDate')}")
                print(f"Sleep time: {sleep_summary.get('sleepTimeSeconds')}s")
                print(
                    f"Sleep efficiency: {sleep_summary.get('sleepEfficiencyPercentage')}%"
                )

            # Show SpO2 data structure
            if "wellnessEpochSpO2DataDtoList" in raw_data:
                spo2_data = raw_data["wellnessEpochSpO2DataDtoList"]
                print(f"\nSpO2 readings: {len(spo2_data)} measurements")
                if len(spo2_data) > 0:
                    print(f"First SpO2 reading keys: {list(spo2_data[0].keys())}")

            # Show respiration data structure
            if "wellnessEpochRespirationDataDtoList" in raw_data:
                resp_data = raw_data["wellnessEpochRespirationDataDtoList"]
                print(f"Respiration readings: {len(resp_data)} measurements")
                if len(resp_data) > 0:
                    print(
                        f"First respiration reading keys: {list(resp_data[0].keys())}"
                    )
        else:
            print("❌ No raw data available")

    except Exception as e:
        print(f"❌ Error fetching raw sleep data: {e}")


if __name__ == "__main__":
    # Run all demos
    main()
    weekly_sleep_trends()
    raw_sleep_data()

    print("\n💡 Modern API Notes:")
    print("   • Explicit client creation: AuthClient() and APIClient()")
    print("   • Use api_client.metrics for direct metric access")
    print("   • Sleep uses standard MetricAccessor")
    print("   • Methods: .get(), .list(), .raw()")
    print("   • Direct class imports: from garmy import Sleep")
