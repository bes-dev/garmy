#!/usr/bin/env python3
"""Calories Data Demo - Daily Calorie Tracking.

==========================================

This example demonstrates how to access daily calories data from the
Garmin Connect API using the new modern API architecture.

Calories tracking includes total burned, active calories, BMR, wellness calories,
and goal tracking for comprehensive energy expenditure analysis.

Example output:
    Total calories: 1,963 kcal
    Active calories: 70 kcal
    BMR calories: 1,893 kcal
    Activity efficiency: 3.6%
"""


from garmy import APIClient, AuthClient


def main():
    """Demonstrate modern Calories data access."""
    print("🔥 Garmin Calories Data Demo (Modern API)")
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
        # Get calories accessor using modern API
        print("🔍 Getting calories accessor...")
        calories_accessor = api_client.metrics.get("calories")

        if not calories_accessor:
            print("❌ Calories metric not available")
            return

        print(f"   Accessor type: {type(calories_accessor)}")

        # Get today's calories data
        print("\n📊 Fetching today's calories data...")
        calories = calories_accessor.get()

        if not calories:
            print("❌ No calories data available")
            print("💡 Make sure you:")
            print("   - Have a compatible Garmin device")
            print("   - Wore your device regularly")
            print("   - Device has calorie tracking enabled")
            print("   - Are authenticated with valid credentials")
            return

        # Display calories summary using convenient properties
        print("\n🔥 Calories Summary (from Garmin API):")
        print(f"   Date: {calories.calendar_date}")
        print(f"   Total calories: {calories.total_kilocalories:,} kcal")
        print(f"   Active calories: {calories.active_kilocalories:,} kcal")
        print(f"   BMR calories: {calories.bmr_kilocalories:,} kcal")
        print(f"   Wellness calories: {calories.wellness_kilocalories:,} kcal")

        # Show calculated metrics
        print("\n📈 Calculated Metrics:")
        print(f"   Activity efficiency: {calories.activity_efficiency:.1f}%")
        print(f"   BMR percentage: {calories.bmr_percentage:.1f}%")
        print(f"   Total burned: {calories.total_burned:,} kcal")

        # Show optional fields if available
        if calories.consumed_kilocalories is not None:
            print(f"   Consumed calories: {calories.consumed_kilocalories:,} kcal")
            if calories.calorie_balance is not None:
                balance = calories.calorie_balance
                balance_status = (
                    "surplus"
                    if balance > 0
                    else "deficit" if balance < 0 else "balanced"
                )
                print(f"   Calorie balance: {balance:+,} kcal ({balance_status})")

        if calories.net_calorie_goal is not None:
            print(f"   Calorie goal: {calories.net_calorie_goal:,} kcal")
            if calories.goal_progress is not None:
                print(f"   Goal progress: {calories.goal_progress:.1f}%")

        if calories.remaining_kilocalories is not None:
            print(f"   Remaining calories: {calories.remaining_kilocalories:,} kcal")

        # Activity level analysis
        print("\n🏃‍♂️ Activity Analysis:")
        if calories.active_kilocalories < 200:
            activity_level = "Low activity day"
            activity_icon = "😴"
        elif calories.active_kilocalories < 500:
            activity_level = "Moderate activity day"
            activity_icon = "🚶‍♂️"
        elif calories.active_kilocalories < 800:
            activity_level = "Active day"
            activity_icon = "🏃‍♂️"
        else:
            activity_level = "Very active day"
            activity_icon = "💪"

        print(f"   {activity_icon} {activity_level}")
        print(f"   Active vs Total: {calories.activity_efficiency:.1f}%")

        # BMR insights
        bmr_ratio = (
            calories.bmr_kilocalories / calories.total_kilocalories
            if calories.total_kilocalories > 0
            else 0
        )
        print("\n🧬 Metabolic Insights:")
        print(f"   BMR contribution: {bmr_ratio * 100:.1f}%")
        if bmr_ratio > 0.85:
            print("   💤 Mostly resting metabolism (low activity)")
        elif bmr_ratio > 0.70:
            print("   🚶‍♂️ Moderate activity level")
        else:
            print("   🏃‍♂️ High activity level")

    except Exception as e:
        print(f"❌ Error fetching calories data: {e}")
        print("💡 Make sure you're authenticated and have calories data available")


