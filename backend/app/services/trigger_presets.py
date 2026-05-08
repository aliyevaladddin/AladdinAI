"""Mapping of UI preset names → cron expressions (UTC).

Keep this list small and obvious. If a user needs anything else, they can
switch the UI to raw cron mode.
"""
PRESETS: dict[str, str] = {
    "every_15_minutes": "*/15 * * * *",
    "every_hour": "0 * * * *",
    "every_morning_9": "0 9 * * *",
    "weekdays_9": "0 9 * * 1-5",
    "every_monday_9": "0 9 * * 1",
    "every_day_18": "0 18 * * *",
}


def resolve(preset: str | None) -> str | None:
    if not preset:
        return None
    return PRESETS.get(preset)
