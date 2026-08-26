import os
from datetime import date, timedelta
from pathlib import Path

import requests
from PIL import Image, ImageDraw, ImageFont


USERNAME = os.environ["GITHUB_USERNAME"]
TOKEN = os.environ["GITHUB_TOKEN"]

ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = ROOT / "assets" / "github"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


THEMES = {
    "light": {
        "background": "#F5F8F6",
        "surface": "#FFFFFF",
        "border": "#DCE7E1",
        "text": "#17221C",
        "muted": "#66756D",
        "accent": "#1F7D53",
        "ring_bg": "#DCE8E1",
    },
    "dark": {
        "background": "#0B1110",
        "surface": "#111A17",
        "border": "#26352E",
        "text": "#E8F1EC",
        "muted": "#9BAEA4",
        "accent": "#08CB00",
        "ring_bg": "#26352E",
    },
}


def get_calendar():
    query = """
    query($login: String!) {
      user(login: $login) {
        contributionsCollection {
          contributionCalendar {
            totalContributions
            weeks {
              contributionDays {
                contributionCount
                date
              }
            }
          }
        }
      }
    }
    """

    response = requests.post(
        "https://api.github.com/graphql",
        headers={
            "Authorization": f"Bearer {TOKEN}",
            "Accept": "application/vnd.github+json",
        },
        json={
            "query": query,
            "variables": {
                "login": USERNAME,
            },
        },
        timeout=30,
    )

    response.raise_for_status()

    payload = response.json()

    if "errors" in payload:
        raise RuntimeError(payload["errors"])

    return payload["data"]["user"]["contributionsCollection"][
        "contributionCalendar"
    ]


def extract_days(calendar):
    days = []

    for week in calendar["weeks"]:
        for contribution in week["contributionDays"]:
            days.append(
                {
                    "date": date.fromisoformat(
                        contribution["date"]
                    ),
                    "count": contribution["contributionCount"],
                }
            )

    days.sort(key=lambda item: item["date"])

    return days


def calculate_streaks(days):
    if not days:
        return 0, 0

    counts = {
        item["date"]: item["count"]
        for item in days
    }

    latest_date = max(counts)

    current = 0
    cursor = latest_date

    while counts.get(cursor, 0) > 0:
        current += 1
        cursor -= timedelta(days=1)

    longest = 0
    running = 0

    for item in days:
        if item["count"] > 0:
            running += 1
            longest = max(longest, running)
        else:
            running = 0

    return current, longest


def font(size, bold=False):
    if bold:
        path = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
    else:
        path = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"

    return ImageFont.truetype(path, size)


def center_text(draw, x, y, text, text_font, fill):
    box = draw.textbbox(
        (0, 0),
        text,
        font=text_font,
    )

    width = box[2] - box[0]
    height = box[3] - box[1]

    draw.text(
        (
            x - width / 2,
            y - height / 2,
        ),
        text,
        font=text_font,
        fill=fill,
    )


def create_stats_card(theme, total, current, longest):
    colors = THEMES[theme]

    width = 900
    height = 390

    image = Image.new(
        "RGB",
        (width, height),
        colors["background"],
    )

    draw = ImageDraw.Draw(image)

    draw.rounded_rectangle(
        (2, 2, width - 2, height - 2),
        radius=24,
        fill=colors["surface"],
        outline=colors["border"],
        width=2,
    )

    draw.text(
        (40, 28),
        "GitHub Stats",
        font=font(28, bold=True),
        fill=colors["text"],
    )

    draw.line(
        (24, 84, width - 24, 84),
        fill=colors["border"],
        width=1,
    )

    columns = [
        (225, total, "Total Contributions"),
        (450, current, "Current Streak"),
        (675, longest, "Longest Streak"),
    ]

    for x, value, label in columns:
        center_text(
            draw,
            x,
            145,
            str(value),
            font(42, bold=True),
            colors["text"],
        )

        center_text(
            draw,
            x,
            198,
            label,
            font(15),
            colors["accent"],
        )

    ring_x = 450
    ring_y = 292
    radius = 43

    draw.ellipse(
        (
            ring_x - radius,
            ring_y - radius,
            ring_x + radius,
            ring_y + radius,
        ),
        outline=colors["ring_bg"],
        width=9,
    )

    if current > 0:
        percentage = current / max(longest, current, 1)

        draw.arc(
            (
                ring_x - radius,
                ring_y - radius,
                ring_x + radius,
                ring_y + radius,
            ),
            start=-90,
            end=-90 + percentage * 360,
            fill=colors["accent"],
            width=9,
        )

    center_text(
        draw,
        ring_x,
        ring_y,
        str(current),
        font(23, bold=True),
        colors["text"],
    )

    center_text(
        draw,
        width / 2,
        365,
        f"@{USERNAME}",
        font(13),
        colors["muted"],
    )

    output = OUTPUT_DIR / f"stats-{theme}.png"

    image.save(
        output,
        "PNG",
        optimize=True,
    )

    print(f"Generated: {output}")


def main():
    calendar = get_calendar()
    days = extract_days(calendar)

    total = calendar["totalContributions"]

    current, longest = calculate_streaks(days)

    print(f"Total contributions: {total}")
    print(f"Current streak: {current}")
    print(f"Longest streak: {longest}")

    create_stats_card(
        "light",
        total,
        current,
        longest,
    )

    create_stats_card(
        "dark",
        total,
        current,
        longest,
    )


if __name__ == "__main__":
    main()
