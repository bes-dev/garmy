#!/usr/bin/env python3
"""Activities Demo - Activity List and Basic Performance Data.

==========================================================

This example demonstrates how to access activity summaries from the Garmin Connect API
using the new modern API architecture.

Perfect for tracking workout history, analyzing training patterns, and correlating
activities with wellness metrics.

Example output:
    Morning Run: 32.5 minutes (running)
    Heart Rate: 165 bpm average (142-184 range)
    Date: 2025-05-29
    Training Effect: 3.2 aerobic, 2.1 anaerobic
"""


from garmy import APIClient, AuthClient


def main():
    """Demonstrate basic Activities data access."""
    print("🏃‍♂️ Garmin Activities Demo (Modern API)")
    print("=" * 40)

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
        # Get activities accessor using modern API
        print("🔍 Getting activities accessor...")
        activities = api_client.metrics.get("activities")

        if not activities:
            print("❌ Activities metric not available")
            return

        print(f"   Accessor type: {type(activities)}")

        # Get recent activities (last 20)
        print("\n📊 Fetching recent activities...")
        recent_activities = activities.list(limit=20)

        if not recent_activities:
            print("❌ No activities found")
            print("💡 Make sure you:")
            print("   - Have recorded activities in Garmin Connect")
            print("   - Are authenticated with valid credentials")
            return

        print(f"\n📈 Found {len(recent_activities)} recent activities:")
        print("=" * 80)

        for i, activity in enumerate(recent_activities[:10], 1):  # Show first 10
            # Basic activity info
            name = activity.activity_name or "Unnamed Activity"
            duration = activity.duration_minutes
            activity_type = activity.activity_type_name
            start_date = activity.start_date

            print(f"{i:2d}. {name}")
            print(f"    Type: {activity_type}")
            print(f"    Duration: {duration:.1f} minutes")
            print(f"    Date: {start_date}")

            # Heart rate info
            if activity.has_heart_rate:
                avg_hr = activity.average_hr
                hr_range = activity.heart_rate_range
                print(f"    Heart Rate: {avg_hr:.0f} bpm avg (range: {hr_range:.0f})")
            else:
                print("    Heart Rate: No data")

            # Training effects
            if activity.aerobic_training_effect > 0:
                aerobic = activity.aerobic_training_effect
                anaerobic = activity.anaerobic_training_effect
                print(
                    f"    Training Effect: {aerobic:.1f} aerobic, {anaerobic:.1f} anaerobic"
                )

            # Stress impact
            if activity.has_stress_data:
                stress_impact = activity.stress_impact
                print(f"    Stress Impact: {stress_impact}")

            # Respiration
            if activity.has_respiration_data:
                avg_resp = activity.avg_respiration_rate
                print(f"    Respiration: {avg_resp:.1f} brpm avg")

            print()

        # Activity type analysis
        print("🔍 Activity Type Analysis:")
        type_counts = {}
        for activity in recent_activities:
            activity_type = activity.activity_type_name
            type_counts[activity_type] = type_counts.get(activity_type, 0) + 1

        for activity_type, count in sorted(
            type_counts.items(), key=lambda x: x[1], reverse=True
        ):
            print(f"   {activity_type}: {count} activities")

    except Exception as e:
        print(f"❌ Error fetching activities data: {e}")
        print("💡 Make sure you're authenticated and have activities available")


def recent_activities_by_type():
    """Demonstrate filtering activities by type."""
    print("\n🏃‍♀️ Activities by Type")
    print("=" * 30)

    try:
        # Create clients and factory
        auth_client = AuthClient()
        api_client = APIClient(
            auth_client=auth_client
        )  # Metrics are auto-discovered when first accessed
        activities = api_client.metrics.get("activities")
        if not activities:
            print("❌ Activities metric not available")
            return

        # Get running activities
        print("🏃‍♂️ Recent running activities:")
        running_activities = activities.get_by_type("running", limit=50)

        if running_activities:
            for activity in running_activities[:5]:  # Show first 5
                duration = activity.duration_minutes
                date = activity.start_date
                print(f"   {activity.activity_name}: {duration:.1f}min on {date}")
        else:
            print("   No running activities found")

        # Get cycling activities
        print("\n🚴‍♀️ Recent cycling activities:")
        cycling_activities = activities.get_by_type("cycling", limit=50)

        if cycling_activities:
            for activity in cycling_activities[:5]:  # Show first 5
                duration = activity.duration_minutes
                date = activity.start_date
                print(f"   {activity.activity_name}: {duration:.1f}min on {date}")
        else:
            print("   No cycling activities found")

    except Exception as e:
        print(f"❌ Error filtering activities by type: {e}")


