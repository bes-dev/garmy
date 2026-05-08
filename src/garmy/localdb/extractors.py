"""Data extraction utilities for converting API responses to database format."""

from datetime import date
from typing import Any, Dict, List, Optional, Tuple, Union

from .models import MetricType


class DataExtractor:
    """Extracts and normalizes data from API responses for database storage."""

    def extract_metric_data(
        self, data: Any, metric_type: MetricType
    ) -> Optional[Union[Dict[str, Any], List[Dict[str, Any]]]]:
        """Extract data based on metric type."""
        if metric_type == MetricType.DAILY_SUMMARY:
            return self._extract_daily_summary_data(data)
        elif metric_type == MetricType.SLEEP:
            return self._extract_sleep_data(data)
        elif metric_type == MetricType.TRAINING_READINESS:
            return self._extract_training_readiness_data(data)
        elif metric_type == MetricType.HRV:
            return self._extract_hrv_data(data)
        elif metric_type == MetricType.RESPIRATION:
            return self._extract_respiration_summary(data)
        elif metric_type == MetricType.ACTIVITIES:
            return self._extract_activity_data(data)
        elif metric_type == MetricType.STEPS:
            return self._extract_steps_data(data)
        elif metric_type == MetricType.CALORIES:
            return self._extract_calories_data(data)
        elif metric_type == MetricType.HEART_RATE:
            return self._extract_heart_rate_summary(data)
        elif metric_type == MetricType.STRESS:
            return self._extract_stress_summary(data)
        elif metric_type == MetricType.BODY_BATTERY:
            return self._extract_body_battery_summary(data)
        elif metric_type == MetricType.SPO2:
            return self._extract_spo2_data(data)
        elif metric_type == MetricType.RESTING_HEART_RATE:
            return self._extract_resting_heart_rate_data(data)
        elif metric_type == MetricType.INTENSITY_MINUTES:
            return self._extract_intensity_minutes_data(data)
        elif metric_type == MetricType.FLOORS:
            return self._extract_floors_data(data)
        elif metric_type == MetricType.BODY_COMPOSITION:
            return self._extract_body_composition_data(data)
        elif metric_type == MetricType.TRAINING_STATUS:
            return self._extract_training_status_data(data)
        elif metric_type == MetricType.ENDURANCE_SCORE:
            return self._extract_endurance_score_data(data)
        else:
            return None

    def _extract_daily_summary_data(self, data: Any) -> Dict[str, Any]:
        """Extract daily summary data."""
        return {
            # Steps and movement
            "total_steps": getattr(data, "total_steps", None),
            "step_goal": getattr(
                data, "daily_step_goal", None
            ),  # Correct attribute name!
            "total_distance_meters": getattr(data, "total_distance_meters", None),
            # Calories
            "total_calories": getattr(data, "total_kilocalories", None),
            "active_calories": getattr(data, "active_kilocalories", None),
            "bmr_calories": getattr(data, "bmr_kilocalories", None),
            # Heart rate
            "resting_heart_rate": getattr(data, "resting_heart_rate", None),
            "max_heart_rate": getattr(data, "max_heart_rate", None),
            "min_heart_rate": getattr(data, "min_heart_rate", None),
            "average_heart_rate": getattr(data, "average_heart_rate", None),
            # Stress and recovery
            "avg_stress_level": getattr(data, "avg_stress_level", None)
            or getattr(data, "stress_avg", None),
            "max_stress_level": getattr(data, "max_stress_level", None)
            or getattr(data, "stress_max", None),
            "body_battery_high": getattr(data, "body_battery_highest_value", None),
            "body_battery_low": getattr(data, "body_battery_lowest_value", None),
            # Additional metrics that might be in daily summary
            "average_spo2": getattr(data, "average_sp_o2_value", None),
            "average_respiration": getattr(data, "average_respiration_value", None),
        }

    def _extract_sleep_data(self, data: Any) -> Dict[str, Any]:
        """Extract sleep data from Sleep object."""
        from datetime import datetime

        result = {
            # Use the built-in properties from Sleep class
            "sleep_duration_hours": getattr(data, "sleep_duration_hours", None),
            "deep_sleep_percentage": getattr(data, "deep_sleep_percentage", None),
            "light_sleep_percentage": getattr(data, "light_sleep_percentage", None),
            "rem_sleep_percentage": getattr(data, "rem_sleep_percentage", None),
            "awake_percentage": getattr(data, "awake_percentage", None),
            "deep_sleep_hours": None,
            "light_sleep_hours": None,
            "rem_sleep_hours": None,
            "awake_hours": None,
            "average_spo2": None,
            "average_respiration": None,
            # NEW: Sleep score
            "sleep_score": None,
            "sleep_score_qualifier": None,
            # NEW: Sleep timing
            "sleep_bedtime": None,
            "sleep_wake_time": None,
            "sleep_need_minutes": None,
            # NEW: Skin temperature
            "skin_temp_deviation_c": None,
        }

        # Extract from sleep_summary if available
        if hasattr(data, "sleep_summary") and data.sleep_summary:
            summary = data.sleep_summary
            deep = getattr(summary, "deep_sleep_seconds", None)
            light = getattr(summary, "light_sleep_seconds", None)
            rem = getattr(summary, "rem_sleep_seconds", None)
            awake = getattr(summary, "awake_sleep_seconds", None)

            if deep and deep > 0:
                result["deep_sleep_hours"] = deep / 3600
            if light and light > 0:
                result["light_sleep_hours"] = light / 3600
            if rem and rem > 0:
                result["rem_sleep_hours"] = rem / 3600
            if awake and awake > 0:
                result["awake_hours"] = awake / 3600

            result["average_spo2"] = getattr(summary, "average_sp_o2_value", None)
            result["average_respiration"] = getattr(
                summary, "average_respiration_value", None
            )

            # NEW: Extract sleep scores from nested dict
            sleep_scores = getattr(summary, "sleep_scores", None)
            if sleep_scores and isinstance(sleep_scores, dict):
                overall = sleep_scores.get("overall", {})
                if isinstance(overall, dict):
                    result["sleep_score"] = overall.get("value")
                    result["sleep_score_qualifier"] = overall.get("qualifier_key")

            # NEW: Extract sleep need
            sleep_need = getattr(summary, "sleep_need", None)
            if sleep_need and isinstance(sleep_need, dict):
                result["sleep_need_minutes"] = sleep_need.get("actual")

            # NEW: Convert timestamps to ISO strings
            sleep_start = getattr(summary, "sleep_start_timestamp_local", None)
            sleep_end = getattr(summary, "sleep_end_timestamp_local", None)

            if sleep_start:
                try:
                    result["sleep_bedtime"] = datetime.fromtimestamp(
                        sleep_start / 1000
                    ).isoformat()
                except (ValueError, OSError):
                    pass

            if sleep_end:
                try:
                    result["sleep_wake_time"] = datetime.fromtimestamp(
                        sleep_end / 1000
                    ).isoformat()
                except (ValueError, OSError):
                    pass

        # NEW: Extract skin temp from top-level Sleep object (not summary)
        skin_temp = getattr(data, "skin_temp_deviation_c", None)
        if skin_temp is not None:
            result["skin_temp_deviation_c"] = skin_temp

        return result

    def _extract_heart_rate_summary(self, data: Any) -> Dict[str, Any]:
        """Extract heart rate summary data."""
        # Heart rate data is in heart_rate_summary nested object
        summary = getattr(data, "heart_rate_summary", data)

        return {
            "resting_heart_rate": getattr(summary, "resting_heart_rate", None),
            "max_heart_rate": getattr(summary, "max_heart_rate", None),
            "min_heart_rate": getattr(summary, "min_heart_rate", None),
            "average_heart_rate": getattr(
                data, "average_heart_rate", None
            ),  # This is on main object
        }

    def _extract_stress_summary(self, data: Any) -> Dict[str, Any]:
        """Extract stress summary data."""
        return {
            "avg_stress_level": getattr(data, "avg_stress_level", None)
            or getattr(data, "stress_avg", None),
            "max_stress_level": getattr(data, "max_stress_level", None)
            or getattr(data, "stress_max", None),
        }

    def _extract_body_battery_summary(self, data: Any) -> Dict[str, Any]:
        """Extract body battery summary data."""
        return {
            "body_battery_high": getattr(data, "body_battery_highest_value", None)
            or getattr(data, "highest_value", None),
            "body_battery_low": getattr(data, "body_battery_lowest_value", None)
            or getattr(data, "lowest_value", None),
        }

    def _extract_training_readiness_data(self, data: Any) -> Dict[str, Any]:
        """Extract training readiness nested data."""
        return {
            "score": getattr(data, "score", None),
            "level": getattr(data, "level", None),
            "feedback": getattr(data, "feedback_short", None),
        }

    def _extract_hrv_data(self, data: Any) -> Dict[str, Any]:
        """Extract HRV using nested summary."""
        hrv_summary = getattr(data, "hrv_summary", None)
        if hrv_summary:
            result = {
                "hrv_weekly_avg": getattr(hrv_summary, "weekly_avg", None),
                "hrv_last_night_avg": getattr(hrv_summary, "last_night_avg", None),
                "hrv_status": getattr(hrv_summary, "status", None),
                "hrv_last_night_5min_high": getattr(
                    hrv_summary, "last_night_5_min_high", None
                ),
            }
            baseline = getattr(hrv_summary, "baseline", None)
            if baseline:
                result["hrv_baseline_low_upper"] = getattr(
                    baseline, "low_upper", None
                )
                result["hrv_baseline_balanced_low"] = getattr(
                    baseline, "balanced_low", None
                )
                result["hrv_baseline_balanced_upper"] = getattr(
                    baseline, "balanced_upper", None
                )
            return result
        return {}

    def _extract_respiration_summary(self, data: Any) -> Dict[str, Any]:
        """Extract respiration summary - unique respiratory metrics."""
        # Try different possible locations for respiration data
        summary = getattr(data, "respiration_summary", None)
        if summary:
            return {
                "average_respiration": getattr(
                    summary, "average_respiration_value", None
                ),
                "avg_waking_respiration_value": getattr(
                    summary, "avg_waking_respiration_value", None
                ),
                "avg_sleep_respiration_value": getattr(
                    summary, "avg_sleep_respiration_value", None
                ),
                "lowest_respiration_value": getattr(
                    summary, "lowest_respiration_value", None
                ),
                "highest_respiration_value": getattr(
                    summary, "highest_respiration_value", None
                ),
            }

        # Also try direct attributes
        result = {
            "average_respiration": getattr(data, "average_respiration_value", None),
            "avg_waking_respiration_value": getattr(
                data, "avg_waking_respiration_value", None
            ),
            "avg_sleep_respiration_value": getattr(
                data, "avg_sleep_respiration_value", None
            ),
            "lowest_respiration_value": getattr(data, "lowest_respiration_value", None),
            "highest_respiration_value": getattr(
                data, "highest_respiration_value", None
            ),
        }

        # Return only if we have any data
        if any(v is not None for v in result.values()):
            return result

        return {}

    def _extract_spo2_data(self, data: Any) -> Dict[str, Any]:
        """Extract SpO2 daily summary data."""
        return {
            "average_spo2": getattr(data, "average_spo2", None),
            "lowest_spo2": getattr(data, "lowest_spo2", None),
        }

    def _extract_resting_heart_rate_data(self, data: Any) -> Dict[str, Any]:
        """Extract dedicated resting heart rate data."""
        return {
            "dedicated_resting_heart_rate": getattr(data, "value", None),
        }

    def _extract_intensity_minutes_data(self, data: Any) -> Dict[str, Any]:
        """Extract intensity minutes daily summary.

        - moderate/vigorous: weekly cumulative values from the API
        - intensity_minutes_total: daily earned total, computed by summing
          the imValuesArray timeseries (not the weekly cumulative)
        - intensity_minutes_goal: weekly goal (typically 150)
        """
        return {
            "moderate_intensity_minutes": getattr(data, "moderate_minutes", None),
            "vigorous_intensity_minutes": getattr(data, "vigorous_minutes", None),
            # Daily total computed from timeseries, not the weekly cumulative
            "intensity_minutes_total": getattr(data, "daily_total", None),
            "intensity_minutes_goal": getattr(data, "week_goal", None),
        }

    def _extract_floors_data(self, data: Any) -> Dict[str, Any]:
        """Extract floors data."""
        return {
            "floors_ascended": getattr(data, "floors_ascended", None),
            "floors_descended": getattr(data, "floors_descended", None),
        }

    def _extract_training_status_data(self, data: Any) -> Dict[str, Any]:
        """Extract training status and load data for performance_metrics table."""
        return {
            "acute_load": getattr(data, "acute_load", None),
            "chronic_load": getattr(data, "chronic_load", None),
            "load_balance": getattr(data, "load_balance", None),
            "load_type": getattr(data, "load_type", None),
            "training_status": getattr(data, "training_status", None),
            "training_status_feedback": getattr(
                data, "training_status_feedback", None
            ),
        }

    def _extract_endurance_score_data(self, data: Any) -> Dict[str, Any]:
        """Extract endurance score data for performance_metrics table."""
        return {
            "endurance_score": getattr(data, "endurance_score", None),
            "endurance_score_classification": getattr(
                data, "endurance_score_classification", None
            ),
        }

    def _extract_activity_data(self, data: Any) -> Dict[str, Any]:
        """Extract activity data from both parsed and raw formats.

        Extracts comprehensive activity data from the activity list API response,
        which includes all the fields we need without requiring separate API calls.
        """

        # Handle both object attributes and dict keys
        def get_value(obj, *keys):
            for key in keys:
                if hasattr(obj, key):
                    return getattr(obj, key, None)
                elif isinstance(obj, dict) and key in obj:
                    return obj[key]
            return None

        def get_nested_value(obj, outer_key, inner_key):
            """Get value from nested dict/object."""
            outer = get_value(obj, outer_key)
            if outer:
                if isinstance(outer, dict):
                    return outer.get(inner_key)
                elif hasattr(outer, inner_key):
                    return getattr(outer, inner_key, None)
            return None

        activity_id = get_value(data, "activity_id", "activityId")
        if activity_id:
            # Extract activity type from nested activityType dict
            # Parsed ActivitySummary uses 'type_key', raw dict uses 'typeKey'
            activity_type = get_nested_value(data, "activity_type", "type_key")
            if not activity_type:
                activity_type = get_nested_value(data, "activity_type", "typeKey")
            if not activity_type:
                activity_type = get_nested_value(data, "activityType", "typeKey")

            return {
                "activity_id": activity_id,
                "activity_name": get_value(data, "activity_name", "activityName"),
                "duration_seconds": get_value(
                    data, "duration", "movingDuration", "elapsedDuration"
                ),
                # Heart rate - parsed uses average_hr/max_hr, raw uses averageHR/maxHR
                "avg_heart_rate": get_value(data, "average_hr", "averageHR", "avgHR"),
                "max_heart_rate": get_value(data, "max_hr", "maxHR"),
                "training_load": get_value(
                    data,
                    "activity_training_load",
                    "activityTrainingLoad",
                    "trainingLoad",
                ),
                "start_time": get_value(
                    data, "start_time_local", "startTimeLocal", "start_time"
                ),
                # Activity type extracted above
                "activity_type": activity_type,
                # These may not be in parsed ActivitySummary, but try anyway
                "distance_meters": get_value(data, "distance", "distance_meters"),
                "calories": get_value(data, "calories"),
                "elevation_gain": get_value(data, "elevation_gain", "elevationGain"),
                "elevation_loss": get_value(data, "elevation_loss", "elevationLoss"),
                "avg_speed": get_value(data, "average_speed", "averageSpeed"),
                "max_speed": get_value(data, "max_speed", "maxSpeed"),
            }
        return {}

    def extract_timeseries_data(
        self, data: Any, metric_type: MetricType
    ) -> List[Tuple]:
        """Extract timeseries data points from Garmy metrics."""
        timeseries_data = []

        if metric_type == MetricType.BODY_BATTERY:
            if hasattr(data, "body_battery_readings") and data.body_battery_readings:
                for reading in data.body_battery_readings:
                    if reading.level is None:
                        continue
                    metadata = {
                        "status": getattr(reading, "status", None),
                        "version": getattr(reading, "version", None),
                    }
                    timeseries_data.append((reading.timestamp, reading.level, metadata))

        elif metric_type == MetricType.STRESS:
            if hasattr(data, "stress_readings") and data.stress_readings:
                for reading in data.stress_readings:
                    if reading.stress_level is None:
                        continue
                    metadata = {}
                    if hasattr(reading, "stress_category"):
                        metadata["stress_category"] = reading.stress_category
                    timeseries_data.append(
                        (reading.timestamp, reading.stress_level, metadata)
                    )

        elif metric_type == MetricType.HEART_RATE:
            if (
                hasattr(data, "heart_rate_values_array")
                and data.heart_rate_values_array
            ):
                for reading in data.heart_rate_values_array:
                    if isinstance(reading, (list, tuple)) and len(reading) >= 2:
                        timestamp, heart_rate = reading[0], reading[1]
                        if heart_rate is not None:
                            timeseries_data.append((timestamp, heart_rate, {}))

        elif metric_type == MetricType.RESPIRATION:
            # Respiration might have different format - check if it has readings
            if hasattr(data, "respiration_readings") and data.respiration_readings:
                for reading in data.respiration_readings:
                    timeseries_data.append((reading.timestamp, reading.value, {}))

        elif metric_type == MetricType.HRV:
            if hasattr(data, "hrv_readings") and data.hrv_readings:
                from datetime import datetime

                for reading in data.hrv_readings:
                    if reading.hrv_value is None:
                        continue
                    # Convert ISO timestamp string to unix ms
                    if reading.reading_time_gmt:
                        try:
                            dt = datetime.fromisoformat(
                                reading.reading_time_gmt.replace("Z", "+00:00")
                            )
                            timestamp_ms = int(dt.timestamp() * 1000)
                            timeseries_data.append(
                                (timestamp_ms, reading.hrv_value, {})
                            )
                        except (ValueError, OSError):
                            continue

        elif metric_type == MetricType.SPO2:
            if (
                hasattr(data, "spo2_hourly_averages")
                and data.spo2_hourly_averages
            ):
                for reading in data.spo2_hourly_averages:
                    if isinstance(reading, (list, tuple)) and len(reading) >= 2:
                        timestamp, spo2_value = reading[0], reading[1]
                        if spo2_value is not None:
                            timeseries_data.append((timestamp, spo2_value, {}))

        elif metric_type == MetricType.INTENSITY_MINUTES:
            # 15-minute interval readings from imValuesArray.
            # Each entry is [timestamp_ms, intensity_minutes_earned].
            if hasattr(data, "im_values_array") and data.im_values_array:
                for reading in data.im_values_array:
                    if isinstance(reading, (list, tuple)) and len(reading) >= 2:
                        timestamp, im_value = reading[0], reading[1]
                        if im_value is not None:
                            timeseries_data.append((timestamp, int(im_value), {}))

        return timeseries_data

    def _extract_steps_data(self, data: Any) -> Dict[str, Any]:
        """Extract steps data."""
        return {
            "total_steps": getattr(data, "total_steps", None),
            "step_goal": getattr(data, "step_goal", None),
        }

    def _extract_calories_data(self, data: Any) -> Dict[str, Any]:
        """Extract calories data."""
        return {
            "total_calories": getattr(data, "total_kilocalories", None),
            "active_calories": getattr(data, "active_kilocalories", None),
            "bmr_calories": getattr(data, "bmr_kilocalories", None),
        }

    def extract_activity_details(self, data: Dict) -> Dict[str, Any]:
        """Extract detailed activity data from activity details API response.

        Args:
            data: Raw API response from /activity-service/activity/{id}

        Returns:
            Dict with normalized activity detail fields.
        """
        if not data:
            return {}

        activity_type_info = data.get("activityType", {})

        return {
            "activity_type": (
                activity_type_info.get("typeKey") if activity_type_info else None
            ),
            "distance_meters": data.get("distance"),
            "calories": data.get("calories"),
            "elevation_gain": data.get("elevationGain"),
            "elevation_loss": data.get("elevationLoss"),
            "avg_speed": data.get("avgSpeed"),
            "max_speed": data.get("maxSpeed"),
            "max_heart_rate": data.get("maxHR"),
        }

    def extract_exercise_sets(
        self, data: Dict, activity_id: str
    ) -> List[Dict[str, Any]]:
        """Extract exercise sets from exerciseSets API response.

        Args:
            data: Raw API response from /activity-service/activity/{id}/exerciseSets
            activity_id: The activity ID these sets belong to

        Returns:
            List of dicts with normalized exercise set fields.
        """
        if not data:
            return []

        sets = []
        exercise_sets = data.get("exerciseSets", [])

        for i, set_data in enumerate(exercise_sets):
            exercises = set_data.get("exercises", [])

            # Get most probable exercise category from the exercises list
            category = None
            exercise_name = None
            if exercises:
                # Sort by probability and get the best match
                best_match = max(exercises, key=lambda x: x.get("probability", 0))
                category = best_match.get("category")
                exercise_name = best_match.get("name")

            sets.append(
                {
                    "set_order": i,
                    "exercise_category": category,
                    "exercise_name": exercise_name,
                    "set_type": set_data.get("setType"),
                    "repetition_count": set_data.get("repetitionCount"),
                    "weight_grams": set_data.get(
                        "weight"
                    ),  # API returns weight in milligrams
                    "duration_seconds": set_data.get("duration"),
                    "start_time": set_data.get("startTime"),
                }
            )

        return sets

    def calculate_strength_summary(self, sets: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate strength training summary from exercise sets.

        Args:
            sets: List of exercise set dicts from extract_exercise_sets

        Returns:
            Dict with total_sets, total_reps, total_weight_kg
        """
        active_sets = [s for s in sets if s.get("set_type") == "ACTIVE"]

        total_reps = sum(s.get("repetition_count", 0) or 0 for s in active_sets)

        # Calculate total volume (sum of weight * reps for each set)
        total_volume_grams = 0
        for s in active_sets:
            weight = s.get("weight_grams", 0) or 0
            reps = s.get("repetition_count", 0) or 0
            total_volume_grams += weight * reps

        return {
            "total_sets": len(active_sets),
            "total_reps": total_reps,
            "total_weight_kg": total_volume_grams / 1000 if total_volume_grams else 0,
        }

    def extract_activity_splits(
        self, data: Dict, activity_id: str
    ) -> List[Dict[str, Any]]:
        """Extract lap/split data from splits API response.

        Args:
            data: Raw API response from /activity-service/activity/{id}/splits
            activity_id: The activity ID these splits belong to

        Returns:
            List of dicts with normalized split/lap fields.
        """
        if not data:
            return []

        splits = []
        lap_dtos = data.get("lapDTOs", [])

        for lap in lap_dtos:
            splits.append(
                {
                    "lap_index": lap.get("lapIndex", 0),
                    "start_time": lap.get("startTimeGMT"),
                    "duration_seconds": lap.get("duration"),
                    "moving_duration_seconds": lap.get("movingDuration"),
                    "distance_meters": lap.get("distance"),
                    "avg_speed": lap.get("averageSpeed"),
                    "max_speed": lap.get("maxSpeed"),
                    "avg_moving_speed": lap.get("averageMovingSpeed"),
                    "avg_heart_rate": (
                        int(lap.get("averageHR")) if lap.get("averageHR") else None
                    ),
                    "max_heart_rate": (
                        int(lap.get("maxHR")) if lap.get("maxHR") else None
                    ),
                    "elevation_gain": lap.get("elevationGain"),
                    "elevation_loss": lap.get("elevationLoss"),
                    "max_elevation": lap.get("maxElevation"),
                    "min_elevation": lap.get("minElevation"),
                    "avg_cadence": lap.get("averageRunCadence"),
                    "max_cadence": lap.get("maxRunCadence"),
                    "calories": lap.get("calories"),
                    "start_latitude": lap.get("startLatitude"),
                    "start_longitude": lap.get("startLongitude"),
                    "end_latitude": lap.get("endLatitude"),
                    "end_longitude": lap.get("endLongitude"),
                    "intensity_type": lap.get("intensityType"),
                }
            )

        return splits

    def calculate_splits_summary(self, splits: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate activity summary from splits data.

        Args:
            splits: List of split dicts from extract_activity_splits

        Returns:
            Dict with total_laps and aggregated metrics
        """
        # Include ACTIVE, INTERVAL, and other non-REST splits
        # (treadmill runs use INTERVAL, outdoor runs use ACTIVE)
        active_splits = [
            s for s in splits if s.get("intensity_type") not in (None, "REST")
        ]

        if not active_splits:
            return {"total_laps": len(splits)}

        total_distance = sum(s.get("distance_meters", 0) or 0 for s in active_splits)
        total_duration = sum(s.get("duration_seconds", 0) or 0 for s in active_splits)
        total_elevation_gain = sum(
            s.get("elevation_gain", 0) or 0 for s in active_splits
        )
        total_calories = sum(s.get("calories", 0) or 0 for s in active_splits)

        # Calculate average pace (min/km) if we have distance
        avg_pace_min_km = None
        if total_distance > 0 and total_duration > 0:
            # pace = time / distance, convert to min/km
            avg_pace_min_km = (total_duration / 60) / (total_distance / 1000)

        return {
            "total_laps": len(active_splits),
            "total_distance_meters": total_distance,
            "total_duration_seconds": total_duration,
            "total_elevation_gain": total_elevation_gain,
            "total_calories": total_calories,
            "avg_pace_min_km": avg_pace_min_km,
        }

    def extract_health_snapshots(
        self, snapshots: List[Any]
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Extract DB-ready rows for the three Health Snapshot tables.

        Args:
            snapshots: List of HealthSnapshot dataclass instances (from
                APIClient.health_snapshots.range / latest / for_date).

        Returns:
            Dict with three keys:
              - "records":   one dict per snapshot, for the health_snapshots table
              - "summaries": 6 dicts per snapshot, for health_snapshot_summaries
              - "zones":     6 dicts per snapshot, for health_snapshot_zones

            All dicts are keyed by activity_uuid (caller adds user_id).
        """
        records: List[Dict[str, Any]] = []
        summaries: List[Dict[str, Any]] = []
        zones: List[Dict[str, Any]] = []

        for snap in snapshots:
            uuid = getattr(snap, "activity_uuid", None)
            if not uuid:
                continue

            cal_date = getattr(snap, "calendar_date_obj", None)
            if cal_date is None:
                date_str = getattr(snap, "calendar_date", "")
                try:
                    cal_date = date.fromisoformat(date_str) if date_str else None
                except (ValueError, TypeError):
                    cal_date = None

            records.append(
                {
                    "activity_uuid": uuid,
                    "calendar_date": cal_date,
                    "start_timestamp_gmt": getattr(snap, "start_timestamp_gmt", None),
                    "start_timestamp_local": getattr(snap, "start_timestamp_local", None),
                    "end_timestamp_gmt": getattr(snap, "end_timestamp_gmt", None),
                    "end_timestamp_local": getattr(snap, "end_timestamp_local", None),
                    "wellness_activity_type": getattr(
                        snap, "wellness_activity_type", None
                    ),
                    "notes": getattr(snap, "notes", None),
                    "rule_pk": getattr(snap, "rule_pk", None),
                    "user_profile_pk": getattr(snap, "user_profile_pk", None),
                    "device_meta_data": getattr(snap, "device_meta_data", None),
                }
            )

            for summary in getattr(snap, "summaries", []) or []:
                summaries.append(
                    {
                        "activity_uuid": uuid,
                        "summary_type": getattr(summary, "summary_type", ""),
                        "min_value": getattr(summary, "min_value", None),
                        "max_value": getattr(summary, "max_value", None),
                        "avg_value": getattr(summary, "avg_value", 0.0),
                    }
                )

            for zone in getattr(snap, "time_in_zone", []) or []:
                zones.append(
                    {
                        "activity_uuid": uuid,
                        "zone_number": getattr(zone, "zone_number", 0),
                        "millis_in_zone": getattr(zone, "millis_in_zone", 0),
                        "zone_low_boundary": getattr(zone, "zone_low_boundary", 0),
                    }
                )

        return {"records": records, "summaries": summaries, "zones": zones}

    def _extract_body_composition_data(self, data: Dict) -> List[Dict[str, Any]]:
        """Extract body composition entries from weight service response.

        Args:
            data: Raw API response from /weight-service/weight/range/

        Returns:
            List of body composition entry dicts
        """
        entries = []

        for summary in data.get("dailyWeightSummaries", []):
            latest = summary.get("latestWeight")
            if not latest:
                continue

            sample_pk = latest.get("samplePk")
            if not sample_pk:
                continue

            entries.append(
                {
                    "sample_pk": str(sample_pk),
                    "measurement_date": latest.get("calendarDate"),
                    "timestamp_gmt": latest.get("timestampGMT"),
                    "weight_grams": latest.get("weight"),
                    "bmi": latest.get("bmi"),
                    "body_fat_percentage": latest.get("bodyFat"),
                    "body_water_percentage": latest.get("bodyWater"),
                    "bone_mass_grams": latest.get("boneMass"),
                    "muscle_mass_grams": latest.get("muscleMass"),
                    "visceral_fat": latest.get("visceralFat"),
                    "metabolic_age": latest.get("metabolicAge"),
                    "physique_rating": latest.get("physiqueRating"),
                    "source_type": latest.get("sourceType"),
                }
            )

        return entries
