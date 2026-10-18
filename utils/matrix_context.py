from datetime import datetime


def parse_matrix_context(callback_data: str) -> tuple[str, int] | None:
    parts = callback_data.split(":")
    if len(parts) != 4 or parts[0] != "matrix" or parts[1] not in {"finance", "love", "close"}:
        return None
    try:
        dob = datetime.strptime(parts[2], "%d.%m.%Y").strftime("%d.%m.%Y")
        message_id = int(parts[3])
    except (ValueError, OverflowError):
        return None
    return (dob, message_id) if message_id > 0 else None
