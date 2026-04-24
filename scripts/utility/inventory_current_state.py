"""Inventory Current Project State

This script scans the repository and produces a concise markdown report
describing the existing PostgreSQL schemas, tables, materialized views,
Python ingestion scripts, model training scripts, and FastAPI service
endpoints. The output is written to `docs/agents/CURRENT_INVENTORY.md`.

It is deliberately lightweight and uses only the standard library so it
can run in any environment without additional dependencies.
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent  # project root


def list_sql_objects() -> list[str]:
    """Collect .sql files that likely define schemas, tables or views.

    The function returns relative paths from the project root.
    """
    sql_dir = ROOT / "sql"
    return [str(p.relative_to(ROOT)) for p in sql_dir.rglob("*.sql")]


def list_python_scripts() -> list[str]:
    """Collect Python scripts that are part of the ingestion / model pipeline."""
    scripts_dir = ROOT / "scripts"
    return [str(p.relative_to(ROOT)) for p in scripts_dir.rglob("*.py")]


def list_fastapi_routes() -> list[str]:
    """Detect FastAPI route files under `baseball-chatbot-ui/app/api`."""
    api_dir = ROOT / "baseball-chatbot-ui" / "app" / "api"
    routes = []
    for p in api_dir.rglob("route.py"):
        rel = str(p.relative_to(ROOT))
        routes.append(rel)
    return routes


def generate_report() -> str:
    lines = ["# Project Inventory", ""]
    lines.append("## SQL Objects")
    for path in sorted(list_sql_objects()):
        lines.append(f"- `{path}`")
    lines.append("")
    lines.append("## Python Scripts")
    for path in sorted(list_python_scripts()):
        lines.append(f"- `{path}`")
    lines.append("")
    lines.append("## FastAPI Service Endpoints")
    for path in sorted(list_fastapi_routes()):
        lines.append(f"- `{path}`")
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    report = generate_report()
    out_path = ROOT / "docs" / "agents" / "CURRENT_INVENTORY.md"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(report, encoding="utf-8")
    print(f"Inventory written to {out_path}")


if __name__ == "__main__":
    main()
