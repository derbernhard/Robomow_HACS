"""Stop-reason code tables for the Robomow bridge.

The bridge hands out the numeric stop reason and only ever provides the
German sentence next to it. These tables let the integration show a
translated label in whichever language Home Assistant runs in.

The English wording follows the Robomow documentation; the bridge treats
the RS615 and MC500 series identically.
"""

from __future__ import annotations

# Stop reasons reported by /renew key "6" and by the event list in /oncemisc.
STOP_REASONS: dict[int, str] = {
    1: "stop_button_pressed",
    3: "started_outside_plot",
    4: "key_pressed_warmup",
    5: "bumper_pressed_warmup",
    6: "front_wheel_problem_warmup",
    10: "no_charging_voltage",
    11: "setup_stopped_base_test",
    12: "setup_stopped_obstacle",
    13: "drive_overheat",
    14: "base_problem",
    16: "drive_overheat_terminated",
    20: "handle_lifted",
    21: "handle_lifted_warmup",
    22: "drive_overcurrent_scan",
    23: "drive_overcurrent_manual",
    24: "stuck_in_place",
    25: "tilt_before_lifting",
    26: "system_switch_off",
    27: "mow_overheat",
    28: "mow_overcurrent",
    29: "mow_overcurrent_remote",
    30: "no_wire_signal",
    31: "mow_overheat_manual",
    32: "cross_outside",
    33: "front_wheel_problem",
    34: "inactive_time",
    35: "mowing_time_reached",
    36: "rain_detected",
    37: "edge_terminate_test",
    38: "remote_safety_button",
    39: "stop_button_manual",
    41: "auto_stopped_searching_base",
    47: "no_wire_signal_driving",
    50: "battery_discharge_time_exceeded",
    52: "going_to_base",
    53: "time_to_charge",
    71: "stopped_from_app",
    72: "drive_overcurrent_scan_5",
}


def stop_reason_code(raw: object) -> int | None:
    """Extract the leading numeric code from a bridge stop-reason string."""
    if raw is None:
        return None
    text = str(raw).replace("\xa0", " ").strip()
    if not text:
        return None
    try:
        return int(text.split(" ", 1)[0])
    except (TypeError, ValueError):
        return None


def stop_reason_key(raw: object) -> str | None:
    """Map a raw stop reason to its translation key, if the code is known."""
    code = stop_reason_code(raw)
    if code is None:
        return None
    return STOP_REASONS.get(code)
