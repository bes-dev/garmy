#!/usr/bin/env python3
"""Sleep Phases Analysis Script.

============================

This script collects sleep phase data from Garmin Connect API
for a user-specified date range and saves it to a CSV file.

Features:
- Interactive date range selection
- Progress bar using tqdm
- Sleep phase duration analysis (Deep, Light, REM, Awake)
- CSV export with daily breakdown
- Error handling for missing data days

Usage:
    python sleep_phases_analysis.py
"""

import csv
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

from tqdm import tqdm

from garmy import APIClient, AuthClient


def get_sleep_phases_for_date(target_date: date) -> Optional[Dict[str, any]]:
    """
    Get sleep phases data for a specific date.

    Args:
        target_date: Date to fetch sleep data for

    Returns:
        Dictionary with sleep phases data or None if no data
    """
    try:
        # Create clients
        auth_client = AuthClient()
        api_client = APIClient(auth_client=auth_client)

        sleep_accessor = api_client.metrics.get("sleep")
        if not sleep_accessor:
            print(f"\n   ❌ Sleep metric not available for {target_date}")
            return None

        sleep_data = sleep_accessor.get(target_date)
        if not sleep_data or not sleep_data.sleep_summary:
            return None

        summary = sleep_data.sleep_summary

        # Convert seconds to hours for easier reading
        deep_hours = (
            summary.deep_sleep_seconds / 3600 if summary.deep_sleep_seconds else 0
        )
        light_hours = (
            summary.light_sleep_seconds / 3600 if summary.light_sleep_seconds else 0
        )
        rem_hours = summary.rem_sleep_seconds / 3600 if summary.rem_sleep_seconds else 0
        awake_hours = (
            summary.awake_sleep_seconds / 3600 if summary.awake_sleep_seconds else 0
        )
        total_hours = (
            summary.sleep_time_seconds / 3600 if summary.sleep_time_seconds else 0
        )

        return {
            "date": target_date.strftime("%Y-%m-%d"),
            "total_sleep_hours": round(total_hours, 2),
            "deep_sleep_hours": round(deep_hours, 2),
            "light_sleep_hours": round(light_hours, 2),
            "rem_sleep_hours": round(rem_hours, 2),
            "awake_hours": round(awake_hours, 2),
            "deep_percentage": round(
                (deep_hours / total_hours * 100) if total_hours > 0 else 0, 1
            ),
            "light_percentage": round(
                (light_hours / total_hours * 100) if total_hours > 0 else 0, 1
            ),
            "rem_percentage": round(
                (rem_hours / total_hours * 100) if total_hours > 0 else 0, 1
            ),
            "awake_percentage": round(
                (awake_hours / total_hours * 100) if total_hours > 0 else 0, 1
            ),
            "sleep_efficiency": (
                round(summary.sleep_efficiency_percentage, 1)
                if hasattr(summary, "sleep_efficiency_percentage")
                and summary.sleep_efficiency_percentage
                else 0
            ),
            "awake_count": summary.awake_count if summary.awake_count else 0,
            "sleep_start": (
                summary.sleep_start_datetime_local.strftime("%H:%M")
                if hasattr(summary, "sleep_start_datetime_local")
                and summary.sleep_start_datetime_local
                else ""
            ),
            "sleep_end": (
                summary.sleep_end_datetime_local.strftime("%H:%M")
                if hasattr(summary, "sleep_end_datetime_local")
                and summary.sleep_end_datetime_local
                else ""
            ),
        }

    except Exception as e:
        print(f"\n   ⚠️ Error fetching data for {target_date}: {e}")
        return None


def collect_sleep_data(start_date: date, end_date: date) -> List[Dict[str, any]]:
    """
    Collect sleep data for a date range with progress bar.

    Args:
        start_date: Start date for data collection
        end_date: End date for data collection

    Returns:
        List of sleep data dictionaries
    """
    sleep_data = []
    current_date = start_date
    total_days = (end_date - start_date).days + 1

    print(
        f"📊 Collecting sleep data from {start_date} to {end_date} ({total_days} days)"
    )

    # Create progress bar
    with tqdm(total=total_days, desc="Fetching sleep data", unit="day") as pbar:
        while current_date <= end_date:
            pbar.set_postfix(date=current_date.strftime("%Y-%m-%d"))

            day_data = get_sleep_phases_for_date(current_date)
            if day_data:
                sleep_data.append(day_data)

            current_date += timedelta(days=1)
            pbar.update(1)

    return sleep_data