def weekly_calories_trends():
    """Demonstrate weekly calories trends analysis."""
    print("\n📅 Weekly Calories Trends")
    print("=" * 30)

    try:
        # Create clients and factory
        auth_client = AuthClient()
        api_client = APIClient(
            auth_client=auth_client
        )  # Metrics are auto-discovered when first accessed
        calories_accessor = api_client.metrics.get("calories")
        if not calories_accessor:
            print("❌ Calories metric not available")
            return

        # Get calories data for the last 7 days
        print("🚀 Fetching 7 days of calories data...")
        daily_data = calories_accessor.list(days=7)

        if not daily_data:
            print("❌ No weekly data available")
            return

        print("\n📊 Weekly Calories Summary:")
        print("   Date       | Total  | Active | BMR    | Efficiency")
        print("   -----------|--------|--------|--------|----------")

        total_calories = 0
        total_active = 0
        total_bmr = 0

        for day in sorted(daily_data, key=lambda x: x.calendar_date):
            total_calories += day.total_kilocalories
            total_active += day.active_kilocalories
            total_bmr += day.bmr_kilocalories

            print(
                f"   {day.calendar_date} | {day.total_kilocalories:6,} | "
                f"{day.active_kilocalories:6,} | {day.bmr_kilocalories:6,} | "
                f"{day.activity_efficiency:6.1f}%"
            )

        # Weekly averages
        days_count = len(daily_data)
        avg_total = total_calories // days_count
        avg_active = total_active // days_count
        avg_bmr = total_bmr // days_count
        avg_efficiency = (
            (total_active / total_calories * 100) if total_calories > 0 else 0
        )

        print("   -----------|--------|--------|--------|----------")
        print(
            f"   Average    | {avg_total:6,} | {avg_active:6,} | "
            f"{avg_bmr:6,} | {avg_efficiency:6.1f}%"
        )

        # Trend analysis
        if len(daily_data) >= 2:
            recent_avg = sum(day.total_kilocalories for day in daily_data[:3]) // min(
                3, len(daily_data)
            )
            older_avg = sum(day.total_kilocalories for day in daily_data[-3:]) // min(
                3, len(daily_data)
            )

            print("\n📈 Trend Analysis:")
            if recent_avg > older_avg:
                trend = recent_avg - older_avg
                print(f"   📈 Increasing: +{trend:,} kcal/day average")
            elif recent_avg < older_avg:
                trend = older_avg - recent_avg
                print(f"   📉 Decreasing: -{trend:,} kcal/day average")
            else:
                print("   ➡️ Stable calorie burn")

        # Activity insights
        print("\n🏃‍♂️ Weekly Activity Insights:")
        print(f"   Total calories burned: {total_calories:,} kcal")
        print(f"   Total active calories: {total_active:,} kcal")
        print(f"   Average daily activity: {avg_efficiency:.1f}% efficiency")

        high_activity_days = sum(
            1 for day in daily_data if day.active_kilocalories >= 400
        )
        low_activity_days = sum(
            1 for day in daily_data if day.active_kilocalories < 200
        )

        print(f"   High activity days (≥400 kcal): {high_activity_days}/{days_count}")
        print(f"   Low activity days (<200 kcal): {low_activity_days}/{days_count}")

    except Exception as e:
        print(f"❌ Error fetching weekly data: {e}")


def raw_api_data():
    """Demonstrate accessing completely raw API response."""
    print("\n🔍 Raw Calories API Response")
    print("=" * 35)

    try:
        # Create clients and factory
        auth_client = AuthClient()
        api_client = APIClient(
            auth_client=auth_client
        )  # Metrics are auto-discovered when first accessed
        # Get raw JSON response without any parsing
        calories_accessor = api_client.metrics.get("calories")
        if not calories_accessor:
            print("❌ Calories metric not available")
            return

        raw_data = calories_accessor.raw()

        if raw_data:
            print("Raw API structure:")
            print(f"   Top-level keys: {list(raw_data.keys())}")

            # Show calorie-related fields
            calorie_fields = [
                k
                for k in raw_data
                if "calorie" in k.lower() or "kilocalorie" in k.lower()
            ]
            if calorie_fields:
                print(f"   Calorie fields: {calorie_fields}")
                print("   Sample calorie data:")
                for field in calorie_fields[:5]:  # Show first 5
                    value = raw_data.get(field)
                    print(f"     {field}: {value}")

            # Show other energy-related fields
            energy_fields = [
                k
                for k in raw_data
                if any(
                    term in k.lower()
                    for term in ["active", "bmr", "wellness", "remaining", "goal"]
                )
            ]
            if energy_fields:
                print(f"   Energy-related fields: {len(energy_fields)} total")

        else:
            print("❌ No raw data available")

    except Exception as e:
        print(f"❌ Error fetching raw data: {e}")


if __name__ == "__main__":
    # Run all demos
    main()
    weekly_calories_trends()
    raw_api_data()

    print("\n💡 Modern API Notes:")
    print("   • Explicit client creation: AuthClient() and APIClient()")
    print("   • Use api_client.metrics for direct metric access")
    print("   • Calories uses standard MetricAccessor")
    print("   • Methods: .get(), .list(), .raw()")
    print("   • Direct class imports: from garmy import Calories")
    print("\n💡 Calories Data Analysis Notes:")
    print("   • All data comes directly from Garmin Connect API")
    print("   • Calories include total burned, active, and BMR components")
    print("   • BMR (Basal Metabolic Rate) represents resting energy expenditure")
    print("   • Active calories represent energy from physical activity")
    print("   • Activity efficiency = Active calories / Total calories")
    print("   • Use this raw data for your own energy expenditure analysis")
