"""Demo customers and past tickets inserted into an empty database."""

# (email, name, plan, customer_since)
CUSTOMERS: list[tuple[str, str, str, str]] = [
    ("dana.kim@example.com", "Dana Kim", "pro", "2024-03-14"),
    ("marcus.oliveira@example.com", "Marcus Oliveira", "business", "2022-11-02"),
    ("priya.shah@example.com", "Priya Shah", "free", "2026-08-20"),
    ("lena.fischer@example.org", "Lena Fischer", "enterprise", "2021-06-01"),
    ("tom.becker@example.net", "Tom Becker", "pro", "2025-01-10"),
]

# (customer_email, category, priority, status, summary, created_at)
TICKETS: list[tuple[str, str, str, str, str, str]] = [
    ("dana.kim@example.com", "billing", "normal", "closed", "Update billing address on invoices", "2025-02-03T09:12:00Z"),
    ("dana.kim@example.com", "technical", "low", "closed", "Board sync slow on mobile app", "2026-05-21T14:40:00Z"),
    ("marcus.oliveira@example.com", "outage", "urgent", "closed", "Boards unavailable during EU incident", "2026-03-11T07:30:00Z"),
    ("marcus.oliveira@example.com", "account", "normal", "closed", "SAML SSO setup question", "2025-07-15T16:20:00Z"),
    ("marcus.oliveira@example.com", "technical", "normal", "open", "Dashboard takes 20 seconds to load", "2026-09-28T08:05:00Z"),
    ("lena.fischer@example.org", "account", "normal", "open", "Add 40 seats before quarter start", "2026-10-01T10:00:00Z"),
    ("tom.becker@example.net", "billing", "normal", "open", "Charged twice in September", "2026-09-30T12:45:00Z"),
]