def weekly_activity_summary():
    """Demonstrate getting recent activities from the last week."""
    print("\n📅 Weekly Activity Summary")
    print("=" * 35)

    try:
        # Create clients and factory
        auth_client = AuthClient()
        api_client = APIClient(
            auth_client=auth_client
        )  # Metrics are auto-discovered when first accessed
        activities = api_client.metrics.get("activities")
        if not activities:
            print("❌ Activities metric not available")
            return

        # Get activities from the last 7 days
        print("📊 Activities from the last 7 days:")
        recent = activities.get_recent(days=7, limit=50)

        if not recent:
            print("❌ No activities found in the last 7 days")
            return

        # Calculate totals
        total_duration = sum(activity.duration_minutes for activity in recent)
        total_activities = len(recent)
        avg_duration = total_duration / total_activities if total_activities > 0 else 0

        print(f"   Total activities: {total_activities}")
        print(
            f"   Total duration: {total_duration:.1f} minutes ({total_duration/60:.1f} hours)"
        )
        print(f"   Average duration: {avg_duration:.1f} minutes")

        # Group by day
        by_day = {}
        for activity in recent:
            day = activity.start_date
            if day not in by_day:
                by_day[day] = []
            by_day[day].append(activity)

        print("\n📅 Daily breakdown:")
        for day in sorted(by_day.keys(), reverse=True):
            day_activities = by_day[day]
            day_duration = sum(a.duration_minutes for a in day_activities)
            activity_types = ", ".join({a.activity_type_name for a in day_activities})
            print(
                f"   {day}: {len(day_activities)} activities, "
                f"{day_duration:.1f}min ({activity_types})"
            )

    except Exception as e:
        print(f"❌ Error getting weekly summary: {e}")


def raw_activities_data():
    """Demonstrate accessing raw activities API response."""
    print("\n🔍 Raw Activities API Response")
    print("=" * 40)

    try:
        # Create clients and factory
        auth_client = AuthClient()
        api_client = APIClient(
            auth_client=auth_client
        )  # Metrics are auto-discovered when first accessed
        activities = api_client.metrics.get("activities")
        if not activities:
            print("❌ Activities metric not available")
            return

        # Get raw JSON response without any parsing
        raw_data = activities.raw(limit=5)

        if raw_data:
            if isinstance(raw_data, list):
                print(f"Raw API returned list with {len(raw_data)} activities")
                if len(raw_data) > 0:
                    first_activity = raw_data[0]
                    print("First activity keys:", list(first_activity.keys()))
                    print(f"Activity name: {first_activity.get('activityName')}")
                    print(f"Duration: {first_activity.get('duration')} seconds")
                    print(
                        f"Activity type: {first_activity.get('activityType', {}).get('typeKey')}"
                    )
            else:
                print("Raw API keys:", list(raw_data.keys()))
        else:
            print("❌ No raw data available")

    except Exception as e:
        print(f"❌ Error fetching raw data: {e}")


if __name__ == "__main__":
    # Run all demos
    main()
    recent_activities_by_type()
    weekly_activity_summary()
    raw_activities_data()

    print("\n💡 Modern API Notes:")
    print("   • Explicit client creation: AuthClient() and APIClient()")
    print("   • Use api_client.metrics for direct metric access")
    print("   • Activities uses custom ActivitiesAccessor with special methods")
    print("   • Methods: .list(), .get_recent(), .get_by_type(), .raw()")
    print("   • Direct class imports: from garmy import ActivitySummary")
