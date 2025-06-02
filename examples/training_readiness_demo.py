#!/usr/bin/env python3
"""Training Readiness Data Demo - Modern API.

=========================================

This example demonstrates how to access Training Readiness data using the new
modern Garpy architecture with explicit client management and auto-discovery.

Training Readiness combines multiple factors including sleep quality, HRV status,
recovery time, training load, and stress to provide a comprehensive assessment.

Example output:
    Score: 78/100
    Level: READY
    Sleep Score: 85
    HRV Factor: 72%
"""


from garmy import APIClient, AuthClient, MetricDiscovery


def main():
    """Demonstrate modern Training Readiness data access."""
    print("🏃‍♀️ Garmin Training Readiness Demo (Modern API)")
    print("=" * 55)

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
        # Get training readiness directly from client metrics
        print("🔍 Getting training readiness...")
        training_readiness = api_client.metrics.get("training_readiness")

        if not training_readiness:
            print("❌ Training readiness metric not available")
            return

        print(f"   Accessor type: {type(training_readiness)}")

        # Get today's training readiness data
        print("\n📊 Fetching today's training readiness data...")
        readiness_data = training_readiness.get()

        if not readiness_data:
            print("❌ No training readiness data available for today")
            print("💡 Make sure you:")
            print(
                "   - Have a compatible Garmin device (Forerunner, Fenix, Epix, etc.)"
            )
            print("   - Wore your device during sleep")
            print("   - Have sufficient activity and sleep history")
            print("   - Are authenticated with valid credentials")
            return

        # Handle if API returns a list
        if isinstance(readiness_data, list):
            if len(readiness_data) == 0:
                print("❌ No training readiness data available for today")
                return
            readiness = readiness_data[0]  # Take the first (most recent) item
        else:
            readiness = readiness_data

        # Display training readiness summary
        print("\n📈 Training Readiness Summary:")
        print(f"   Date: {readiness.calendar_date}")
        print(f"   Score: {readiness.score}/100")
        print(f"   Level: {readiness.level}")
        print(f"   User Profile: {readiness.user_profile_pk}")

        # Display Garmin's feedback
        print("\n💬 Garmin Feedback:")
        if readiness.feedback_short:
            print(f"   Short: {readiness.feedback_short}")
        if readiness.feedback_long:
            print(f"   Long: {readiness.feedback_long}")

        # Display contributing factors (if available)
        print("\n🔍 Contributing Factors:")
        factors = []

        if hasattr(readiness, "sleep_score") and readiness.sleep_score is not None:
            factors.append(f"Sleep Score: {readiness.sleep_score}")
        if (
            hasattr(readiness, "hrv_factor_percent")
            and readiness.hrv_factor_percent is not None
        ):
            factors.append(f"HRV Factor: {readiness.hrv_factor_percent}%")
        if hasattr(readiness, "recovery_time") and readiness.recovery_time is not None:
            factors.append(f"Recovery Time: {readiness.recovery_time}h")
        if (
            hasattr(readiness, "acwr_factor_percent")
            and readiness.acwr_factor_percent is not None
        ):
            factors.append(f"Training Load Factor: {readiness.acwr_factor_percent}%")
        if (
            hasattr(readiness, "stress_history_factor_percent")
            and readiness.stress_history_factor_percent is not None
        ):
            factors.append(f"Stress Factor: {readiness.stress_history_factor_percent}%")

        if factors:
            for factor in factors:
                print(f"   {factor}")
        else:
            print("   No individual factor data available")

        # Display readiness categories
        print("\n🎯 Readiness Categories:")
        if readiness.score >= 75:
            print("   ✅ Ready for high intensity training (75-100)")
        elif readiness.score >= 50:
            print("   🟡 Moderate training recommended (50-74)")
        else:
            print("   🔴 Recovery or low intensity recommended (0-49)")

        # Show timestamps if available
        if hasattr(readiness, "timestamp") and readiness.timestamp:
            print("\n⏰ Measurement Time:")
            print(f"   Timestamp: {readiness.timestamp}")

    except Exception as e:
        print(f"❌ Error fetching training readiness data: {e}")
        print(
            "💡 Make sure you're authenticated and have training readiness data available"
        )


