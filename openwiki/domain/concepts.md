# Domain Concepts

## Varieties
A **variety** is the top-level inventory category. It has:
- a unique name
- a `tracking_type` of either `weight` or `units`

This is the key branch in the business logic. It determines both how the UI asks for quantities and how the backend decrements stock.

## Products
A **product** is the barcode-scannable item sold at the counter.
- It belongs to one variety.
- It optionally stores `package_size_grams` for weight-based items.
- The barcode is the primary key.

Scanning is barcode-driven: the system looks up the product, then uses the associated variety to decide how stock should be consumed.

## Batches
A **batch** is a delivery lot with its own expiry date.
- Weight-tracked batches use `grams_remaining`.
- Unit-tracked batches use `units_remaining`.
- Batches also store `received_at` for audit/history.

The repository’s main business rule is that batches are not interchangeable. The app always consumes the earliest-expiring batch first.

## Stock movements
A **stock movement** records inventory changes:
- `IN` for restocks
- `OUT` for scans and manual deductions

The low-stock script uses these movements to estimate recent consumption over the last week.

## Tracking modes
### Weight-based
Used for bulk goods like nuts and dried fruit.
- Scan/removal deducts a gram amount.
- A scanned product consumes its configured package size.
- The UI displays totals in grams.

### Unit-based
Used for packaged goods.
- Scan/removal deducts whole units.
- The UI displays totals as units.

## FIFO / expiry semantics
FIFO is implemented as “earliest expiry first,” not simply “oldest inserted first.” That means the app orders batches by `expiry_date` and subtracts from the first batch with remaining stock.

This is the central invariant to preserve when changing the backend or the UI.
