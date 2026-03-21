"""CLI entrypoint for the legal transcript document workflow."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from depo_formatter.ufm_engine.document_builder import DocumentBuilder

CLI_APP_NAME = "Legal Transcript System"


def get_non_empty_input(prompt: str) -> str:
    """Prompt until the user enters a non-empty value."""
    while True:
        value = input(prompt).strip()
        if value:
            return value
        print("Input cannot be empty. Please try again.")


def get_yes_no(prompt: str) -> bool:
    """Prompt until the user enters y or n."""
    while True:
        value = input(prompt).strip().lower()
        if value == "y":
            return True
        if value == "n":
            return False
        print("Please enter 'y' or 'n'.")


def get_valid_date(prompt: str) -> str:
    """Prompt until the user enters a valid ISO date string."""
    while True:
        value = input(prompt).strip()
        try:
            datetime.strptime(value, "%Y-%m-%d")
        except ValueError:
            print("Please enter a valid date in YYYY-MM-DD format.")
            continue
        return value


def main() -> None:
    """Run the CLI workflow for transcript generation."""
    print(f"\n--- {CLI_APP_NAME} ---\n")

    witness_name = get_non_empty_input("Enter witness name: ")
    date = get_valid_date("Enter proceeding date (YYYY-MM-DD): ")
    is_remote = get_yes_no("Is this a remote proceeding? (y/n): ")
    reporter_name = get_non_empty_input("Enter reporter name: ")
    csr_number = get_non_empty_input("Enter CSR number: ")
    include_signature = get_yes_no("Include signature pages? (y/n): ")

    job_data = {
        "witness_name": witness_name,
        "date": date,
        "is_remote": is_remote,
        "reporter_name": reporter_name,
        "csr_number": csr_number,
        "include_signature": include_signature,
    }

    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)

    safe_name = "".join(char if char.isalnum() else "_" for char in witness_name).strip("_").lower()
    if not safe_name:
        safe_name = "transcript"

    output_path = output_dir / f"transcript_{safe_name}.docx"
    builder = DocumentBuilder()

    try:
        print("\nGenerating legal transcript package...\n")
        builder.build_document(job_data, str(output_path))
        print("Legal transcript package created successfully")
        print(f"Saved to: {output_path}")
    except Exception as exc:
        print("\nError generating legal transcript package")
        print(str(exc))


if __name__ == "__main__":
    main()
