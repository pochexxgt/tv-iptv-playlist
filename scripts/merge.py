"""Merge Free-TV/IPTV with iptv-org country playlists into one M3U.

Each iptv-org channel gets its country as group-title, so the TV app
can filter by country. Duplicate stream URLs are dropped.
"""
import re
import sys
import urllib.request

FREE_TV = "https://raw.githubusercontent.com/Free-TV/IPTV/master/playlist.m3u8"
IPTV_ORG = "https://iptv-org.github.io/iptv/countries/{}.m3u"
# iptv-org code -> group name (Korea/Indonesia match Free-TV's own groups)
COUNTRIES = {"my": "Malaysia", "sg": "Singapore", "kr": "Korea", "id": "Indonesia"}

# Malaysia is the default group; these come first, so TV1 is channel 1
MY_FIRST = ["TV1", "TV2", "Berita RTM", "Okey"]

GROUP_RE = re.compile(r'group-title="[^"]*"')


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "tv-playlist-merge"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read().decode("utf-8", errors="replace")


def entries(text):
    """Yield (extinf_line, extra_lines, url) for each channel."""
    info, extra = None, []
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#EXTM3U"):
            continue
        if line.startswith("#EXTINF"):
            info, extra = line, []
        elif line.startswith("#"):
            if info:
                extra.append(line)
        elif info:
            yield info, extra, line
            info, extra = None, []


def my_rank(info):
    title = info.rsplit(",", 1)[-1]
    for i, name in enumerate(MY_FIRST):
        if title.startswith(name):
            return i
    return len(MY_FIRST)


def with_group(info, group):
    if GROUP_RE.search(info):
        return GROUP_RE.sub(f'group-title="{group}"', info, count=1)
    return info.replace("#EXTINF:-1", f'#EXTINF:-1 group-title="{group}"', 1)


def main(out_path):
    seen, out, counts = set(), ["#EXTM3U"], {}
    asian = []
    for code, name in COUNTRIES.items():
        chans = list(entries(fetch(IPTV_ORG.format(code))))
        if code == "my":
            chans.sort(key=lambda c: my_rank(c[0]))
        for info, extra, url in chans:
            asian.append((with_group(info, name), extra, url, name))
    free = [(i, e, u, None) for i, e, u in entries(fetch(FREE_TV))]
    # Asian groups first so they sit near the top of the group list
    for info, extra, url, name in asian + free:
        if url in seen:
            continue
        seen.add(url)
        out += [info, *extra, url]
        key = name or "Free-TV"
        counts[key] = counts.get(key, 0) + 1
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(out) + "\n")
    print(counts)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "playlist.m3u")
