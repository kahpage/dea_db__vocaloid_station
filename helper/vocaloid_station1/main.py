import sys
import json
from pathlib import Path
from typing import Any
import requests
from bs4 import BeautifulSoup
import lxml
import re

# Add project root to sys.path (find the directory containing db_structs.py)
_root = Path(__file__).resolve().parent
while _root.parent != _root:
    if (_root / "db_structs.py").exists():
        if str(_root) not in sys.path:
            sys.path.append(str(_root))
        break
    _root = _root.parent

from db_structs import (
    Medium,
    Circle,
    Event,
    EventGroup,
    Source,
    ReliabilityTypes,
    OriginTypes,
    Location,
)

PATH_EVENT = Path(__file__).parent
PATH_CIRCLES_JSON = PATH_EVENT / "circles.json"
NAME = PATH_EVENT.name


def retrieve_soup_fetch_if_needed(url: str) -> BeautifulSoup:
    """Retrieve BeautifulSoup object for the given URL, fetching the content if necessary."""
    html_path = PATH_EVENT / "raw.html"
    if not html_path.exists():
        print(f"Raw HTML file not found, fetching from {url} ...")
        response = requests.get(url)
        if response.status_code != 200:
            raise Exception(
                f"Failed to retrieve data from {url}, status code: {response.status_code}"
            )
        # Handle encoding properly when fetching. Wayback Machine often wraps/redirects and
        # can cause requests to incorrectly guess ISO-8859-1. Correct encoding is CP932/Shift_JIS.
        response.encoding = response.apparent_encoding or "shift_jis"
        html_path.write_text(response.text, encoding="utf-8")
    
    try:
        with html_path.open("r", encoding="utf-8") as f:
            return BeautifulSoup(f, "lxml")
    except UnicodeDecodeError:
        with html_path.open("r", encoding="cp932") as f:
            return BeautifulSoup(f, "lxml")


def sanitize_string(s: str) -> str:
    s = s.strip()
    s = re.sub(r"[\s\n\t]+", " ", s)
    return s


def main():
    """Create circles.json"""
    print(f"Retrieving circles information for {NAME} ...")
    raw_url = "https://web.archive.org/web/20130710182339fw_/http://slash.sakuraweb.com/event/circlelist.htm"
    
    # Parse the HTML content to extract circle information
    soup = retrieve_soup_fetch_if_needed(raw_url)
    circles = []

    # Find the innermost table that contains "サークル名" (the circles list headers)
    table = None
    for t in soup.find_all("table"):
        if "サークル名" in t.get_text() and not t.find("table"):
            table = t
            break

    if not table:
        raise Exception("Failed to find the circles table in the HTML content.")

    table_rows = table.select("tr")
    if not table_rows:
        raise Exception("No rows found in the circles table.")
    
    active = False

    for row in table_rows:
            cols = row.select("td")
            if len(cols) < 1:
                continue  # Skip rows that don't have enough columns
            position = sanitize_string(cols[0].get_text())
            if position == "VOCALOID STATION":
                active = True
                continue  # Only VOCALOID STATION

            if len(cols) < 4 or not active:
                continue  # Skip rows that don't have enough columns or are not active

            circle_name = sanitize_string(cols[1].get_text())
            pen_name = sanitize_string(cols[2].get_text())
            genre = sanitize_string(cols[3].get_text())
            comment_parts = [f"ジャンル: {genre}"] if genre else []

            circle = Circle(
                aliases=[circle_name],
                pen_names=[pen_name] if pen_name else None,
                position=position,
                comments=", ".join(comment_parts) if comment_parts else None,
            )

            circles.append(circle)

    # Save the extracted circle information to a JSON file
    with open(PATH_CIRCLES_JSON, "w", encoding="utf-8") as f:
        json.dump([c.get_json() for c in circles], f, ensure_ascii=False, indent=2)
    print(f"Saved {len(circles)} circles to {PATH_CIRCLES_JSON}")


if __name__ == "__main__":
    main()
