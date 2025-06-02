#!/usr/bin/env python3
"""Steps Data Demo - Daily Steps Analysis.

=====================================

This example demonstrates how to access daily steps data from the
Garmin Connect API using the new modern API architecture.

Steps tracking includes daily step counts, step goals, distances walked,
and weekly aggregations for trend analysis.

Example output:
    Weekly total: 28,562 steps
    Daily average: 4,080 steps
    Distance: 22.5 km walked
"""


from garmy import APIClient, AuthClient


def main():
    """Demonstrate modern Steps data access."""
    print("👟 Garmin Steps Data Demo (Modern API)")
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
        # Get steps accessor using modern API
        print("🔍 Getting steps accessor...")
        steps_accessor = api_client.metrics.get("steps")

        if not steps_accessor:
            print("❌ Steps metric not available")
            return

        print(f"   Accessor type: {type(steps_accessor)}")

        # Get steps data for the last 7 days
        print("\n📊 Fetching last 7 days of steps data...")
        steps = steps_accessor.get(days=7)

        if not steps or not steps.daily_steps:
            print("❌ No steps data available")
            print("💡 Make sure you:")
            print("   - Have a compatible Garmin device")
            print("   - Wore your device regularly")
            print("   - Device has step tracking enabled")
            print("   - Are authenticated with valid credentials")
            return

        # Display steps summary using convenient properties
        print("\n📈 Steps Summary (from Garmin API):")
        print(f"   Period: {len(steps.daily_steps)} days")
        print(f"   Weekly total: {steps.weekly_total:,} steps")
        print(f"   Daily average: {steps.aggregations.daily_average:,} steps")
        print(f"   Total distance: {steps.total_distance_km:.1f} km")

        # Display daily breakdown using dataclass properties
        print("\n📋 Daily Breakdown:")
        print("   Date       | Steps    | Goal     | Distance | Goal %")
        print("   -----------|---------|---------|---------|---------")

        for day in steps.daily_steps:
            # Calculate goal percentage and achievement
            goal_pct = (
                (day.total_steps / day.step_goal * 100) if day.step_goal > 0 else 0
            )
            goal_icon = "✅" if day.total_steps >= day.step_goal else "❌"

            print(
                f"   {day.calendar_date} | {day.total_steps:7,} | {day.step_goal:7,} | "
                f"{day.distance_km:6.1f}km | {goal_pct:5.1f}% {goal_icon}"
            )

        # Calculate additional statistics from daily steps
        step_counts = [day.total_steps for day in steps.daily_steps]
        if step_counts:
            max_steps = max(step_counts)
            min_steps = min(step_counts)

            print("\n📊 Additional Statistics:")
            print(f"   Highest day: {max_steps:,} steps")
            print(f"   Lowest day: {min_steps:,} steps")
            print(f"   Range: {max_steps - min_steps:,} steps")

            # Goal achievement analysis
            goals_achieved = sum(
                1 for day in steps.daily_steps if day.total_steps >= day.step_goal
            )
            achievement_rate = (goals_achieved / len(steps.daily_steps)) * 100

            print("\n🎯 Goal Achievement:")
            print(f"   Days achieved: {goals_achieved}/{len(steps.daily_steps)}")
            print(f"   Achievement rate: {achievement_rate:.1f}%")

            # Activity level distribution
            high_activity_days = sum(
                1 for steps_count in step_counts if steps_count >= 10000
            )
            moderate_activity_days = sum(
                1 for steps_count in step_counts if 5000 <= steps_count < 10000
            )
            low_activity_days = sum(
                1 for steps_count in step_counts if steps_count < 5000
            )

            print("\n🚶‍♂️ Activity Level Distribution:")
            print(f"   High activity (≥10k steps): {high_activity_days} days")
            print(f"   Moderate activity (5k-10k): {moderate_activity_days} days")
            print(f"   Low activity (<5k steps): {low_activity_days} days")

    except Exception as e:
        print(f"❌ Error fetching steps data: {e}")
        print("💡 Make sure you're authenticated and have steps data available")


