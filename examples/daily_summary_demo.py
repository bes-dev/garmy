#!/usr/bin/env python3
"""Daily Summary Demo - Complete Daily Health Overview.

===================================================

This example demonstrates how to access comprehensive daily summary data from the
Garmin Connect API using the new modern API architecture.

This includes all major health metrics in one convenient endpoint: activity,
calories, heart rate, stress, body battery, SpO2, respiration.

Daily Summary is perfect for dashboards, health overviews, and comprehensive
daily health tracking without needing multiple API calls.

Example output:
    Steps: 1,671 / 6,000 (27.9%)
    Calories: 1,963 kcal (3.6% active)
    Heart Rate: 55 bpm resting (51-107 range)
    Stress: 32/100 (BALANCED)
    Body Battery: 22% (charged 65, drained 70)
    SpO2: 98% average (85-98 range)
"""


from garmy import APIClient, AuthClient


def main():
    """Demonstrate modern Daily Summary data access."""
    print("📊 Garmin Daily Summary Demo (Modern API)")
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
        # Get daily summary accessor using modern API
        print("🔍 Getting daily summary accessor...")
        summary_accessor = api_client.metrics.get("daily_summary")

        if not summary_accessor:
            print("❌ Daily summary metric not available")
            return

        print(f"   Accessor type: {type(summary_accessor)}")

        # Get today's complete daily summary
        print("\n📈 Fetching today's daily summary...")
        summary = summary_accessor.get()

        if not summary:
            print("❌ No daily summary data available")
            print("💡 Make sure you:")
            print("   - Have a compatible Garmin device")
            print("   - Wore your device regularly")
            print("   - Device has wellness tracking enabled")
            print("   - Are authenticated with valid credentials")
            return

        print(f"\n📅 Daily Summary for {summary.calendar_date}")
        print("=" * 50)

        # Activity Summary
        print("\n🚶‍♂️ Activity:")
        print(
            f"   Steps: {summary.total_steps:,} / {summary.daily_step_goal:,} "
            f"({summary.step_goal_progress:.1f}%)"
        )
        print(
            f"   Distance: {summary.distance_km:.1f} km ({summary.distance_miles:.1f} miles)"
        )
        print(f"   Active time: {summary.total_active_minutes:.0f} minutes")
        print(f"   Sedentary time: {summary.total_sedentary_hours:.1f} hours")
        if summary.floors_ascended > 0:
            print(
                f"   Floors: {summary.floors_ascended} ascended, "
                f"{summary.floors_descended} descended"
            )
        if summary.intensity_minutes_goal > 0:
            print(
                f"   Intensity minutes: "
                f"{summary.moderate_intensity_minutes + summary.vigorous_intensity_minutes}/"
                f"{summary.intensity_minutes_goal} ({summary.intensity_minutes_progress:.1f}%)"
            )

        # Calories Summary
        print("\n🔥 Calories:")
        print(f"   Total: {summary.total_kilocalories:,} kcal")
        print(
            f"   Active: {summary.active_kilocalories:,} kcal ({summary.activity_efficiency:.1f}%)"
        )
        print(
            f"   BMR: {summary.bmr_kilocalories:,} kcal ({summary.bmr_percentage:.1f}%)"
        )
        if summary.net_calorie_goal:
            print(f"   Goal: {summary.net_calorie_goal:,} kcal")

        # Heart Rate Summary
        print("\n❤️ Heart Rate:")
        print(f"   Resting: {summary.resting_heart_rate} bpm")
        print(
            f"   Range: {summary.min_heart_rate}-{summary.max_heart_rate} bpm "
            f"({summary.heart_rate_range} bpm range)"
        )
        print(
            f"   7-day avg resting: {summary.last_seven_days_avg_resting_heart_rate} bpm"
        )
        if summary.resting_hr_trend != 0:
            trend_icon = "📈" if summary.resting_hr_trend > 0 else "📉"
            print(
                f"   Trend: {trend_icon} {summary.resting_hr_trend:+d} bpm vs 7-day avg"
            )

        # Stress Summary
        print("\n😌 Stress:")
        print(
            f"   Average: {summary.average_stress_level}/100 ({summary.stress_qualifier})"
        )
        print(f"   Max: {summary.max_stress_level}/100")
        print(f"   Total measured: {summary.total_stress_hours:.1f} hours")
        print(
            f"   Distribution: {summary.low_stress_percentage:.0f}% low, "
            f"{summary.medium_stress_percentage:.0f}% medium, "
            f"{summary.high_stress_percentage:.0f}% high"
        )

        # Body Battery Summary
        print("\n🔋 Body Battery:")
        print(f"   Current: {summary.body_battery_most_recent_value}%")
        print(
            f"   Range: {summary.body_battery_lowest_value}%-{summary.body_battery_highest_value}%"
        )
        print(
            f"   Charged: +{summary.body_battery_charged_value}, "
            f"Drained: -{summary.body_battery_drained_value}"
        )
        print(f"   Net change: {summary.net_body_battery_change:+d}")
        print(f"   Sleep recovery: {summary.body_battery_during_sleep}")
        print(f"   Wake level: {summary.body_battery_at_wake_time}%")

        # SpO2 Summary
        if summary.average_spo2 > 0:
            print("\n🫁 SpO2:")
            print(f"   Average: {summary.average_spo2}%")
            print(
                f"   Range: {summary.lowest_spo2}-{summary.average_spo2}% "
                f"({summary.spo2_range}% drop)"
            )
            print(f"   Latest: {summary.latest_spo2}%")

        # Respiration Summary
        if summary.avg_waking_respiration_value > 0:
            print("\n🌬️ Respiration:")
            print(f"   Waking average: {summary.avg_waking_respiration_value} bpm")
            print(
                f"   Range: {summary.lowest_respiration_value}-"
                f"{summary.highest_respiration_value} bpm"
            )
            print(f"   Latest: {summary.latest_respiration_value} bpm")

        # Sleep Summary
        if summary.sleep_hours > 0:
            print("\n😴 Sleep:")
            print(f"   Duration: {summary.sleep_hours:.1f} hours")
            print(f"   Measurable sleep: {summary.measurable_sleep_hours:.1f} hours")

        # Device & Sync Info
        print("\n📱 Device Info:")
        print(f"   Source: {summary.source}")
        print(f"   Wellness period: {summary.wellness_duration_hours:.1f} hours")
        print(
            f"   Includes: {'✓' if summary.includes_wellness_data else '✗'} wellness, "
            f"{'✓' if summary.includes_activity_data else '✗'} activity, "
            f"{'✓' if summary.includes_calorie_consumed_data else '✗'} nutrition"
        )
        if summary.last_sync_datetime_gmt:
            print(f"   Last sync: {summary.last_sync_datetime_gmt}")

    except Exception as e:
        print(f"❌ Error fetching daily summary: {e}")
        print("💡 Make sure you're authenticated and have summary data available")


