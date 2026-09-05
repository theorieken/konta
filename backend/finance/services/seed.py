"""Default categories – modelled after the household reference plan."""

from __future__ import annotations

from finance.models import Category

# slug, name, kind, color, icon, keywords
DEFAULT_CATEGORIES: list[tuple[str, str, str, str, str, list[str]]] = [
    # --- Einnahmen -----------------------------------------------------------
    ("gehalt", "Gehalt", Category.Kind.INCOME, "#2e7d32", "payments",
     ["lohn", "gehalt", "salär", "bezüge", "entgelt", "sonderzahlung"]),
    ("nebeneinkommen", "Nebeneinkommen", Category.Kind.INCOME, "#43a047", "work",
     ["honorar", "freelance", "nebentätigkeit", "auftrag"]),
    ("beteiligung", "Beteiligung", Category.Kind.INCOME, "#00897b", "trending_up",
     ["secondary", "anteil", "beteiligung", "dividende", "ausschüttung"]),
    ("erstattung", "Erstattung", Category.Kind.INCOME, "#26a69a", "undo",
     ["erstattung", "rückerstattung", "gutschrift", "storno", "kostenerstattung"]),
    ("geschenk", "Geschenk", Category.Kind.INCOME, "#66bb6a", "card_giftcard",
     ["geschenk", "schenkung", "zuwendung"]),
    # --- Ausgaben ------------------------------------------------------------
    ("wohnen", "Wohnen", Category.Kind.EXPENSE, "#5e35b1", "home",
     ["miete", "nebenkosten", "hausgeld", "kaution", "vermieter"]),
    ("haushalt", "Haushalt", Category.Kind.EXPENSE, "#3949ab", "shopping_cart",
     ["rewe", "edeka", "aldi", "lidl", "penny", "netto", "dm", "rossmann",
      "lebensmittel", "supermarkt", "drogerie"]),
    ("energie", "Energie & Wasser", Category.Kind.EXPENSE, "#1e88e5", "bolt",
     ["strom", "gas", "wasser", "fernwärme", "stadtwerke", "vattenfall", "eon"]),
    ("versicherung", "Versicherung", Category.Kind.EXPENSE, "#00acc1", "shield",
     ["versicherung", "haftpflicht", "hausrat", "police", "allianz", "huk"]),
    ("abos", "Abos & Mobilfunk", Category.Kind.EXPENSE, "#8e24aa", "subscriptions",
     ["netflix", "spotify", "telekom", "vodafone", "o2", "abo", "mitgliedschaft",
      "icloud", "google one", "internet"]),
    ("mobilitaet", "Mobilität", Category.Kind.EXPENSE, "#f4511e", "directions_car",
     ["tankstelle", "aral", "shell", "hvv", "deutschlandticket", "bahn", "adac",
      "parken", "werkstatt", "kfz"]),
    ("gesundheit", "Gesundheit", Category.Kind.EXPENSE, "#e53935", "medical_services",
     ["apotheke", "arzt", "zahnarzt", "praxis", "krankenkasse", "brille"]),
    ("steuern", "Steuern & Abgaben", Category.Kind.EXPENSE, "#6d4c41", "account_balance",
     ["finanzamt", "steuer", "einkommensteuer", "vorauszahlung", "rundfunkbeitrag"]),
    ("freizeit", "Freizeit", Category.Kind.EXPENSE, "#fb8c00", "local_activity",
     ["restaurant", "bar", "kino", "café", "cafe", "sport", "fitness", "konzert"]),
    ("reisen", "Reisen", Category.Kind.EXPENSE, "#039be5", "flight",
     ["hotel", "airbnb", "flug", "urlaub", "booking", "reise"]),
    ("anschaffung", "Anschaffungen", Category.Kind.EXPENSE, "#7cb342", "chair",
     ["möbel", "ikea", "elektronik", "media markt", "saturn", "anschaffung"]),
    ("bildung", "Bildung", Category.Kind.EXPENSE, "#5c6bc0", "school",
     ["kurs", "seminar", "buch", "studium", "fortbildung", "semesterbeitrag"]),
    ("familie", "Familie", Category.Kind.EXPENSE, "#d81b60", "favorite",
     ["hochzeit", "kita", "kind", "geschenk", "familie"]),
    ("kredit", "Kredit & Zinsen", Category.Kind.EXPENSE, "#455a64", "request_quote",
     ["kredit", "darlehen", "rate", "tilgung", "zins", "finanzierung"]),
    ("gebuehren", "Gebühren", Category.Kind.EXPENSE, "#78909c", "receipt_long",
     ["kontoführung", "gebühr", "entgelt", "bankgebühr"]),
    # --- Neutral -------------------------------------------------------------
    ("sparen", "Sparen & Anlage", Category.Kind.BOTH, "#00695c", "savings",
     ["sparplan", "depot", "etf", "tagesgeld", "festgeld", "rücklage"]),
    ("umbuchung", "Umbuchung", Category.Kind.BOTH, "#90a4ae", "swap_horiz",
     ["umbuchung", "übertrag", "eigenübertrag", "interne buchung"]),
    ("sonstiges", "Sonstiges", Category.Kind.BOTH, "#9e9e9e", "more_horiz", []),
]

# Fallback used whenever nothing else fits – the "every transaction has a
# category" invariant must never block an import.
FALLBACK_CATEGORY_SLUG = "sonstiges"


def ensure_default_categories(user=None, *, household=None) -> int:
    """Idempotent: creates missing default categories, returns how many."""
    if household is None and user is not None:
        household = getattr(user, "current_household", None)
    if household is None:
        from base.models import Household

        household = Household.objects.first()
    created = 0
    for slug, name, kind, color, icon, keywords in DEFAULT_CATEGORIES:
        _, was_created = Category.objects.get_or_create(
            household=household,
            slug=slug,
            defaults={
                "name": name,
                "kind": kind,
                "color": color,
                "icon": icon,
                "keywords": keywords,
                "is_system": True,
                "created_by": user,
            },
        )
        created += int(was_created)
    return created


def get_fallback_category(*, household=None) -> Category:
    category = Category.objects.filter(
        household=household, slug=FALLBACK_CATEGORY_SLUG
    ).first()
    if category is None:
        ensure_default_categories(household=household)
        category = Category.objects.filter(
            household=household, slug=FALLBACK_CATEGORY_SLUG
        ).first()
    if category is None:  # last resort, keeps imports alive
        category = Category.objects.create(
            slug=FALLBACK_CATEGORY_SLUG, name="Sonstiges",
            kind=Category.Kind.BOTH, is_system=True, household=household,
        )
    return category
