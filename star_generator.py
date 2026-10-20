#!/usr/bin/env python3
"""
Unique ASCII star generator.

The same seed always gives the same star, and different seeds give different
stars. Use something like "from|for" as the seed, so every greeting gets a
star that can be regenerated at any time.

Usage:
    python star.py                      # random seed
    python star.py "Anna|Erik"          # reproducible star for this seed
    python star.py "Anna|Erik" -H 41    # bigger (height in rows)
    python star.py "Anna|Erik" -o out.txt
"""

import argparse
import hashlib
import math
import random
import secrets

# Brightness ramps, dark -> bright (center of the star uses the last char)
RAMPS = [
    " .:-=+*#%@",
    " .⁺,:;ox%#@",
    " .'⋆*+xX#@",
    " .₊⋆:+*✢#@@",
    " .-+*o0O#@",
]

HALO_CHARS = ".'`:,"
SPARKLE_CHARS = "+*⋆⁺₊.'`x"


def seed_to_rng(seed) -> random.Random:
    digest = hashlib.sha256(str(seed).encode("utf-8")).hexdigest()
    return random.Random(int(digest, 16))


def generate_star(seed, height: int = 31) -> str:
    rng = seed_to_rng(seed)
    width = height * 2 - 1  # chars are ~2x taller than wide

    # ---- randomized star "DNA" -------------------------------------------
    n = rng.choice([4, 5, 5, 6, 6, 7, 8, 8, 9, 10, 12, 16])  # number of points
    phase = rng.uniform(0, 2 * math.pi / n)                    # rotation
    sharpness = rng.uniform(1.2, 6.0)                          # thin vs fat arms
    inner = rng.uniform(0.10, 0.40)                            # valley depth (fraction of R)
    jitter = rng.choice([0.0, 0.0, 0.1, 0.25, 0.4])            # arm length variation
    lengths = [1 - rng.uniform(0, jitter) for _ in range(n)]
    if n % 2 == 0 and rng.random() < 0.4:                      # alternating long/short arms
        short = rng.uniform(0.45, 0.8)
        lengths = [l if i % 2 == 0 else l * short for i, l in enumerate(lengths)]

    ramp = rng.choice(RAMPS)
    falloff = rng.uniform(0.5, 1.6)        # how fast brightness fades to the edge
    core_r = rng.uniform(0.04, 0.16)       # bright solid core (fraction of R)
    halo_len = rng.uniform(0.8, 3.0)       # halo reach in rows
    halo_strength = rng.uniform(0.3, 0.9)
    n_sparkles = rng.randint(8, 35)

    R = (height - 1) / 2 * 0.8             # leave room for halo + sparkles
    cx, cy = (width - 1) / 2, (height - 1) / 2

    grid = [[" "] * width for _ in range(height)]

    # ---- render star body + halo ------------------------------------------
    for row in range(height):
        for col in range(width):
            dx = (col - cx) * 0.5          # correct for character aspect ratio
            dy = row - cy
            d = math.hypot(dx, dy)
            theta = math.atan2(dy, dx)

            x = theta - phase
            peak = abs(math.cos(n * x / 2)) ** sharpness
            k = int(round(x * n / (2 * math.pi))) % n
            tip = R * lengths[k]
            r = R * inner + (tip - R * inner) * peak

            if d <= r:
                t = d / r if r > 0 else 0
                val = 0.2 + 0.8 * (1 - t) ** falloff
                if d <= R * core_r:
                    val = 1.0
                grid[row][col] = ramp[min(len(ramp) - 1, int(val * len(ramp)))]
            else:
                halo = halo_strength * math.exp(-(d - r) / halo_len)
                if rng.random() < halo * 0.7:
                    grid[row][col] = rng.choice(HALO_CHARS)

    # ---- sparkles in the surrounding sky -----------------------------------
    for _ in range(n_sparkles):
        row, col = rng.randrange(height), rng.randrange(width)
        if grid[row][col] != " ":
            continue
        if rng.random() < 0.15:  # little cross-shaped twinkle
            grid[row][col] = "+"
            for dr, dc, ch in ((0, -1, "-"), (0, 1, "-"), (-1, 0, "|"), (1, 0, "|")):
                rr, cc = row + dr, col + dc
                if 0 <= rr < height and 0 <= cc < width and grid[rr][cc] == " ":
                    grid[rr][cc] = ch
        else:
            grid[row][col] = rng.choice(SPARKLE_CHARS)

    return "\n".join("".join(line).rstrip() for line in grid)


def main():
    p = argparse.ArgumentParser(description="Generate a unique ASCII star.")
    p.add_argument("seed", nargs="?", default=None,
                   help='Seed text, e.g. "Anna|Erik". Random if omitted.')
    p.add_argument("-H", "--height", type=int, default=31, help="Height in rows (default 31)")
    p.add_argument("-o", "--out", help="Write to this file instead of printing")
    args = p.parse_args()

    seed = args.seed if args.seed is not None else secrets.token_hex(8)
    art = generate_star(seed, args.height)

    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(art + "\n")
        print(f"Wrote star for seed {seed!r} to {args.out}")
    else:
        print(art)
        print(f"\nseed: {seed}")


if __name__ == "__main__":
    main()