def weekly_readiness_data():
    """Demonstrate accessing multiple days of training readiness data."""
    print("\n📅 Weekly Training Readiness Trends")
    print("=" * 45)

    try:
        # Create clients and factory
        auth_client = AuthClient()
        api_client = APIClient(auth_client=auth_client)
        # Metrics are auto-discovered when first accessed
        # Use api_client.metrics directly

        # Get training readiness accessor
        training_readiness = api_client.metrics.get("training_readiness")

        if not training_readiness:
            print("❌ Training readiness metric not available")
            return

        # Get training readiness data for the last 7 days
        print("🚀 Fetching 7 days of data using list method...")
        weekly_data = training_readiness.list(days=7)

        if not weekly_data:
            print("❌ No training readiness data available for the past week")
            return

        print("   Date       | Score | Level    | Sleep | HRV")
        print("   -----------|-------|----------|-------|-----")

        for readiness in weekly_data:
            score = str(readiness.score) if readiness.score is not None else "--"
            level = readiness.level[:8] if readiness.level else "N/A"

            # Get sleep and HRV if available
            sleep_score = "--"
            hrv_factor = "--"

            if hasattr(readiness, "sleep_score") and readiness.sleep_score is not None:
                sleep_score = str(readiness.sleep_score)
            if (
                hasattr(readiness, "hrv_factor_percent")
                and readiness.hrv_factor_percent is not None
            ):
                hrv_factor = f"{readiness.hrv_factor_percent}%"

            print(
                f"   {readiness.calendar_date} | {score:>5} | {level:8s} | "
                f"{sleep_score:>5} | {hrv_factor:>4}"
            )

    except Exception as e:
        print(f"❌ Error fetching weekly training readiness data: {e}")


def raw_api_data():
    """Demonstrate accessing completely raw API response."""
    print("\n🔍 Raw API Response")
    print("=" * 30)

    try:
        # Create clients and factory
        auth_client = AuthClient()
        api_client = APIClient(auth_client=auth_client)
        # Metrics are auto-discovered when first accessed
        # Use api_client.metrics directly

        # Get training readiness accessor
        training_readiness = api_client.metrics.get("training_readiness")

        if not training_readiness:
            print("❌ Training readiness metric not available")
            return

        # Get raw JSON response without any parsing
        raw_data = training_readiness.raw()

        if raw_data:
            # Handle if API returns a list
            if isinstance(raw_data, list):
                if len(raw_data) > 0:
                    data = raw_data[0]  # Take first item
                    print("Raw API structure: List with", len(raw_data), "items")
                    print("First item keys:", list(data.keys()))
                    print(f"Calendar date: {data.get('calendarDate')}")
                    print(f"Score: {data.get('score')}")
                    print(f"Level: {data.get('level')}")
                    print(f"User Profile PK: {data.get('userProfilePk')}")

                    # Show available factor keys
                    factor_keys = [
                        key
                        for key in data
                        if "factor" in key.lower() or "score" in key.lower()
                    ]
                    if factor_keys:
                        print(f"Available factor keys: {factor_keys}")
                else:
                    print("Raw API returned empty list")
            else:
                print("Raw API keys:", list(raw_data.keys()))
                print(f"Calendar date: {raw_data.get('calendarDate')}")
                print(f"Score: {raw_data.get('score')}")
                print(f"Level: {raw_data.get('level')}")
                print(f"User Profile PK: {raw_data.get('userProfilePk')}")

                # Show available factor keys
                factor_keys = [
                    key
                    for key in raw_data
                    if "factor" in key.lower() or "score" in key.lower()
                ]
                if factor_keys:
                    print(f"Available factor keys: {factor_keys}")
        else:
            print("❌ No raw data available")

    except Exception as e:
        print(f"❌ Error fetching raw data: {e}")


