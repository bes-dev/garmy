#!/usr/bin/env python3
"""Body Battery Data Demo - Energy Level Raw Data.

======================================================

This example demonstrates how to access Body Battery data directly from the
Garmin Connect API using the new modern API architecture.

Body Battery tracks energy levels throughout the day, showing charging and
draining periods based on stress, activity, and recovery patterns.

Example output:
    Date: 2025-05-29
    Total readings: 145
    Current level: 67%
    Status: charging
"""


from garmy import APIClient, AuthClient


def main():
    """Demonstrate raw Body Battery data access."""
    print("🔋 Garmin Body Battery Demo (Modern API)")
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
        # Get Body Battery accessor using modern API
        print("🔍 Getting Body Battery accessor...")
        body_battery = api_client.metrics.get("body_battery")

        if not body_battery:
            print("❌ Body Battery metric not available")
            return

        print(f"   Accessor type: {type(body_battery)}")

        # Get today's Body Battery data
        print("\n📊 Fetching today's Body Battery data...")
        battery = body_battery.get()

        if not battery:
            print("❌ No Body Battery data available for today")
            print("💡 Make sure you:")
            print("   - Wore your device throughout the day")
            print("   - Have a compatible Garmin device")
            print("   - Device has Body Battery feature enabled")
            print("   - Are authenticated with valid credentials")
            return

        # Calculate Body Battery summary from readings
        readings = battery.body_battery_readings
        if not readings:
            print("❌ No Body Battery readings available")
            return

        levels = [r.level for r in readings]
        start_level = readings[0].level
        end_level = readings[-1].level
        highest_level = max(levels)
        lowest_level = min(levels)

        print("\n📈 Body Battery Summary:")
        print(f"   Date: {battery.calendar_date}")
        print(f"   Start Level: {start_level}%")
        print(f"   End Level: {end_level}%")
        print(f"   Highest Level: {highest_level}%")
        print(f"   Lowest Level: {lowest_level}%")
        print(f"   Net Change: {end_level - start_level:+d}%")
        print(f"   Total Readings: {len(readings)}")

        # Show body battery readings if available
        if battery.body_battery_readings:
            readings = battery.body_battery_readings
            print("\n📊 Body Battery Readings:")
            print(f"   Total readings: {len(readings)}")

            # Show first and last few readings
            print("\n   First 3 readings:")
            for reading in readings[:3]:
                time_str = (
                    reading.datetime.strftime("%H:%M")
                    if hasattr(reading, "datetime")
                    else "Unknown"
                )
                print(f"     {time_str}: {reading.level}% (status: {reading.status})")

            print("\n   Last 3 readings:")
            for reading in readings[-3:]:
                time_str = (
                    reading.datetime.strftime("%H:%M")
                    if hasattr(reading, "datetime")
                    else "Unknown"
                )
                print(f"     {time_str}: {reading.level}% (status: {reading.status})")

            # Current status
            if readings:
                current = readings[-1]
                print(
                    f"\n   Current Status: {current.level}% (status: {current.status})"
                )
        else:
            print("\n   No detailed readings available")

        # Body Battery insights
        print("\n💡 Body Battery Insights:")
        net_change = end_level - start_level
        if net_change > 0:
            print(f"   📈 Net gain: +{net_change}% (good recovery day)")
        elif net_change < 0:
            print(f"   📉 Net loss: {net_change}% (energy depleted)")
        else:
            print("   ⚖️ Net neutral: No change (balanced day)")

        # Calculate charging vs draining periods (simplified)
        charging_count = sum(
            1 for r in readings if r.status and "charg" in str(r.status).lower()
        )
        draining_count = len(readings) - charging_count

        if charging_count > draining_count:
            print("   ✅ More charging periods than draining (good recovery)")
        elif charging_count < draining_count:
            print("   ⚠️ More draining periods than charging (consider more rest)")
        else:
            print("   📊 Balanced charging and draining periods")

        # Energy level categories
        current_level = end_level
        if current_level >= 75:
            print(f"   🟢 High energy level ({current_level}%) - ready for activities")
        elif current_level >= 50:
            print(f"   🟡 Moderate energy level ({current_level}%) - pace yourself")
        elif current_level >= 25:
            print(
                f"   🟠 Low energy level ({current_level}%) - consider light activities"
            )
        else:
            print(f"   🔴 Very low energy level ({current_level}%) - rest recommended")

    except Exception as e:
        print(f"❌ Error fetching Body Battery data: {e}")
        print("💡 Make sure you're authenticated and have Body Battery data available")


