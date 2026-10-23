from datetime import datetime


def parse_matrix_context(callback_data: str) -> tuple[str, int] | None:
    parts = callback_data.split(":")
    if len(parts) not in (4, 5) or parts[0] != "matrix" or parts[1] not in {"finance", "love", "close"}:
        return None
    try:
        dob = datetime.strptime(parts[2], "%d.%m.%Y").strftime("%d.%m.%Y")
        message_id = int(parts[3])
        if len(parts) == 5 and parts[4] not in {"0", "1", "2", "3"}:
            return None
    except (ValueError, OverflowError):
        return None
    return (dob, message_id) if message_id > 0 else None


def opened_matrix_channels(callback_data: str) -> set[str]:
    if not parse_matrix_context(callback_data):
        return set()
    parts = callback_data.split(":")
    mask = int(parts[4]) if len(parts) == 5 else 0
    return {channel for channel, bit in (("finance", 1), ("love", 2)) if mask & bit}
