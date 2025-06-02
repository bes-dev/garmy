#!/usr/bin/env python3
"""Metrics Synchronization Demo - Combining Multiple Data Sources.

==============================================================

This example demonstrates how to synchronize and combine data from multiple
Garmin metrics to create custom analytics. It shows the power of using garmy
as a raw data source for your own analysis rather than relying on built-in analytics.

This replaces the old Wellness composite metric with a flexible, user-controlled approach.

Example analysis:
    - Energy vs Stress correlation throughout the day
    - Optimal activity periods identification
    - Custom wellness states based on your criteria
    - Multi-metric trend analysis
"""

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from garmy import APIClient, AuthClient


def sync_body_battery_stress(date_str: Optional[str] = None) -> Dict[str, Any]:
    """
    Synchronize Body Battery and Stress data for the same time periods.

    Args:
        date_str: Date in YYYY-MM-DD format, or None for today

    Returns:
        Dictionary with synchronized data and basic analysis
    """
    try:
        # Create clients and factory
        auth_client = AuthClient()
        api_client = APIClient(
            auth_client=auth_client
        )  # Metrics are auto-discovered when first accessed
        # Get both metrics for the same date
        battery_accessor = api_client.metrics.get("body_battery")
        stress_accessor = api_client.metrics.get("stress")

        if not battery_accessor or not stress_accessor:
            return {
                "success": False,
                "error": "Required metrics not available (body_battery or stress)",
            }

        battery = battery_accessor.get(date_str) if date_str else battery_accessor.get()
        stress = stress_accessor.get(date_str) if date_str else stress_accessor.get()

        if not battery or not stress:
            return {
                "success": False,
                "error": "Missing data - ensure both Body Battery and Stress data are available",
            }

        # Verify we have the same date
        if battery.calendar_date != stress.calendar_date:
            return {
                "success": False,
                "error": (
                    f"Date mismatch: Battery({battery.calendar_date}) "
                    f"vs Stress({stress.calendar_date})"
                ),
            }

        # Create timestamp-based lookup for faster synchronization
        stress_by_timestamp = {
            reading.timestamp: reading for reading in stress.stress_readings
        }

        # Synchronize data points
        synchronized_readings = []
        for battery_reading in battery.body_battery_readings:
            stress_reading = stress_by_timestamp.get(battery_reading.timestamp)
            if stress_reading:
                synchronized_readings.append(
                    {
                        "timestamp": battery_reading.timestamp,
                        "datetime": battery_reading.datetime,
                        "energy_level": battery_reading.level,
                        "energy_status": battery_reading.status,
                        "stress_level": stress_reading.stress_level,
                        "stress_category": stress_reading.stress_category,
                        "is_rest": stress_reading.stress_level == -1,
                    }
                )

        return {
            "success": True,
            "date": battery.calendar_date,
            "synchronized_readings": synchronized_readings,
            "total_synced_points": len(synchronized_readings),
            "battery_points": len(battery.body_battery_readings),
            "stress_points": len(stress.stress_readings),
            "sync_rate": len(synchronized_readings)
            / min(len(battery.body_battery_readings), len(stress.stress_readings))
            * 100,
        }

    except Exception as e:
        return {"success": False, "error": f"Synchronization failed: {e}"}


