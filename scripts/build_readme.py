"""
Builds README.md from README.template.md using live GitHub profile data.
Nothing is hardcoded: username comes from the repo owner, everything else
(name, bio, location, website, email, socials, top languages) from the GitHub API.

Env:
  GITHUB_REPOSITORY_OWNER / GH_USER  username
  GITHUB_REPOSITORY                  owner/repo (for raw links)
  GITHUB_TOKEN                       optional (higher rate limit)
"""
import collections
import json
import os
import re
import sys
import urllib.parse as up
import urllib.request

USER = os.getenv("GH_USER") or os.getenv("GITHUB_REPOSITORY_OWNER")
REPO = os.getenv("GITHUB_REPOSITORY") or (f"{USER}/{USER}" if USER else None)
TOKEN = os.getenv("GITHUB_TOKEN")
if not USER:
    sys.exit("Set GH_USER or GITHUB_REPOSITORY_OWNER")

LANG_ICONS = {
    "JavaScript": "js", "TypeScript": "ts", "Python": "py", "Java": "java",
    "C++": "cpp", "C": "c", "C#": "cs", "HTML": "html", "CSS": "css",
    "SCSS": "sass", "Go": "go", "Rust": "rust", "PHP": "php", "Ruby": "ruby",
    "Kotlin": "kotlin", "Swift": "swift", "Dart": "dart", "Shell": "bash",
    "Jupyter Notebook": "jupyter", "Dockerfile": "docker", "Vue": "vue",
    "Svelte": "svelte", "Lua": "lua", "R": "r", "MATLAB": "matlab",
    "Scala": "scala", "Haskell": "haskell", "PowerShell": "powershell",
}


def api(path):
    req = urllib.request.Request(
        f"https://api.github.com{path}",
        headers={"Accept": "application/vnd.github+json", "User-Agent": "profile-readme-builder"},
    )
    if TOKEN:
        req.add_header("Authorization", f"Bearer {TOKEN}")
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def clean(s):
    return re.sub(r"\s+", " ", (s or "")).strip()


def yq(s):
    """YAML-safe value."""
    s = clean(s).replace('"', "'")
    return f'"{s}"' if re.search(r"[:#\[\]{}&*!|>%@`,]", s) else s


def esc(s):
    """shields.io static badge escaping: - -> --, _ -> __, then URL-encode."""
    return up.quote(s.replace("-", "--").replace("_", "__"), safe="")


def badge(label, url, logo, text):
    return (f'  <a href="{url}"><img src="https://img.shields.io/badge/{esc(label)}-{esc(text)}'
            f'-0d1117?style=for-the-badge&logo={logo}&logoColor=39d353" alt="{label}"/></a>')


u = api(f"/users/{USER}")
try:
    repos = api(f"/users/{USER}/repos?per_page=100&type=owner&sort=updated")
except Exception:
    repos = []

name = clean(u.get("name")) or u["login"]
bio = clean(u.get("bio"))
location = clean(u.get("location"))
company = clean(u.get("company"))
blog = clean(u.get("blog"))
email = clean(u.get("email"))
twitter = clean(u.get("twitter_username"))
if blog and not blog.startswith("http"):
    blog = "https://" + blog

# ---- top languages -> skill icons
count = collections.Counter(r["language"] for r in repos if r.get("language") and not r.get("fork"))
icons = [LANG_ICONS[l] for l, _ in count.most_common() if l in LANG_ICONS][:10]
icons += ["git", "github", "vscode"]
tech_icons = ",".join(dict.fromkeys(icons))  # de-dupe, keep order

# ---- about block
about = [("name", name), ("username", u["login"])]
if bio:      about.append(("bio", bio))
if company:  about.append(("company", company.lstrip("@")))
if location: about.append(("location", location))
if blog:     about.append(("website", blog))
about += [
    ("member_since", (u.get("created_at") or "")[:4]),
    ("public_repos", str(u.get("public_repos", 0))),
    ("followers", str(u.get("followers", 0))),
    ("status", "● online & committing"),
]
width = max(len(k) for k, _ in about) + 2
about_yaml = "\n".join(f"{(k + ':').ljust(width)}{yq(v)}" for k, v in about)

# ---- typing lines
lines = [f"{u['login']}@github ~ $ whoami"]
if bio:
    lines.append(bio[:60])
if count:
    top = [l for l, _ in count.most_common(3)]
    lines.append("I code in " + ", ".join(top))
lines.append("Open to collaborate 🚀")
typing = ";".join(up.quote_plus(l) for l in lines)

# ---- social badges (only what exists on the profile)
b = [badge("GitHub", f"https://github.com/{u['login']}", "github", u["login"])]
if blog:
    if "linkedin.com" in blog.lower():
        b.append(badge("LinkedIn", blog, "linkedin", "Connect"))
    else:
        b.append(badge("Website", blog, "googlechrome", re.sub(r"^https?://", "", blog).rstrip("/")[:30]))
if twitter:
    b.append(badge("X", f"https://x.com/{twitter}", "x", f"@{twitter}"))
if email:
    b.append(badge("Email", f"mailto:{email}", "gmail", "Contact"))
social = "\n".join(b)

tagline = bio[:80] if bio else "~/ building things | breaking things | learning things"

values = {
    "USERNAME": u["login"],
    "NAME_URL": up.quote(name, safe=""),
    "TAGLINE_URL": up.quote(tagline, safe=""),
    "TYPING_LINES": typing,
    "ABOUT_YAML": about_yaml,
    "TECH_ICONS": tech_icons,
    "SOCIAL_BADGES": social,
    "REPO": REPO,
}

with open("README.template.md", encoding="utf-8") as f:
    out = f.read()
for k, v in values.items():
    out = out.replace("{{" + k + "}}", v)

left = re.findall(r"\{\{[A-Z_]+\}\}", out)
if left:
    sys.exit(f"Unfilled placeholders: {left}")

with open("README.md", "w", encoding="utf-8") as f:
    f.write(out)
print(f"README.md built for {u['login']} ({name})")
