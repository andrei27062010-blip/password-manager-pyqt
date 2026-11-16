import csv


FIELD_ALIASES = {
    "service": {"service", "name", "title", "website", "site", "url"},
    "login": {"login", "username", "user", "email"},
    "password": {"password", "pass"},
    "notes": {"notes", "note", "comment", "comments"},
    "category": {"category", "folder", "group"},
    "is_favorite": {"is_favorite", "favorite", "favourite", "starred"},
}


def _normalize_header(value):
    return "".join(char for char in (value or "").strip().casefold()
                   if char.isalnum())


def read_csv(path):
    """Читает CSV Google Password Manager или собственного формата."""
    with open(path, "r", encoding="utf-8-sig", newline="") as csv_file:
        reader = csv.DictReader(csv_file)
        if not reader.fieldnames:
            raise ValueError("В CSV-файле отсутствует строка заголовков.")

        normalized_headers = {
            _normalize_header(header): header for header in reader.fieldnames
        }
        columns = {}
        for field, aliases in FIELD_ALIASES.items():
            for alias in aliases:
                original = normalized_headers.get(_normalize_header(alias))
                if original is not None:
                    columns[field] = original
                    break

        missing = [field for field in ("service", "login", "password")
                   if field not in columns]
        if missing:
            names = {"service": "сервис или name", "login": "логин или username",
                     "password": "password"}
            raise ValueError(
                "Не найдены обязательные столбцы: "
                + ", ".join(names[field] for field in missing)
            )

        records = []
        for line_number, row in enumerate(reader, start=2):
            if not any((value or "").strip() for value in row.values()):
                continue

            service = (row.get(columns["service"]) or "").strip()
            login = (row.get(columns["login"]) or "").strip()
            password = row.get(columns["password"]) or ""
            if not service or not login or not password:
                raise ValueError(
                    f"Строка {line_number}: сервис, логин и пароль должны быть заполнены."
                )

            favorite_value = (row.get(columns.get("is_favorite", "")) or "").strip().casefold()
            records.append({
                "service": service,
                "login": login,
                "password": password,
                "notes": (row.get(columns.get("notes", "")) or "").strip(),
                "category": (row.get(columns.get("category", "")) or "").strip(),
                "is_favorite": favorite_value in {"1", "true", "yes", "да", "★", "избранное"},
            })

    if not records:
        raise ValueError("В CSV-файле нет записей для импорта.")
    return records


def write_csv(path, records):
    """Сохраняет записи в формате, совместимом с Google CSV и расширенном полями."""
    fieldnames = ["name", "url", "username", "password", "note",
                  "category", "is_favorite"]
    with open(path, "w", encoding="utf-8-sig", newline="") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()
        for record in records:
            writer.writerow({
                "name": record["service"],
                "url": "",
                "username": record["login"],
                "password": record["password"],
                "note": record.get("notes") or "",
                "category": record.get("category") or "",
                "is_favorite": "true" if record.get("is_favorite") else "false",
            })
