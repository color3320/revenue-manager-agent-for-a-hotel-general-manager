# Metric window definitions

Authoritative verify-page filters for anchor date **2026-06-11**. Implemented in [`etl/metric_windows.py`](../etl/metric_windows.py) and validated by [`etl/verify.py`](../etl/verify.py) against [`data/verify_targets.json`](../data/verify_targets.json).

**Global anchor:** `as_of_date` from `dataset_metadata` (singleton row, id=1), must match `verify_targets.json` → `anchor_date`.

**Lookback constant:** `CURRENT_LOOKBACK_DAYS = 180`

---

## Row counts

| Metric | Grain | SQL predicate |
|---|---|---|
| `total_reservations` | reservation | none — `COUNT(DISTINCT reservation_id)` |
| `total_stay_rows` | stay row | none — `COUNT(*)` |
| `cancelled_reservations` | reservation | `reservation_status = 'Cancelled'` |
| `current_reservations` | reservation | `arrival_date >= as_of_date - 180 days` |
| `last_year_reservations` | reservation | `arrival_date < as_of_date - 180 days` |

The current / last-year split partitions all 250 reservations (150 + 100). Classification uses **`arrival_date`**, not `stay_date`.

---

## On the books (OTB)

Verify heading: *On the books (current, Reserved, stay_date ≥ today)*

| Metric | Filter |
|---|---|
| `otb_room_nights` | `Reserved` AND `stay_date >= as_of_date` → `SUM(number_of_spaces)` |
| `otb_room_revenue_before_tax` | same → `SUM(daily_room_revenue_before_tax)` |
| `otb_total_revenue_before_tax` | same → `SUM(daily_total_revenue_before_tax)` |
| `otb_room_nights_by_market` | same, grouped by `market_code` |

**Date field:** `stay_date` (not `arrival_date`).

---

## Same time last year (STLY)

Verify heading: *Same time last year (last_year, Reserved)*

| Metric | Filter |
|---|---|
| `stly_room_nights` | `Reserved` AND `stay_date < as_of_date - 180 days` → `SUM(number_of_spaces)` |
| `stly_total_revenue_before_tax` | same → `SUM(daily_total_revenue_before_tax)` |

**Date field:** `stay_date`. The `< as_of_date - 180 days` boundary mirrors the last-year reservation block (arrivals before the current 180-day lookback).

---

## ADR by room type

Verify heading: *ADR by room type (current, Reserved)*

Per `space_type`, **reservation-level** average of `adr_room` (not stay-weighted revenue):

```sql
SELECT space_type, ROUND(AVG(adr_room), 2)
FROM (
  SELECT DISTINCT ON (reservation_id)
    reservation_id, space_type, adr_room
  FROM reservations_hackathon
  WHERE reservation_status = 'Reserved'
    AND arrival_date >= as_of_date - INTERVAL '180 days'
  ORDER BY reservation_id
) t
GROUP BY space_type
```

**Date field for cohort:** `arrival_date` (current 180-day window). **Formula:** `AVG(adr_room)` at reservation grain.

---

## Defaults

- Exclude `Cancelled` for OTB, STLY, and ADR unless the metric is explicitly about cancellations.
- Do not use `COUNT(*)` when the business question is room nights — use `SUM(number_of_spaces)`.
- Do not use `COUNT(*)` when the business question is reservations — use `COUNT(DISTINCT reservation_id)`.

---

## Part 5 reuse

Reuse these exact predicates in semantic-layer views / agent skills. Do not re-derive windows in application code.