def comprehensive_readiness_analysis():
    """Demonstrate comprehensive readiness analysis with related metrics."""
    print("\n🔬 Comprehensive Readiness Analysis")
    print("=" * 45)

    try:
        # Create clients and factory
        auth_client = AuthClient()
        api_client = APIClient(auth_client=auth_client)
        # Metrics are auto-discovered when first accessed
        # Use api_client.metrics directly

        # Get multiple metric accessors using modern API
        print("🚀 Getting metric accessors...")

        training_readiness = api_client.metrics.get("training_readiness")
        sleep = api_client.metrics.get("sleep")
        hrv = api_client.metrics.get("hrv")
        stress = api_client.metrics.get("stress")
        body_battery = api_client.metrics.get("body_battery")

        # Fetch data from each metric
        print("📊 Fetching data from multiple metrics...")

        try:
            readiness_data = training_readiness.get() if training_readiness else None
            sleep_data = sleep.get() if sleep else None
            hrv_data = hrv.get() if hrv else None
            stress_data = stress.get() if stress else None
            body_battery_data = body_battery.get() if body_battery else None
        except Exception as e:
            print(f"   ❌ Error fetching data: {e}")
            print("   💡 Authentication required to fetch actual data")
            return

        # Handle list responses
        if isinstance(readiness_data, list) and len(readiness_data) > 0:
            readiness = readiness_data[0]
        elif not isinstance(readiness_data, list):
            readiness = readiness_data
        else:
            readiness = None

        print("\n📊 Cross-metric Readiness Analysis:")

        # Training Readiness
        if readiness:
            print(f"   Training Readiness: {readiness.score}/100 ({readiness.level})")
        else:
            print("   Training Readiness: No data available")

        # Sleep correlation
        if sleep_data:
            if hasattr(sleep_data, "sleep_summary"):
                efficiency = sleep_data.sleep_summary.sleep_efficiency_percentage
                duration = sleep_data.sleep_duration_hours
                print(f"   Sleep: {duration:.1f}h, {efficiency:.1f}% efficiency")
            else:
                print("   Sleep: Data available (check structure)")
        else:
            print("   Sleep: No data available")

        # HRV correlation
        if hrv_data:
            if hasattr(hrv_data, "hrv_summary"):
                print(
                    f"   HRV: {hrv_data.hrv_summary.status}, "
                    f"{hrv_data.hrv_summary.last_night_avg}ms avg"
                )
            else:
                print("   HRV: Data available (check structure)")
        else:
            print("   HRV: No data available")

        # Stress correlation
        if stress_data:
            if hasattr(stress_data, "avg_stress_level"):
                print(
                    f"   Stress: Avg {stress_data.avg_stress_level}, "
                    f"Max {stress_data.max_stress_level}"
                )
            else:
                print("   Stress: Data available (check structure)")
        else:
            print("   Stress: No data available")

        # Body Battery correlation
        if body_battery_data:
            if (
                hasattr(body_battery_data, "body_battery_readings")
                and body_battery_data.body_battery_readings
            ):
                current_bb = body_battery_data.body_battery_readings[-1].level
                print(f"   Body Battery: {current_bb}%")
            else:
                print("   Body Battery: Data available (check structure)")
        else:
            print("   Body Battery: No data available")

        # Comprehensive insight
        if readiness and sleep_data:
            print("\n💡 Training Insights:")

            sleep_duration = (
                getattr(sleep_data, "sleep_duration_hours", 0) if sleep_data else 0
            )

            if readiness.score >= 75 and sleep_duration >= 7:
                print(
                    "   🟢 Excellent readiness with good sleep - ideal for intense training"
                )
            elif readiness.score >= 50 and sleep_duration >= 6:
                print("   🟡 Moderate readiness - consider medium intensity training")
            elif readiness.score < 50 or sleep_duration < 6:
                print("   🔴 Low readiness or poor sleep - prioritize recovery")
            else:
                print("   📊 Review individual factors for personalized insights")

    except Exception as e:
        print(f"❌ Comprehensive analysis failed: {e}")


def modern_api_showcase():
    """Showcase the modern API features."""
    print("\n🆕 Modern API Showcase")
    print("=" * 30)

    try:
        # Show metric discovery
        print("📋 Discovering available metrics...")
        discovered = MetricDiscovery.discover_metrics("garmy.metrics")

        print("📋 Available metrics:")
        for metric_name in sorted(discovered.keys()):
            print(f"   - {metric_name}")

        print(f"\n📊 Total metrics discovered: {len(discovered)}")

        # Show metrics summary
        print("\n📋 Metrics Summary:")
        MetricDiscovery.print_metrics_info(discovered)

        # Show how to access any metric
        print("\n🔍 Example: Using metrics directly")
        auth_client = AuthClient()
        api_client = APIClient(auth_client=auth_client)
        # Metrics are auto-discovered when first accessed
        # Use api_client.metrics directly

        example_metrics = ["training_readiness", "activities", "hrv"]
        for metric_name in example_metrics:
            accessor = api_client.metrics.get(metric_name)
            if accessor:
                print(f"   {metric_name}: {type(accessor).__name__}")
            else:
                print(f"   {metric_name}: Not available")

        # Show direct class imports
        print("\n📦 Direct class imports work too:")
        from garmy import ActivitySummary, TrainingReadiness

        print(f"   TrainingReadiness: {TrainingReadiness}")
        print(f"   ActivitySummary: {ActivitySummary}")

    except Exception as e:
        print(f"❌ Modern API showcase failed: {e}")


def run_all_demos():
    """Run all demo functions."""
    print("🚀 Running all training readiness demos (Modern API)...")

    # Show modern API first
    try:
        modern_api_showcase()
    except Exception as e:
        print(f"❌ Modern API showcase failed: {e}")

    # Run main demo
    main()

    # Run other demos
    try:
        weekly_readiness_data()
    except Exception as e:
        print(f"❌ Weekly readiness demo failed: {e}")

    try:
        raw_api_data()
    except Exception as e:
        print(f"❌ Raw API demo failed: {e}")

    try:
        comprehensive_readiness_analysis()
    except Exception as e:
        print(f"❌ Comprehensive analysis demo failed: {e}")


if __name__ == "__main__":
    run_all_demos()

    print("\n💡 Modern API Notes:")
    print("   • Explicit client creation: AuthClient() and APIClient()")
    print("   • No global state or singleton patterns")
    print("   • Use api_client.metrics for direct metric access")
    print("   • All metrics auto-discovered, no manual configuration")
    print("   • Type-safe configurations with validation")
    print("   • Clean separation between data classes and accessors")
    print("   • Direct class imports: from garmy import TrainingReadiness")