def weekly_steps_comparison():
    """Demonstrate comparing different weeks using raw data."""
    print("\n📅 Weekly Steps Comparison")
    print("=" * 30)

    try:
        # Create clients and factory
        auth_client = AuthClient()
        api_client = APIClient(
            auth_client=auth_client
        )  # Metrics are auto-discovered when first accessed
        # Get current week and previous week
        print("🚀 Fetching current and previous week data...")

        steps_accessor = api_client.metrics.get("steps")
        if not steps_accessor:
            print("❌ Steps metric not available")
            return

        this_week = steps_accessor.get(days=7)

        # Get previous week by fetching 14 days and taking the first 7
        two_weeks = steps_accessor.get(days=14)

        if not this_week or not two_weeks:
            print("❌ Unable to fetch comparison data")
            return

        # Extract previous week (first 7 days from 14-day request)
        prev_week_values = (
            two_weeks.daily_steps[:7] if len(two_weeks.daily_steps) >= 14 else []
        )
        this_week_values = this_week.daily_steps

        print("\n📊 Week Comparison:")
        print("   Period        | Total Steps | Daily Avg | Goals Met")
        print("   --------------|-------------|-----------|----------")

        # This week
        this_total = sum(day.total_steps for day in this_week_values)
        this_avg = this_total // len(this_week_values) if this_week_values else 0
        this_goals = sum(
            1 for day in this_week_values if day.total_steps >= day.step_goal
        )

        print(f"   This week     | {this_total:10,} | {this_avg:8,} | {this_goals}/7")

        # Previous week (if available)
        if prev_week_values:
            prev_total = sum(day.total_steps for day in prev_week_values)
            prev_avg = prev_total // len(prev_week_values)
            prev_goals = sum(
                1 for day in prev_week_values if day.total_steps >= day.step_goal
            )

            print(
                f"   Previous week | {prev_total:10,} | {prev_avg:8,} | {prev_goals}/7"
            )

            # Trend analysis
            trend = this_avg - prev_avg
            print("\n📈 Trend Analysis:")
            if trend > 0:
                print(f"   📈 Improving: +{trend:,} steps/day")
            elif trend < 0:
                print(f"   📉 Declining: {trend:,} steps/day")
            else:
                print("   ➡️ Stable: No significant change")
        else:
            print("   Previous week | Insufficient data")

    except Exception as e:
        print(f"❌ Error fetching comparison data: {e}")


def raw_api_data():
    """Demonstrate accessing completely raw API response."""
    print("\n🔍 Raw API Response ")
    print("=" * 30)

    try:
        # Create clients and factory
        auth_client = AuthClient()
        api_client = APIClient(
            auth_client=auth_client
        )  # Metrics are auto-discovered when first accessed
        # Get raw JSON response without any parsing
        steps_accessor = api_client.metrics.get("steps")
        if not steps_accessor:
            print("❌ Steps metric not available")
            return

        raw_data = steps_accessor.raw(days=3)  # Just 3 days for demo

        if raw_data:
            print("Raw API structure:")
            print(f"   Top-level keys: {list(raw_data.keys())}")

            if "values" in raw_data:
                print(f"   Daily values count: {len(raw_data['values'])}")
                if raw_data["values"]:
                    first_day = raw_data["values"][0]
                    print(f"   Sample day keys: {list(first_day.keys())}")
                    if "values" in first_day:
                        print(f"   Sample metrics: {list(first_day['values'].keys())}")

                        # Show actual values for demonstration
                        sample_values = first_day["values"]
                        print("   Sample data:")
                        print(f"     Steps: {sample_values.get('totalSteps', 'N/A')}")
                        print(f"     Goal: {sample_values.get('stepGoal', 'N/A')}")
                        print(
                            f"     Distance: {sample_values.get('totalDistance', 'N/A')} meters"
                        )

            if "aggregations" in raw_data:
                print(f"   Aggregation keys: {list(raw_data['aggregations'].keys())}")
                agg = raw_data["aggregations"]
                print(f"   Weekly total: {agg.get('totalStepsWeeklyAverage', 'N/A')}")
                print(f"   Daily average: {agg.get('totalStepsAverage', 'N/A')}")
        else:
            print("❌ No raw data available")

    except Exception as e:
        print(f"❌ Error fetching raw data: {e}")


def run_all_demos():
    """Run all demo functions sequentially."""
    print("🚀 Running all steps demos...")

    # Run demos sequentially to avoid connection issues
    main()

    try:
        weekly_steps_comparison()
    except Exception as e:
        print(f"❌ Weekly comparison demo failed: {e}")

    try:
        raw_api_data()
    except Exception as e:
        print(f"❌ Raw API demo failed: {e}")


if __name__ == "__main__":
    (run_all_demos())

    print("\n💡 Steps Data Analysis Notes:")
    print("   • All data comes directly from Garmin Connect API")
    print("   • Raw data format preserves original API structure")
    print("   • Steps are tracked continuously by compatible devices")
    print("   • Goals are adaptive based on recent activity patterns")
    print("   • Distance calculations use device stride length settings")
    print("   • Use this raw data for your own activity analysis")
    print("   • Async methods provide better performance for time-series data")