def analyze_energy_stress_correlation(
    synced_data: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Analyze correlation between energy levels and stress throughout the day.

    Args:
        synced_data: List of synchronized readings with energy and stress data

    Returns:
        Dictionary with correlation analysis results
    """
    if not synced_data:
        return {"error": "No synchronized data provided"}

    # Filter out rest periods for active correlation analysis
    active_periods = [reading for reading in synced_data if not reading["is_rest"]]

    if len(active_periods) < 2:
        return {"error": "Insufficient active periods for correlation analysis"}

    # Calculate correlation patterns
    high_energy_low_stress = 0  # Energy >70, Stress <30
    low_energy_high_stress = 0  # Energy <30, Stress >60
    balanced_periods = 0  # Energy 40-80, Stress 20-50
    total_active = len(active_periods)

    energy_levels = []
    stress_levels = []

    for reading in active_periods:
        energy = reading["energy_level"]
        stress = reading["stress_level"]

        energy_levels.append(energy)
        stress_levels.append(stress)

        # Categorize periods
        if energy > 70 and stress < 30:
            high_energy_low_stress += 1
        elif energy < 30 and stress > 60:
            low_energy_high_stress += 1
        elif 40 <= energy <= 80 and 20 <= stress <= 50:
            balanced_periods += 1

    # Calculate simple correlation coefficient
    if len(energy_levels) > 1:
        energy_mean = sum(energy_levels) / len(energy_levels)
        stress_mean = sum(stress_levels) / len(stress_levels)

        numerator = sum(
            (e - energy_mean) * (s - stress_mean)
            for e, s in zip(energy_levels, stress_levels)
        )
        energy_variance = sum((e - energy_mean) ** 2 for e in energy_levels)
        stress_variance = sum((s - stress_mean) ** 2 for s in stress_levels)

        if energy_variance > 0 and stress_variance > 0:
            correlation = numerator / (energy_variance * stress_variance) ** 0.5
        else:
            correlation = 0
    else:
        correlation = 0

    return {
        "correlation_coefficient": correlation,
        "total_active_periods": total_active,
        "optimal_periods": high_energy_low_stress,
        "stressed_periods": low_energy_high_stress,
        "balanced_periods": balanced_periods,
        "optimal_percentage": (
            (high_energy_low_stress / total_active * 100) if total_active > 0 else 0
        ),
        "stress_percentage": (
            (low_energy_high_stress / total_active * 100) if total_active > 0 else 0
        ),
        "balance_percentage": (
            (balanced_periods / total_active * 100) if total_active > 0 else 0
        ),
        "average_energy": (
            sum(energy_levels) / len(energy_levels) if energy_levels else 0
        ),
        "average_stress": (
            sum(stress_levels) / len(stress_levels) if stress_levels else 0
        ),
    }


def identify_optimal_activity_periods(
    synced_data: List[Dict[str, Any]], min_duration_minutes: int = 30
) -> List[Dict[str, Any]]:
    """
    Identify periods optimal for physical activity (high energy, low stress).

    Args:
        synced_data: List of synchronized readings
        min_duration_minutes: Minimum duration in minutes for a period to be considered

    Returns:
        List of optimal periods with start/end times and duration
    """
    optimal_periods = []
    current_period = {
        "start_time": None,
        "start_energy": None,
        "start_stress": None,
        "end_time": None,
        "end_energy": None,
        "end_stress": None,
    }

    for reading in synced_data:
        # Define optimal conditions (customize these thresholds as needed)
        is_optimal = (
            not reading["is_rest"]
            and reading["energy_level"] > 60
            and reading["stress_level"] < 40
        )

        if is_optimal:
            if current_period["start_time"] is None:
                # Start new optimal period
                current_period.update(
                    {
                        "start_time": reading["datetime"],
                        "start_energy": reading["energy_level"],
                        "start_stress": reading["stress_level"],
                        "end_time": reading["datetime"],
                        "end_energy": reading["energy_level"],
                        "end_stress": reading["stress_level"],
                        "readings_count": 1,
                    }
                )
            else:
                # Continue optimal period
                current_period["end_time"] = reading["datetime"]
                current_period["end_energy"] = reading["energy_level"]
                current_period["end_stress"] = reading["stress_level"]
                current_period["readings_count"] += 1
        elif current_period["start_time"] is not None:
            # End optimal period and check duration
            duration = current_period["end_time"] - current_period["start_time"]
            if duration.total_seconds() >= min_duration_minutes * 60:
                current_period["duration_minutes"] = duration.total_seconds() / 60
                optimal_periods.append(current_period)
            current_period = {
                "start_time": None,
                "start_energy": None,
                "start_stress": None,
                "end_time": None,
                "end_energy": None,
                "end_stress": None,
            }

    # Handle case where optimal period continues to end of data
    if current_period["start_time"] is not None:
        duration = current_period["end_time"] - current_period["start_time"]
        if duration.total_seconds() >= min_duration_minutes * 60:
            current_period["duration_minutes"] = duration.total_seconds() / 60
            optimal_periods.append(current_period)

    return optimal_periods


def create_custom_wellness_states(synced_data: List[Dict[str, Any]]) -> Dict[str, int]:
    """
    Create custom wellness state categories based on energy and stress combinations.

    Args:
        synced_data: List of synchronized readings

    Returns:
        Dictionary with counts for each wellness state
    """
    wellness_states = {
        "Peak Performance": 0,  # High energy (>75), Low stress (<25)
        "Active Ready": 0,  # Good energy (50-75), Low stress (<35)
        "Moderate": 0,  # Medium energy (30-70), Medium stress (25-60)
        "Recovery Needed": 0,  # Low energy (<40) OR High stress (>70)
        "Rest/Sleep": 0,  # Rest periods
        "Overreaching": 0,  # High energy (>70) + High stress (>60) - potential overreaching
    }

    for reading in synced_data:
        energy = reading["energy_level"]
        stress = reading["stress_level"]

        if reading["is_rest"]:
            wellness_states["Rest/Sleep"] += 1
        elif energy > 75 and stress < 25:
            wellness_states["Peak Performance"] += 1
        elif energy >= 50 and energy <= 75 and stress < 35:
            wellness_states["Active Ready"] += 1
        elif energy > 70 and stress > 60:
            wellness_states["Overreaching"] += 1
        elif energy < 40 or stress > 70:
            wellness_states["Recovery Needed"] += 1
        else:
            wellness_states["Moderate"] += 1

    return wellness_states


def main():
    """Demonstrate metrics synchronization and custom analysis."""
    print("🔄 Garmin Metrics Synchronization Demo (Modern API)")
    print("=" * 50)

    # Create clients explicitly
    print("🔧 To use this demo with real data:")
    print("📱 First authenticate:")
    print("   auth_client = AuthClient()")
    print("   auth_client.login('your_email@example.com', 'your_password')")
    print("   api_client = APIClient(auth_client=auth_client)")
    print("   Then use api_client.metrics for data access")
    print()

    try:
        # Synchronize today's data
        print("\n📊 Synchronizing Body Battery and Stress data...")
        sync_result = sync_body_battery_stress()

        if not sync_result["success"]:
            print(f"❌ Synchronization failed: {sync_result['error']}")
            return

        synced_data = sync_result["synchronized_readings"]

        print(
            f"✅ Successfully synchronized {sync_result['total_synced_points']} data points"
        )
        print(f"   Date: {sync_result['date']}")
        print(f"   Battery readings: {sync_result['battery_points']}")
        print(f"   Stress readings: {sync_result['stress_points']}")
        print(f"   Sync rate: {sync_result['sync_rate']:.1f}%")

        # Analyze correlation
        print("\n📈 Energy-Stress Correlation Analysis:")
        correlation_results = analyze_energy_stress_correlation(synced_data)

        if "error" not in correlation_results:
            print(
                f"   Correlation coefficient: {correlation_results['correlation_coefficient']:.3f}"
            )
            print(f"   Average energy: {correlation_results['average_energy']:.1f}%")
            print(f"   Average stress: {correlation_results['average_stress']:.1f}")
            print(
                f"   Optimal periods: {correlation_results['optimal_percentage']:.1f}%"
            )
            print(
                f"   High stress periods: {correlation_results['stress_percentage']:.1f}%"
            )
            print(
                f"   Balanced periods: {correlation_results['balance_percentage']:.1f}%"
            )
        else:
            print(f"   ❌ {correlation_results['error']}")

        # Identify optimal activity periods
        print("\n🏃‍♀️ Optimal Activity Periods (30+ minutes):")
        optimal_periods = identify_optimal_activity_periods(synced_data)

        if optimal_periods:
            for i, period in enumerate(optimal_periods, 1):
                start_time = period["start_time"].strftime("%H:%M")
                end_time = period["end_time"].strftime("%H:%M")
                duration = period["duration_minutes"]
                print(
                    f"   Period {i}: {start_time}-{end_time} ({duration:.0f} minutes)"
                )
                print(
                    f"      Energy: {period['start_energy']}%-{period['end_energy']}%"
                )
                print(f"      Stress: {period['start_stress']}-{period['end_stress']}")
        else:
            print("   No optimal activity periods found today")

        # Custom wellness states
        print("\n🎯 Custom Wellness State Distribution:")
        wellness_states = create_custom_wellness_states(synced_data)
        total_readings = sum(wellness_states.values())

        for state, count in wellness_states.items():
            if count > 0:
                percentage = (count / total_readings * 100) if total_readings > 0 else 0
                print(f"   {state}: {count} readings ({percentage:.1f}%)")

        # Sample synchronized data
        print("\n📋 Sample Synchronized Data (first 5 readings):")
        print("   Time  | Energy | Status   | Stress | Category")
        print("   ------|--------|----------|--------|----------")

        for reading in synced_data[:5]:
            time_str = reading["datetime"].strftime("%H:%M")
            energy = reading["energy_level"]
            status = reading["energy_status"][:8]
            stress = "Rest" if reading["is_rest"] else f"{reading['stress_level']:2d}"
            category = reading["stress_category"]
            print(
                f"   {time_str}  | {energy:3d}%   | {status:8s} | {stress:5s}  | {category}"
            )

        if len(synced_data) > 5:
            print(f"   ... ({len(synced_data) - 5} more synchronized readings)")

    except Exception as e:
        print(f"❌ Error in synchronization demo: {e}")


def weekly_trends_analysis():
    """Demonstrate multi-day correlation analysis."""
    print("\n📅 Weekly Trends Analysis")
    print("=" * 25)

    try:
        # Analyze trends over the past week
        weekly_correlations = []

        for days_ago in range(7):
            target_date = (datetime.now() - timedelta(days=days_ago)).strftime(
                "%Y-%m-%d"
            )
            sync_result = sync_body_battery_stress(target_date)

            if sync_result["success"]:
                correlation_data = analyze_energy_stress_correlation(
                    sync_result["synchronized_readings"]
                )
                if "error" not in correlation_data:
                    weekly_correlations.append(
                        {
                            "date": target_date,
                            "correlation": correlation_data["correlation_coefficient"],
                            "avg_energy": correlation_data["average_energy"],
                            "avg_stress": correlation_data["average_stress"],
                            "optimal_pct": correlation_data["optimal_percentage"],
                        }
                    )

        if weekly_correlations:
            print("   Date       | Corr  | Avg Energy | Avg Stress | Optimal %")
            print("   -----------|-------|------------|------------|----------")

            for day in weekly_correlations:
                print(
                    f"   {day['date']} | {day['correlation']:5.2f} | "
                    f"{day['avg_energy']:8.1f}%  | {day['avg_stress']:8.1f}   | "
                    f"{day['optimal_pct']:6.1f}%"
                )
        else:
            print("   No correlation data available for the past week")

    except Exception as e:
        print(f"❌ Error in weekly analysis: {e}")


if __name__ == "__main__":
    main()
    weekly_trends_analysis()

    print("\n💡 Modern API Notes:")
    print("   • Explicit client creation: AuthClient() and APIClient()")
    print("   • Use api_client.metrics for direct metric access")
    print("   • All metrics use standard MetricAccessor interface")
    print("   • Methods: .get(), .list(), .raw()")
    print("   • Direct class imports: from garmy import BodyBattery, Stress")
    print("\n💡 Synchronization Notes:")
    print("   • Body Battery and Stress use the same API endpoint for perfect sync")
    print("   • Timestamps match exactly - no interpolation needed")
    print("   • All thresholds are customizable for your personal preferences")
    print("   • This approach replaces rigid Wellness analytics with flexible analysis")
    print("   • You can combine ANY metrics that share timestamp synchronization")