def weekly_health_overview():
    """Demonstrate weekly health trends using daily summaries."""
    print("\n📅 Weekly Health Overview")
    print("=" * 25)

    try:
        # Create clients and factory
        auth_client = AuthClient()
        api_client = APIClient(
            auth_client=auth_client
        )  # Metrics are auto-discovered when first accessed
        # Get last 7 days of daily summaries
        print("🚀 Fetching last 7 days of health data...")

        summary_accessor = api_client.metrics.get("daily_summary")
        if not summary_accessor:
            print("❌ Daily summary metric not available")
            return

        daily_summaries = summary_accessor.list(days=7)

        if not daily_summaries:
            print("❌ No weekly health data available")
            return

        # Sort by date
        daily_summaries.sort(key=lambda x: x.calendar_date)

        print("\n📊 Weekly Health Trends:")
        print("   Date       | Steps   | Calories | Stress | Body Battery | SpO2")
        print("   -----------|---------|----------|--------|--------------|-----")

        # Track totals for averages
        total_steps = 0
        total_calories = 0
        total_stress_readings = 0
        total_stress_sum = 0
        total_bb_readings = 0
        total_bb_sum = 0
        total_spo2_readings = 0
        total_spo2_sum = 0

        for day in daily_summaries:
            # Calculate values
            steps = day.total_steps
            calories = day.total_kilocalories
            stress = day.average_stress_level
            bb = day.body_battery_most_recent_value
            spo2 = day.average_spo2

            # Track totals
            total_steps += steps
            total_calories += calories
            if stress > 0:
                total_stress_sum += stress
                total_stress_readings += 1
            if bb > 0:
                total_bb_sum += bb
                total_bb_readings += 1
            if spo2 > 0:
                total_spo2_sum += spo2
                total_spo2_readings += 1

            # Format display
            stress_str = f"{stress:3.0f}" if stress > 0 else " - "
            bb_str = f"{bb:3.0f}%" if bb > 0 else "  - "
            spo2_str = f"{spo2:3.0f}%" if spo2 > 0 else "  - "

            print(
                f"   {day.calendar_date} | {steps:7,} | {calories:8,} | "
                f"{stress_str:6} | {bb_str:12} | {spo2_str}"
            )

        # Weekly averages
        days_count = len(daily_summaries)
        avg_steps = total_steps // days_count
        avg_calories = total_calories // days_count
        avg_stress = (
            total_stress_sum // total_stress_readings
            if total_stress_readings > 0
            else 0
        )
        avg_bb = total_bb_sum // total_bb_readings if total_bb_readings > 0 else 0
        avg_spo2 = (
            total_spo2_sum // total_spo2_readings if total_spo2_readings > 0 else 0
        )

        stress_str = f"{avg_stress:3.0f}" if avg_stress > 0 else " - "
        bb_str = f"{avg_bb:3.0f}%" if avg_bb > 0 else "  - "
        spo2_str = f"{avg_spo2:3.0f}%" if avg_spo2 > 0 else "  - "

        print("   -----------|---------|----------|--------|--------------|-----")
        print(
            f"   Average    | {avg_steps:7,} | {avg_calories:8,} | "
            f"{stress_str:6} | {bb_str:12} | {spo2_str}"
        )

        # Health insights
        print("\n🎯 Weekly Health Insights:")
        print(f"   Activity: {avg_steps:,} steps/day, {avg_calories:,} kcal/day")
        if avg_stress > 0:
            stress_level = (
                "low" if avg_stress < 25 else "moderate" if avg_stress < 50 else "high"
            )
            print(f"   Stress: {avg_stress}/100 average ({stress_level} level)")
        if avg_bb > 0:
            bb_level = "low" if avg_bb < 25 else "moderate" if avg_bb < 75 else "high"
            print(f"   Energy: {avg_bb}% Body Battery average ({bb_level} level)")
        if avg_spo2 > 0:
            print(f"   Oxygen: {avg_spo2}% SpO2 average")

    except Exception as e:
        print(f"❌ Error fetching weekly overview: {e}")