def weekly_body_battery_trends():
    """Demonstrate accessing multiple days of Body Battery data."""
    print("\n📅 Weekly Body Battery Trends")
    print("=" * 40)

    try:
        # Create clients and factory
        auth_client = AuthClient()
        api_client = APIClient(
            auth_client=auth_client
        )  # Metrics are auto-discovered when first accessed
        body_battery = api_client.metrics.get("body_battery")
        if not body_battery:
            print("❌ Body Battery metric not available")
            return

        # Get Body Battery data for the last 7 days
        print("🚀 Fetching 7 days of Body Battery data...")
        weekly_data = body_battery.list(days=7)

        if not weekly_data:
            print("❌ No Body Battery data available for the past week")
            return

        print("   Date       | Start | End | High | Low | Net | Readings")
        print("   -----------|-------|-----|------|-----|-----|----------")

        for battery in weekly_data:
            readings = battery.body_battery_readings
            if readings:
                levels = [r.level for r in readings]
                start = readings[0].level
                end = readings[-1].level
                high = max(levels)
                low = min(levels)
                net = end - start
                readings_count = len(readings)

                net_str = f"+{net}" if net >= 0 else str(net)
                print(
                    f"   {battery.calendar_date} | {start:>5}%| {end:>3}%| "
                    f"{high:>4}%| {low:>3}%| {net_str:>3} | {readings_count:>8}"
                )
            else:
                print(f"   {battery.calendar_date} | No readings available")

        # Weekly insights
        if len(weekly_data) > 1:
            valid_batteries = []
            for b in weekly_data:
                if b.body_battery_readings:
                    readings = b.body_battery_readings
                    levels = [r.level for r in readings]
                    valid_batteries.append(
                        {"start": readings[0].level, "end": readings[-1].level}
                    )

            if valid_batteries:
                avg_start = sum(b["start"] for b in valid_batteries) / len(
                    valid_batteries
                )
                avg_end = sum(b["end"] for b in valid_batteries) / len(valid_batteries)
                avg_net = avg_end - avg_start

                print("\n📊 Weekly Averages:")
                print(f"   Start Level: {avg_start:.1f}%")
                print(f"   End Level: {avg_end:.1f}%")
                print(f"   Net Change: {avg_net:+.1f}%")

                if avg_net > 5:
                    print("   💪 Great weekly recovery pattern!")
                elif avg_net > 0:
                    print("   ✅ Positive weekly recovery trend")
                elif avg_net > -5:
                    print("   ⚖️ Stable energy levels")
                else:
                    print("   ⚠️ Weekly energy depletion - consider more rest")

    except Exception as e:
        print(f"❌ Error fetching weekly Body Battery data: {e}")


def raw_body_battery_data():
    """Demonstrate accessing raw Body Battery API response."""
    print("\n🔍 Raw Body Battery API Response")
    print("=" * 40)

    try:
        # Create clients and factory
        auth_client = AuthClient()
        api_client = APIClient(
            auth_client=auth_client
        )  # Metrics are auto-discovered when first accessed
        body_battery = api_client.metrics.get("body_battery")
        if not body_battery:
            print("❌ Body Battery metric not available")
            return

        # Get raw JSON response without any parsing
        raw_data = body_battery.raw()

        if raw_data:
            print("Raw API keys:", list(raw_data.keys()))
            print(f"Calendar date: {raw_data.get('calendarDate')}")

            # Body Battery values are in bodyBatteryValuesArray
            bb_values = raw_data.get("bodyBatteryValuesArray", [])
            if bb_values:
                # Calculate start/end levels from readings
                levels = [
                    reading[2] for reading in bb_values if len(reading) > 2
                ]  # Level is at index 2
                start_level = levels[0] if levels else None
                end_level = levels[-1] if levels else None

                print(f"Start level: {start_level}%")
                print(f"End level: {end_level}%")
                if start_level is not None and end_level is not None:
                    net_change = end_level - start_level
                    print(f"Net change: {net_change:+d}%")

            # Show readings structure
            readings = bb_values
            if readings:
                print("\nReadings structure (first item):")
                first_reading = readings[0]
                print("  Format: [timestamp, status, level, version]")
                print(f"  Example: {first_reading}")
                if len(first_reading) >= 3:
                    print(f"  Timestamp: {first_reading[0]}")
                    print(f"  Status: {first_reading[1]}")
                    print(f"  Level: {first_reading[2]}%")
                    if len(first_reading) > 3:
                        print(f"  Version: {first_reading[3]}")
        else:
            print("❌ No raw data available")

    except Exception as e:
        print(f"❌ Error fetching raw Body Battery data: {e}")


