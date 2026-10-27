"""SYNTHETIC tests for the parking meter rules."""

from datetime import datetime

from src.meter import (
    DAILY_CAP_CENTS,
    barrier_opens,
    capped,
    discounted,
    entry_stamp,
    fare,
    full_sign,
    hourly_rate,
    lost_ticket_fare,
    receipt,
    rounded,
)


# [utest->req~card-refusal~1]
def test_declined_card_keeps_barrier_closed() -> None:
    """A declined card leaves the barrier closed."""
    assert not barrier_opens(False)


# [utest->req~daily-cap~1]
def test_capped_fare_is_the_cap() -> None:
    """A huge fare is cut to the cap."""
    assert capped(100000) == DAILY_CAP_CENTS


# [utest->req~entry-time~1]
def test_entry_stamp_drops_seconds() -> None:
    """The stamp keeps the minute and drops the seconds."""
    assert entry_stamp(datetime(2026, 1, 1, 9, 30, 45, 5)) == datetime(2026, 1, 1, 9, 30)


# [utest->req~ev-discount~1]
def test_electric_car_pays_less() -> None:
    """An electric car pays less than a petrol car."""
    assert discounted(1000, True) < discounted(1000, False)


# [utest->req~fare-rounding~1]
def test_fare_rounds_up() -> None:
    """A fare of 101 cents rounds up to 110."""
    assert rounded(101) == 110


# [utest->req~full-sign~1]
def test_full_sign_when_all_taken() -> None:
    """The sign shows when taken equals spaces."""
    assert full_sign(50, 50)
    assert not full_sign(49, 50)


# [utest->req~grace-period~1]
def test_grace_period_is_free() -> None:
    """A car leaving after five minutes pays nothing."""
    assert fare(5, 300) == 0


# [utest->req~lost-ticket~1]
def test_lost_ticket_charges_something() -> None:
    """A lost ticket costs money."""
    assert lost_ticket_fare() > 0


# [utest->req~night-rate~1]
def test_night_rate_is_half() -> None:
    """Eleven at night costs half the day rate."""
    assert hourly_rate(23, 400) == 200
    assert hourly_rate(12, 400) == 400


# [utest->req~receipt-total~1]
def test_receipt_shows_total() -> None:
    """The receipt prints the total in dollars."""
    assert receipt(1230) == "Total: $12.30"