def health_dashboard():
    """Create a compact health dashboard view."""
    print("\n📱 Health Dashboard")
    print("=" * 18)

    try:
        # Create clients and factory
        auth_client = AuthClient()
        api_client = APIClient(
            auth_client=auth_client
        )  # Metrics are auto-discovered when first accessed
        summary_accessor = api_client.metrics.get("daily_summary")
        if not summary_accessor:
            print("❌ Daily summary metric not available")
            return

        summary = summary_accessor.get()

        if not summary:
            print("❌ No dashboard data available")
            return

        # Compact dashboard format
        print(f"🗓️  {summary.calendar_date}")
        print(f"👟 {summary.total_steps:,} steps ({summary.step_goal_progress:.0f}%)")
        print(
            f"🔥 {summary.total_kilocalories:,} kcal ({summary.activity_efficiency:.0f}% active)"
        )
        print(f"❤️  {summary.resting_heart_rate} bpm resting")
        print(
            f"😌 {summary.average_stress_level}/100 stress ({summary.stress_qualifier.lower()})"
        )
        print(f"🔋 {summary.body_battery_most_recent_value}% energy")
        if summary.average_spo2 > 0:
            print(f"🫁 {summary.average_spo2}% SpO2")

        # Health score calculation (simple example)
        health_factors = []
        if summary.step_goal_progress >= 100:
            health_factors.append("steps")
        if summary.activity_efficiency >= 5:
            health_factors.append("active")
        if summary.average_stress_level < 30:
            health_factors.append("stress")
        if summary.body_battery_most_recent_value >= 50:
            health_factors.append("energy")

        health_score = len(health_factors) * 25
        print(f"\n🎯 Daily Health Score: {health_score}/100")
        if health_factors:
            print(f"   ✓ Good: {', '.join(health_factors)}")

    except Exception as e:
        print(f"❌ Error creating health dashboard: {e}")


if __name__ == "__main__":
    # Run all demos
    main()
    weekly_health_overview()
    health_dashboard()

    print("\n💡 Modern API Notes:")
    print("   • Explicit client creation: AuthClient() and APIClient()")
    print("   • Use api_client.metrics for direct metric access")
    print("   • Daily Summary uses standard MetricAccessor")
    print("   • Methods: .get(), .list(), .raw()")
    print("   • Direct class imports: from garmy import DailySummary")
    print("\n💡 Daily Summary Analysis Notes:")
    print("   • One API call provides comprehensive daily health overview")
    print("   • Combines activity, calories, heart rate, stress, body battery, SpO2")
    print("   • Perfect for dashboards and daily health tracking")
    print("   • All data comes directly from Garmin Connect API")
    print("   • Structured data with convenient properties for analysis")
    print("   • Use this for efficient health monitoring without multiple API calls")
