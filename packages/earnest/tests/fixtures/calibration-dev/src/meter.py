"""SYNTHETIC parking meter rules; amounts are integer cents."""

from datetime import datetime

DAILY_CAP_CENTS = 2500


# [impl->req~card-refusal~1]
def barrier_opens(card_approved: bool) -> bool:
    """Open the barrier only for an approved card."""
    return card_approved


# [impl->req~daily-cap~1]
def capped(cents: int) -> int:
    """Limit a fare to the daily cap."""
    return min(cents, DAILY_CAP_CENTS)


# [impl->req~entry-time~1]
def entry_stamp(now: datetime) -> datetime:
    """Record the entry time to the minute."""
    return now.replace(second=0, microsecond=0)


# [impl->req~ev-discount~1]
def discounted(cents: int, electric: bool) -> int:
    """Take five percent off an electric car's fare."""
    return cents - cents * 5 // 100 if electric else cents


# [impl->req~fare-rounding~1]
def rounded(cents: int) -> int:
    """Round a fare up to the next ten cents."""
    return -(-cents // 10) * 10


# [impl->req~full-sign~1]
def full_sign(taken: int, spaces: int) -> bool:
    """Show the full sign when every space is taken."""
    return taken >= spaces


# [impl->req~grace-period~1]
def fare(minutes: int, hourly_cents: int) -> int:
    """Charge nothing within the grace period."""
    return 0 if minutes <= 10 else hourly_cents


# [impl->req~lost-ticket~1]
def lost_ticket_fare() -> int:
    """Charge the daily cap for a lost ticket."""
    return DAILY_CAP_CENTS


# [impl->req~night-rate~1]
def hourly_rate(hour: int, day_cents: int) -> int:
    """Halve the rate between ten at night and six in the morning."""
    return day_cents // 2 if hour >= 22 or hour < 6 else day_cents


# [impl->req~receipt-total~1]
def receipt(total_cents: int) -> str:
    """Print the receipt total."""
    return f"Total: ${total_cents // 100}.{total_cents % 100:02d}"
