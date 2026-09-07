"""Texto humano anterior a 2022 desde Wikipedia en español (FR-020, R-006).

Se piden **revisiones anteriores al 1 de enero de 2022**, no la versión actual:
el Artículo VII exige una categoría de texto humano previo a 2022 y una página
viva puede haber sido editada después con ayuda de un modelo. La fecha de corte
la fija la spec, no una estimación.

Wikipedia aporta además el registro que a la parte pública del corpus le falta:
prosa contemporánea y expositiva, frente a la literatura de dominio público que
es casi toda anterior a 1930 (Supuestos de la spec).

Dos categorías salen de aquí, y se separan a propósito:

- `humano_pre2022`: biografías, historia, geografía — prosa narrativa.
- `tecnica_estructurada`: matemáticas, física, informática — el registro que el
  Artículo III señala como propenso a falsos positivos.

Licencia: CC BY-SA 4.0. Obliga a atribución y a compartir igual, por eso cada
caso guarda su URL y su `oldid` en la procedencia.
"""

from __future__ import annotations

import json
import re
import urllib.parse
import urllib.request
from dataclasses import dataclass

API = "https://es.wikipedia.org/w/api.php"
CUTOFF = "2021-12-31T23:59:59Z"
LICENSE = "CC-BY-SA-4.0"
UA = "nonio-corpus/0.1 (https://github.com/JoaquinRuiz/nonio)"

__all__ = ["fetch_category_members", "fetch_pre2022_text", "WikiText"]


@dataclass(frozen=True)
class WikiText:
    title: str
    oldid: int
    timestamp: str
    text: str

    @property
    def provenance(self) -> str:
        return (
            f"Wikipedia es «{self.title}», revisión {self.oldid} de {self.timestamp} — "
            f"https://es.wikipedia.org/w/index.php?oldid={self.oldid}"
        )


def _api(params: dict[str, str]) -> dict:
    params = {**params, "format": "json", "formatversion": "2"}
    url = f"{API}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=45) as fh:
        return json.loads(fh.read().decode("utf-8"))


def fetch_category_members(category: str, limit: int = 60) -> list[str]:
    data = _api(
        {
            "action": "query",
            "list": "categorymembers",
            "cmtitle": f"Categoría:{category}",
            "cmnamespace": "0",
            "cmlimit": str(limit),
        }
    )
    return [m["title"] for m in data.get("query", {}).get("categorymembers", [])]


_TAG = re.compile(r"<[^>]+>")
_REF = re.compile(r"\[\d+\]")
_WS = re.compile(r"[ \t]+")


def _clean(html: str) -> str:
    html = re.sub(r"(?is)<(table|style|script|sup|figure)\b.*?</\1>", " ", html)
    paragraphs = re.findall(r"(?is)<p\b[^>]*>(.*?)</p>", html)
    out = []
    for p in paragraphs:
        t = _REF.sub("", _TAG.sub("", p))
        t = (
            t.replace("&nbsp;", " ")
            .replace("&amp;", "&")
            .replace("&quot;", '"')
            .replace("&#39;", "'")
            .replace("&lt;", "<")
            .replace("&gt;", ">")
        )
        t = _WS.sub(" ", t).strip()
        if len(t.split()) >= 15:
            out.append(t)
    return "\n\n".join(out)


def fetch_pre2022_text(title: str) -> WikiText | None:
    """Devuelve el texto plano de la última revisión anterior a 2022."""
    meta = _api(
        {
            "action": "query",
            "prop": "revisions",
            "titles": title,
            "rvprop": "ids|timestamp",
            "rvstart": CUTOFF,
            "rvdir": "older",
            "rvlimit": "1",
        }
    )
    pages = meta.get("query", {}).get("pages", [])
    if not pages or "revisions" not in pages[0]:
        return None
    rev = pages[0]["revisions"][0]

    parsed = _api({"action": "parse", "oldid": str(rev["revid"]), "prop": "text"})
    html = parsed.get("parse", {}).get("text", "")
    text = _clean(html)
    if not text:
        return None
    return WikiText(title=title, oldid=rev["revid"], timestamp=rev["timestamp"], text=text)