def body_battery_analysis():
    """Demonstrate detailed Body Battery analysis."""
    print("\n🔬 Detailed Body Battery Analysis")
    print("=" * 40)

    try:
        # Create clients and factory
        auth_client = AuthClient()
        api_client = APIClient(
            auth_client=auth_client
        )  # Metrics are auto-discovered when first accessed
        body_battery = api_client.metrics.get("body_battery")
        if not body_battery:
            print("❌ Body Battery metric not available")
            return

        # Get today's data
        battery = body_battery.get()
        if not battery or not battery.body_battery_readings:
            print("❌ No detailed Body Battery readings available")
            return

        readings = battery.body_battery_readings

        # Analyze charging vs draining periods based on status
        charging_periods = []
        draining_periods = []

        for reading in readings:
            if "charg" in str(reading.status).lower():
                charging_periods.append(reading)
            else:
                draining_periods.append(reading)

        print("📊 Body Battery Pattern Analysis:")
        print(f"   Total readings: {len(readings)}")
        print(f"   Charging periods: {len(charging_periods)}")
        print(f"   Draining periods: {len(draining_periods)}")

        # Find peak charging and draining
        if charging_periods:
            max_charge_reading = max(charging_periods, key=lambda x: x.level)
            print(f"   Peak charge: {max_charge_reading.level}%")

        if draining_periods:
            min_drain_reading = min(draining_periods, key=lambda x: x.level)
            print(f"   Lowest drain: {min_drain_reading.level}%")

        # Energy distribution
        high_energy = [r for r in readings if r.level >= 75]
        medium_energy = [r for r in readings if 50 <= r.level < 75]
        low_energy = [r for r in readings if r.level < 50]

        total_readings = len(readings)
        print("\n⚡ Energy Distribution:")
        print(
            f"   High energy (75%+): {len(high_energy)}/{total_readings} "
            f"({len(high_energy)/total_readings*100:.1f}%)"
        )
        print(
            f"   Medium energy (50-74%): {len(medium_energy)}/{total_readings} "
            f"({len(medium_energy)/total_readings*100:.1f}%)"
        )
        print(
            f"   Low energy (<50%): {len(low_energy)}/{total_readings} "
            f"({len(low_energy)/total_readings*100:.1f}%)"
        )

        # Recovery insights
        if len(high_energy) > len(low_energy):
            print("\n💪 Analysis: Good energy management day!")
        elif len(low_energy) > len(high_energy):
            print("\n🔋 Analysis: Energy-depleting day - consider more recovery")
        else:
            print("\n⚖️ Analysis: Balanced energy day")

    except Exception as e:
        print(f"❌ Error in Body Battery analysis: {e}")


if __name__ == "__main__":
    # Run all demos
    main()
    weekly_body_battery_trends()
    raw_body_battery_data()
    body_battery_analysis()

    print("\n💡 Modern API Notes:")
    print("   • Explicit client creation: AuthClient() and APIClient()")
    print("   • Use api_client.metrics for direct metric access")
    print("   • Body Battery uses standard MetricAccessor")
    print("   • Methods: .get(), .list(), .raw()")
    print("   • Direct class imports: from garmy import BodyBattery")
