#!/usr/bin/env python3
"""
Generate one Hugo markdown page per greeting.

Reads greetings.txt (lines like "Anna|Erik"), and for each one writes
content/stars/<slug>.md containing:
  - a unique ASCII star (from star_generator.py, seeded by the greeting)
  - a real star it "shines like", with real facts and a color

Run from the root of your Hugo site:
    python generate_pages.py
    python generate_pages.py --clean      # delete old generated pages first

The output is deterministic: running it again gives identical pages
(apart from the "light left in the year" fact, which depends on the current year).
"""

import argparse
import datetime
import hashlib
import json
import math
import re
import sys
import unicodedata
from collections import Counter
from pathlib import Path

from star_generator import generate_star, seed_to_rng

KM_PER_LY = 9.4607e12
JET_KMH = 900
HOURS_PER_YEAR = 8766

# (name, constellation, distance in light-years, spectral type,
#  apparent magnitude, color, fun fact)
# Colors follow spectral class: B blue-white, A white-blue, F white,
# G yellow-white, K orange, M red-orange.
B, A, F, G, K, M = "#aabfff", "#cad7ff", "#f8f7ff", "#fff4ea", "#ffd2a1", "#ffbd6f"
REAL_STARS = [
    ("Sirius", "Canis Major", 8.6, "A1V", -1.46, A,
     "The brightest star in the night sky. It has a faint white dwarf companion."),
    ("Alpha Centauri A", "Centaurus", 4.37, "G2V", 0.01, G,
     "Part of the closest star system to our Sun."),
    ("Proxima Centauri", "Centaurus", 4.25, "M5.5Ve", 11.1, M,
     "The closest star to the Sun, yet far too faint to see without a telescope."),
    ("Betelgeuse", "Orion", 550, "M1-2Ia", "varies between 0.0 and 1.6", M,
     "A red supergiant so huge that, in place of the Sun, it would swallow the orbits of Mercury, Venus, Earth and Mars."),
    ("Vega", "Lyra", 25, "A0V", 0.03, A,
     "It was the North Star about 14,000 years ago, and will be again in about 12,000 years."),
    ("Polaris", "Ursa Minor", 446, "F7Ib", 1.98, F,
     "The North Star: it hardly moves while the whole sky turns around it."),
    ("Rigel", "Orion", 860, "B8Ia", 0.13, B,
     "Shines with the light of roughly 120,000 Suns."),
    ("Arcturus", "Bootes", 37, "K1.5III", -0.05, K,
     "In 1933 its light was used to switch on the lights of the Chicago World's Fair."),
    ("Capella", "Auriga", 43, "G8III", 0.08, G,
     "Actually four stars: two bright yellow giants and two small red dwarfs."),
    ("Procyon", "Canis Minor", 11.5, "F5IV-V", 0.34, F,
     "Its name means 'before the dog', because it rises ahead of Sirius, the Dog Star."),
    ("Aldebaran", "Taurus", 65, "K5III", 0.85, K,
     "The glowing orange eye of Taurus the Bull."),
    ("Antares", "Scorpius", 550, "M1.5Iab", 1.06, M,
     "Its name means 'rival of Mars', because it is just as red."),
    ("Altair", "Aquila", 16.7, "A7V", 0.76, A,
     "Spins so fast (a day lasts under 9 hours) that it is squashed into an oval."),
    ("Deneb", "Cygnus", 1500, "A2Ia", 1.25, A,
     "One of the most luminous stars you can see, shining with the light of at least 50,000 Suns."),
    ("Spica", "Virgo", 250, "B1 III-IV", 0.97, B,
     "Really two stars orbiting each other so closely that gravity stretches them into egg shapes."),
    ("Regulus", "Leo", 79, "B8IV", 1.35, B,
     "A system of four stars, and the main one spins so fast it is flattened."),
    ("Fomalhaut", "Piscis Austrinus", 25, "A3V", 1.16, A,
     "Surrounded by a huge ring of dust and debris where planets may be forming."),
    ("Canopus", "Carina", 310, "A9II", -0.74, A,
     "The second-brightest star in the night sky."),
    ("Pollux", "Gemini", 34, "K0III", 1.14, K,
     "Has a planet named Thestias orbiting it."),
    ("Castor", "Gemini", 51, "A1V", 1.58, A,
     "Actually a system of six stars."),
    ("Tau Ceti", "Cetus", 11.9, "G8V", 3.5, G,
     "A Sun-like star that has long been a favourite target for alien-hunters."),
    ("Algol", "Perseus", 93, "B8V", "between 2.1 and 3.4", B,
     "The 'Demon Star': every 2.87 days it dims as a companion star passes in front of it."),
    ("Mira", "Cetus", 300, "M7IIIe", "between 2.0 and 10.1", M,
     "Pulses in brightness over about 11 months, swinging from easily visible to nearly invisible."),
    ("Bellatrix", "Orion", 250, "B2III", 1.64, B,
     "Its name is Latin for 'female warrior'."),
    ("Alnilam", "Orion", 1250, "B0Ia", 1.69, B,
     "The middle star of Orion's Belt. Its name means 'string of pearls'."),
    ("Epsilon Eridani", "Eridanus", 10.5, "K2V", 3.73, K,
     "A young star, only about a billion years old, with a giant planet and dusty discs around it."),
    ("Thuban", "Draco", 300, "A0III", 3.65, A,
     "It was the North Star when the Egyptian pyramids were built."),
]


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def read_greetings(path: Path):
    """Return a list of (sender, recipient) tuples."""
    greetings = []
    for lineno, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.count("|") != 1:
            print(f"warning: {path}:{lineno}: expected 'from|for', skipping: {raw!r}",
                  file=sys.stderr)
            continue
        sender, recipient = (p.strip() for p in line.split("|"))
        if not sender or not recipient:
            print(f"warning: {path}:{lineno}: empty name, skipping: {raw!r}",
                  file=sys.stderr)
            continue
        greetings.append((sender, recipient))
    return greetings


