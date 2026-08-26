import os
from datetime import date, datetime, timedelta
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
        "background": "#F7FAF8",
        "surface": "#FFFFFF",
        "border": "#DCE7E1",
        "text": "#17221C",
        "muted": "#5B6B62",
        "accent": "#1F7D53",
        "accent_soft": "#E8F3ED",
        "ring_bg": "#DDE8E1",
    },
    "dark": {
        "background": "#0B1110",
        "surface": "#111A17",
        "border": "#26352E",
        "text": "#E8F1EC",
        "muted": "#9BAEA4",
        "accent": "#08CB00",
        "accent_soft": "#17321F",
        "ring_bg": "#26352E",
    },
}


def github_query():
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


def get_days(calendar):
    days = []

    for week in calendar["weeks"]:
        for item in week["contributionDays"]:
            days.append(
                {
                    "date": date.fromisoformat(item["date"]),
                    "count": item["contributionCount"],
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

    today = max(counts)

    current = 0
    cursor = today

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


def load_font(size):
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    ]

    path = candidates[1 if size >= 24 else 0]

    return ImageFont.truetype(path, size)


def centered(draw, box, text, font, fill):
    bbox = draw.textbbox((0, 0), text, font=font)

    width = bbox[2] - bbox[0]
    height = bbox[3] - bbox[1]

    x = box[0] + ((box[2] - box[0]) - width) / 2
    y = box[1] + ((box[3] - box[1]) - height) / 2

    draw.text(
        (x, y),
        text,
        font=font,
        fill=fill,
    )


def rounded(draw, box, radius, fill, outline=None, width=1):
    draw.rounded_rectangle(
        box,
        radius=radius,
        fill=fill,
        outline=outline,
        width=width,
    )


def draw_card(theme, total, current, longest):
    colors = THEMES[theme]

    width = 900
    height = 360

    image = Image.new(
        "RGB",
        (width, height),
        colors["background"],
    )

    draw = ImageDraw.Draw(image)

    rounded(
        draw,
        (2, 2, width - 2, height - 2),
        24,
        colors["surface"],
        colors["border"],
        2,
    )

    draw.text(
        (40, 28),
        "GitHub Stats",
        font=load_font(28),
        fill=colors["text"],
    )

    draw.line(
        (24, 82, width - 24, 82),
        fill=colors["border"],
        width=1,
    )

    values = [
        ("Total Contributions", total),
        ("Current Streak", current),
        ("Longest Streak", longest),
    ]

    centers = [220, 450, 680]

    for (label, value), center_x in zip(values, centers):
        centered(
            draw,
            (
                center_x - 100,
                115,
                center_x + 100,
                175,
            ),
            str(value),
            load_font(40),
            colors["text"],
        )

        centered(
            draw,
            (
                center_x - 110,
                180,
                center_x + 110,
                215,
            ),
            label,
            load_font(15),
            colors["accent"],
        )

    # Streak ring
    ring_center = (450, 275)
    radius = 43

    draw.ellipse(
        (
            ring_center[0] - radius,
            ring_center[1] - radius,
            ring_center[0] + radius,
            ring_center[1] + radius,
        ),
        outline=colors["ring_bg"],
        width=10,
    )

    if current > 0:
        draw.arc(
            (
                ring_center[0] - radius,
                ring_center[1] - radius,
                ring_center[0] + radius,
                ring_center[1] + radius,
            ),
            start=-90,
            end=-90 + min(current / max(longest, current, 1), 1) * 360,
            fill=colors["accent"],
            width=10,
        )

    centered(
        draw,
        (
            ring_center[0] - 35,
            ring_center[1] - 20,
            ring_center[0] + 35,
            ring_center[1] + 20,
        ),
        str(current),
        load_font(24),
        colors["text"],
    )

    centered(
        draw,
        (300, 325, 600, 350),
        f"@{USERNAME}",
        load_font(13),
        colors["muted"],
    )

    output = OUTPUT_DIR / f"stats-{theme}.png"

    image.save(
        output,
        "PNG",
        optimize=True,
    )

    print(f"Generated {output}")


def main():
    calendar = github_query()

    days = get_days(calendar)

    total = calendar["totalContributions"]

    current, longest = calculate_streaks(days)

    print(f"Total contributions: {total}")
    print(f"Current streak: {current}")
    print(f"Longest streak: {longest}")

    draw_card(
        "light",
        total,
        current,
        longest,
    )

    draw_card(
        "dark",
        total,
        current,
        longest,
    )


if __name__ == "__main__":
    main()
