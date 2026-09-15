#!/usr/bin/env python3
"""ตรวจ static site ของ nithep/landing ก่อน deploy (Cloudflare Pages — ไม่มี build step)

Usage: python3 scripts/check_static_site.py [--quiet]

ตรวจ 4 ด้าน:
  1. ไฟล์บังคับครบ (index.html, 404.html, _headers, _redirects)
  2. `_redirects` — relative URL เท่านั้น (absolute https:// ทำ Pages/Workers build ล้ม)
  3. `_headers`   — คอมเมนต์ต้องเริ่มด้วย '#' · rule ต้องเริ่มด้วย '/' · header ต้องย่อหน้าแบบ 'Key: Value'
                    rule '/' ต้องมี security headers ครบ และ CSP ต้องอนุญาตฟอนต์ที่ HTML ใช้จริง
  4. หน้า HTML    — anchor (#...) ต้องมี id รองรับ · ไฟล์ภายในต้องมีจริง · ห้ามหลงเหลือ localhost/ไดรฟ์

Exit: 0 = ผ่านทุกข้อ, 1 = พบปัญหา (แสดงทุกรายการ)
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

# ให้ log ไทย/emoji ทำงานได้ทั้งบน CI (UTF-8) และคอนโซล Windows ที่ codepage เก่า (เช่น cp874)
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
REQUIRED_FILES = ("index.html", "404.html", "_headers", "_redirects")
REQUIRED_HEADERS = (
    "X-Frame-Options",
    "X-Content-Type-Options",
    "Referrer-Policy",
    "Content-Security-Policy",
)
SCHEME_RE = re.compile(r"^[a-zA-Z][a-zA-Z0-9+.-]*://")
EXTERNAL_PREFIXES = ("#", "//", "mailto:", "tel:", "data:", "javascript:")
ATTR_RE = re.compile(r"""(?:href|src)\s*=\s*["']([^"']*)["']""")
ID_RE = re.compile(r"""\bid\s*=\s*["']([^"']+)["']""")

problems: list[str] = []


def fail(message: str) -> None:
    problems.append(message)


def read_html_texts() -> list[str]:
    return [p.read_text(encoding="utf-8") for p in sorted(ROOT.glob("*.html"))]


def check_required_files() -> None:
    for name in REQUIRED_FILES:
        if not (ROOT / name).is_file():
            fail(f"ขาดไฟล์บังคับ: {name}")


def check_redirects() -> None:
    path = ROOT / "_redirects"
    if not path.is_file():
        return
    for lineno, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if SCHEME_RE.match(line):
            fail(f"_redirects:{lineno} ใช้ absolute URL ไม่ได้ (Pages build จะล้ม): {line}")
            continue
        fields = line.split()
        if len(fields) not in (2, 3):
            fail(f"_redirects:{lineno} ต้องมี 2-3 คอลัมน์ (from to [status]): {line}")
        elif len(fields) == 3 and not re.fullmatch(r"(200|30[1-8])", fields[2]):
            fail(f"_redirects:{lineno} status ไม่ถูกต้อง (200 หรือ 301-308): {fields[2]}")


def parse_headers() -> dict[str, dict[str, str]]:
    """อ่าน _headers เป็น {rule: {header: value}} พร้อมตรวจรูปแบบบรรทัด"""
    rules: dict[str, dict[str, str]] = {}
    path = ROOT / "_headers"
    if not path.is_file():
        return rules
    current: str | None = None
    for lineno, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        line = raw.rstrip()
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if line[:1] == "/" and not any(ch.isspace() for ch in line):
            current = line.strip()
            rules.setdefault(current, {})
            continue
        if line[:1].isspace():
            if current is None:
                fail(f"_headers:{lineno} พบ header อยู่นอก rule")
                continue
            if ":" not in line:
                fail(f"_headers:{lineno} header ต้องเป็นรูปแบบ 'Key: Value': {line.strip()}")
                continue
            key, _, value = line.strip().partition(":")
            rules[current][key.strip()] = value.strip()
            continue
        fail(
            f"_headers:{lineno} บรรทัดไม่ถูกต้อง — คอมเมนต์ต้องเริ่มด้วย '#' และ rule ต้องเริ่มด้วย '/' "
            f"(Cloudflare จะอ่านบรรทัดนี้เป็น path pattern): {line.strip()}"
        )
    return rules


def check_headers(rules: dict[str, dict[str, str]]) -> None:
    root_rule = rules.get("/")
    if root_rule is None:
        fail("_headers ต้องมี rule '/' (ใช้กับทุก path)")
        return
    for name in REQUIRED_HEADERS:
        if name not in root_rule:
            fail(f"_headers: rule '/' ขาด security header '{name}'")
    csp = root_rule.get("Content-Security-Policy", "")
    html = "\n".join(read_html_texts())
    if "fonts.googleapis.com" in html and "https://fonts.googleapis.com" not in csp:
        fail("CSP ไม่ได้อนุญาต https://fonts.googleapis.com แต่หน้าเว็บเรียกฟอนต์นี้")
    if "fonts.gstatic.com" in html and "https://fonts.gstatic.com" not in csp:
        fail("CSP ไม่ได้อนุญาต https://fonts.gstatic.com แต่หน้าเว็บเรียกฟอนต์นี้")


def check_html() -> None:
    for path in sorted(ROOT.glob("*.html")):
        name = path.name
        text = path.read_text(encoding="utf-8")
        lowered = text.lower()
        if "<html" not in lowered or "</html>" not in lowered:
            fail(f"{name} ไม่ใช่ HTML ที่สมบูรณ์ (ขาด <html> หรือ </html>)")
        for token in ("http://localhost", "127.0.0.1", "file:///", "D:\\", "d:\\"):
            if token in text:
                fail(f"{name} มีค่าที่ไม่ควรอยู่ใน production: {token}")
        ids = set(ID_RE.findall(text))
        for ref in ATTR_RE.findall(text):
            if not ref or ref.startswith(EXTERNAL_PREFIXES) or SCHEME_RE.match(ref):
                continue
            if ref.startswith("#"):
                target = ref[1:]
                if target and target not in ids:
                    fail(f"{name} anchor '{ref}' ไม่มี id รองรับ")
                continue
            if ref.startswith("/"):
                continue
            local = (ROOT / ref.split("#", 1)[0].split("?", 1)[0]).resolve()
            if not local.is_file():
                fail(f"{name} อ้างไฟล์ภายในที่ไม่มีอยู่: {ref}")


def main() -> int:
    quiet = "--quiet" in sys.argv[1:]
    check_required_files()
    check_redirects()
    check_headers(parse_headers())
    check_html()

    if problems:
        print("❌ ตรวจ static site ไม่ผ่าน:", file=sys.stderr)
        for item in problems:
            print(f"   - {item}", file=sys.stderr)
        return 1
    if not quiet:
        print(f"🔍 ตรวจ {', '.join(REQUIRED_FILES)} + หน้า HTML ใน {ROOT}")
    print("✅ ผ่านทุกข้อ — redirects relative-only · headers format ถูกต้อง · anchor/ลิงก์ภายในครบ")
    return 0


if __name__ == "__main__":
    sys.exit(main())