def slugify(text: str) -> str:
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def md_escape(text: str) -> str:
    return re.sub(r"([\\`*_\[\]<>#])", r"\\\1", text)


_SUP = str.maketrans("-0123456789", "⁻⁰¹²³⁴⁵⁶⁷⁸⁹")


def sci(x: float) -> str:
    exp = math.floor(math.log10(x))
    return f"{x / 10 ** exp:.1f} × 10{str(exp).translate(_SUP)}"


def fmt_ly(ly: float) -> str:
    return f"{round(ly):,}" if ly >= 100 else f"{ly:g}"


def fmt_years(y: float) -> str:
    if y >= 1e9:
        return f"{y / 1e9:.1f} billion"
    if y >= 1e6:
        return f"{y / 1e6:.1f} million"
    return f"{round(y):,}"


def fmt_year(y: int) -> str:
    return f"the year {y}" if y > 0 else f"{1 - y} BC"


# ---------------------------------------------------------------------------
# page building
# ---------------------------------------------------------------------------

def build_page(sender: str, recipient: str, seed: str, year: int, height: int) -> str:
    art = generate_star(seed, height)

    # Pick a real star deterministically from the seed
    rng = seed_to_rng("real:" + seed)
    name, const, ly, spectral, mag, color, fact = rng.choice(REAL_STARS)

    catalogue = "XMAS-" + hashlib.sha256(seed.encode("utf-8")).hexdigest()[:6].upper()
    km = ly * KM_PER_LY
    jet_years = km / JET_KMH / HOURS_PER_YEAR
    light_year = year - round(ly)

    title = f"For {recipient}, from {sender}"
    s, r = md_escape(sender), md_escape(recipient)

    return f"""---
title: {json.dumps(title, ensure_ascii=False)}
from: {json.dumps(sender, ensure_ascii=False)}
for: {json.dumps(recipient, ensure_ascii=False)}
star: {json.dumps(name)}
color: {json.dumps(color)}
catalogue: {json.dumps(catalogue)}
---

*Merry Christmas, {r}! {s} wanted you to have a star of your very own:*

~~~~
{art}
~~~~

| | |
|---|---|
| Catalogue no. | {catalogue} |
| Shines like | {name}, in the constellation {const} |
| Distance from Earth | {fmt_ly(ly)} light-years (about {sci(km)} km) |
| The light you see left in | {fmt_year(light_year)} |
| Time to fly there by jet | about {fmt_years(jet_years)} years |
| Spectral type | {spectral} |
| Brightness | magnitude {mag} (lower means brighter) |
| Fun fact | {fact} |
"""


def main():
    ap = argparse.ArgumentParser(description="Generate Hugo star pages from greetings.txt")
    ap.add_argument("-i", "--input", default="greetings.txt", help="greetings file (default: greetings.txt)")
    ap.add_argument("-o", "--out", default="content/stars", help="output dir (default: content/stars)")
    ap.add_argument("-H", "--height", type=int, default=31, help="star height in rows (default: 31)")
    ap.add_argument("--clean", action="store_true",
                    help="delete existing .md files in the output dir first (keeps _index.md)")
    args = ap.parse_args()

    in_path, out_dir = Path(args.input), Path(args.out)
    if not in_path.exists():
        sys.exit(f"error: {in_path} not found (run this from your Hugo site root)")

    greetings = read_greetings(in_path)
    out_dir.mkdir(parents=True, exist_ok=True)

    if args.clean:
        for f in out_dir.glob("*.md"):
            if f.name != "_index.md":
                f.unlink()

    year = datetime.date.today().year
    seen_seeds = Counter()
    used_slugs = set()

    for sender, recipient in greetings:
        base_seed = f"{sender}|{recipient}"
        seen_seeds[base_seed] += 1
        n = seen_seeds[base_seed]
        # a repeat purchase of the exact same greeting gets its own star
        seed = base_seed if n == 1 else f"{base_seed}#{n}"

        base_slug = slugify(f"{sender}-{recipient}") or "star"
        slug, i = base_slug, 2
        while slug in used_slugs:
            slug = f"{base_slug}-{i}"
            i += 1
        used_slugs.add(slug)

        page = build_page(sender, recipient, seed, year, args.height)
        (out_dir / f"{slug}.md").write_text(page, encoding="utf-8")
        print(f"  {slug}.md")

    print(f"Generated {len(greetings)} page(s) in {out_dir}/")


if __name__ == "__main__":
    main()