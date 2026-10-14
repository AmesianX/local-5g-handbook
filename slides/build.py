#!/usr/bin/env python3
"""slides/parts/*.html 을 이름순으로 이어 붙여 slides/index.html 을 만든다.
사용: python3 slides/build.py
"""
import pathlib

here = pathlib.Path(__file__).resolve().parent
parts = sorted((here / "parts").glob("*.html"))
body = "\n".join(p.read_text(encoding="utf-8") for p in parts)
tpl = (here / "template.html").read_text(encoding="utf-8")
out = here / "index.html"
out.write_text(tpl.replace("<!--PARTS-->", body), encoding="utf-8")
print(f"{out}  ({len(parts)} parts, {out.stat().st_size // 1024} KB)")