def save_to_csv(
    sleep_data: List[Dict[str, any]], filename: str = "sleep_phases_analysis.csv"
) -> str:
    """
    Save sleep data to CSV file.

    Args:
        sleep_data: List of sleep data dictionaries
        filename: Output CSV filename

    Returns:
        Full path to the saved CSV file
    """
    if not sleep_data:
        raise ValueError("No sleep data to save")

    # Get the directory where this script is located
    script_dir = Path(__file__).parent.resolve()
    csv_path = script_dir / filename

    # Define CSV columns
    fieldnames = [
        "date",
        "total_sleep_hours",
        "deep_sleep_hours",
        "light_sleep_hours",
        "rem_sleep_hours",
        "awake_hours",
        "deep_percentage",
        "light_percentage",
        "rem_percentage",
        "awake_percentage",
        "sleep_efficiency",
        "awake_count",
        "sleep_start",
        "sleep_end",
    ]

    with csv_path.open("w", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(sleep_data)

    return csv_path


def print_summary_stats(sleep_data: List[Dict[str, any]]):
    """Print summary statistics about the collected sleep data."""
    if not sleep_data:
        print("❌ No sleep data collected")
        return

    total_days = len(sleep_data)

    # Calculate averages
    avg_total = sum(day["total_sleep_hours"] for day in sleep_data) / total_days
    avg_deep = sum(day["deep_sleep_hours"] for day in sleep_data) / total_days
    avg_light = sum(day["light_sleep_hours"] for day in sleep_data) / total_days
    avg_rem = sum(day["rem_sleep_hours"] for day in sleep_data) / total_days
    avg_awake = sum(day["awake_hours"] for day in sleep_data) / total_days
    avg_efficiency = sum(day["sleep_efficiency"] for day in sleep_data) / total_days

    print(f"\n📈 Sleep Data Summary ({total_days} days):")
    print("=" * 50)
    print(f"🛌 Average total sleep: {avg_total:.1f} hours")
    print(
        f"🔵 Average deep sleep: {avg_deep:.1f} hours ({avg_deep/avg_total*100:.1f}%)"
    )
    print(
        f"🟡 Average light sleep: {avg_light:.1f} hours ({avg_light/avg_total*100:.1f}%)"
    )
    print(f"🟣 Average REM sleep: {avg_rem:.1f} hours ({avg_rem/avg_total*100:.1f}%)")
    print(
        f"🔴 Average awake time: {avg_awake:.1f} hours ({avg_awake/avg_total*100:.1f}%)"
    )
    print(f"📊 Average sleep efficiency: {avg_efficiency:.1f}%")

    # Find best and worst sleep days
    best_sleep = max(sleep_data, key=lambda x: x["total_sleep_hours"])
    worst_sleep = min(sleep_data, key=lambda x: x["total_sleep_hours"])
    best_efficiency = max(sleep_data, key=lambda x: x["sleep_efficiency"])

    print(
        f"\n🏆 Best sleep day: {best_sleep['date']} ({best_sleep['total_sleep_hours']:.1f}h)"
    )
    print(
        f"😴 Worst sleep day: {worst_sleep['date']} ({worst_sleep['total_sleep_hours']:.1f}h)"
    )
    print(
        f"⭐ Best efficiency: {best_efficiency['date']} ({best_efficiency['sleep_efficiency']:.1f}%)"
    )


def get_date_input(prompt: str, default_date: date = None) -> date:
    """Get a date input from the user with validation."""
    while True:
        if default_date:
            date_str = input(
                f"{prompt} (YYYY-MM-DD) [default: {default_date}]: "
            ).strip()
            if not date_str:
                return default_date
        else:
            date_str = input(f"{prompt} (YYYY-MM-DD): ").strip()

        try:
            parsed_date = datetime.strptime(date_str, "%Y-%m-%d").date()
            return parsed_date
        except ValueError:
            print("❌ Invalid date format. Please use YYYY-MM-DD format.")


def get_date_range() -> tuple[date, date]:
    """Get start and end dates from user input."""
    print("\n📅 Date Range Selection")
    print("-" * 30)

    # Default dates
    default_start = date.today() - timedelta(days=30)  # 30 days ago
    default_end = date.today()

    print("Select the date range for sleep analysis:")
    start_date = get_date_input("Start date", default_start)

    # Validate end date is after start date
    while True:
        end_date = get_date_input("End date", default_end)
        if end_date >= start_date:
            break
        print(f"❌ End date must be on or after start date ({start_date})")

    return start_date, end_date


def main():
    """Run the sleep phases analysis."""
    print("🌙 Garmin Sleep Phases Analysis")
    print("=" * 40)
    print("This tool analyzes your sleep phases data from Garmin Connect.")
    print("You'll be able to specify the date range for analysis.")

    # Get date range from user
    start_date, end_date = get_date_range()

    total_days = (end_date - start_date).days + 1
    print(f"\n📊 Analysis Settings:")
    print(f"   Start date: {start_date}")
    print(f"   End date: {end_date}")
    print(f"   Total days: {total_days}")
    print("\n📱 Make sure you're authenticated with Garmin Connect")

    try:
        # Test authentication by trying to get today's data
        print("\n🔐 Testing Garmin Connect authentication...")
        # Create clients
        auth_client = AuthClient()
        api_client = APIClient(auth_client=auth_client)

        sleep_accessor = api_client.metrics.get("sleep")
        if not sleep_accessor:
            print("❌ Sleep metric not available - cannot proceed")
            return

        test_data = sleep_accessor.get()
        if not test_data:
            print("⚠️ No sleep data available for today - continuing anyway")
        else:
            print("✅ Authentication successful")

        # Collect sleep data
        sleep_data = collect_sleep_data(start_date, end_date)

        if not sleep_data:
            print("\n❌ No sleep data collected for the specified period")
            print("💡 Make sure you:")
            print("   - Have a compatible Garmin device")
            print("   - Wore your device during sleep")
            print("   - Have sleep data for some days in the period")
            return

        # Save to CSV
        print(f"\n💾 Saving {len(sleep_data)} days of sleep data to CSV...")
        csv_path = save_to_csv(sleep_data)
        print(f"✅ Data saved to: {csv_path}")

        # Print summary statistics
        print_summary_stats(sleep_data)

        print("\n💡 CSV file contains detailed daily sleep phase data")
        print("   You can open it in Excel, Google Sheets, or any data analysis tool")

    except KeyboardInterrupt:
        print("\n\n⏹️ Analysis interrupted by user")
    except Exception as e:
        print(f"\n❌ Error during analysis: {e}")
        print("💡 Make sure you're authenticated with Garmin Connect")


if __name__ == "__main__":
    main()
