"""Informe HTML del análisis (FR-013, FR-024, Artículos IV, V y IX).

Tres decisiones de diseño que no son estéticas:

1. **Autocontenido, sin recursos externos.** Ni fuentes de Google, ni CDN, ni
   imágenes remotas. Un informe que cargara algo de fuera delataría, a quien
   sirviera ese recurso, que alguien está analizando un texto — y el Artículo V
   existe para que el texto y el hecho de analizarlo no salgan de la máquina.

2. **No parece un certificado.** El Artículo IX prohíbe exportaciones diseñadas
   para adjuntarse a un expediente, y un documento con aspecto oficial es
   exactamente lo que se imprime y se adjunta. Por eso el aviso va arriba, en el
   flujo del documento y no en un pie, la tasa de error acompaña a cada cifra, y
   no hay sellos, firmas, logotipos ni marcas de agua.

3. **La abstención se ve tan grande como una lectura.** Si el informe la
   presentara como un caso degradado, el Artículo II quedaría desmentido por la
   tipografía.
"""

from __future__ import annotations

import html
from datetime import UTC, datetime

from nonio.config_author import AuthorLinks, load_author_links
from nonio.schema.models import Abstention, AnalysisResult, Reading

__all__ = ["render_html"]

_CSS = """
:root{--bg:#fbfaf8;--fg:#1c1a17;--mut:#6b6560;--line:#e2ddd6;--card:#fff;
--warn-bg:#fff4e6;--warn-line:#e8a33d;--warn-fg:#6b4506;
--bajo:#3f7d58;--moderado:#b8860b;--alto:#a94442;--abst:#5a6b7a;--accent:#2f5d7c}
@media(prefers-color-scheme:dark){:root{--bg:#16181a;--fg:#e8e6e3;--mut:#9a948e;
--line:#2e3236;--card:#1d2023;--warn-bg:#2e2413;--warn-line:#a3762a;--warn-fg:#f0d9a8;
--bajo:#6fbf8f;--moderado:#d9b04a;--alto:#e08b86;--abst:#8fa3b5;--accent:#79b0d6}}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);
font:15px/1.6 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif}
.wrap{max-width:820px;margin:0 auto;padding:32px 20px 64px}
h1{font-size:26px;margin:0 0 4px;letter-spacing:-.01em}
.sub{color:var(--mut);margin:0 0 24px;font-size:14px}
.warn{background:var(--warn-bg);border:1px solid var(--warn-line);border-left-width:4px;
border-radius:6px;padding:14px 16px;margin:0 0 28px;color:var(--warn-fg);font-size:14px}
.warn strong{display:block;margin-bottom:4px}
.card{background:var(--card);border:1px solid var(--line);border-radius:8px;
padding:20px;margin:0 0 18px}
.verdict{display:flex;align-items:baseline;gap:12px;flex-wrap:wrap;margin-bottom:4px}
.level{font-size:30px;font-weight:600;letter-spacing:-.02em}
.level.bajo{color:var(--bajo)}.level.moderado{color:var(--moderado)}
.level.alto{color:var(--alto)}.level.abst{color:var(--abst);font-size:22px}
.tag{font-size:12px;color:var(--mut);border:1px solid var(--line);
border-radius:99px;padding:2px 9px}
.margin{margin-top:14px;padding-top:14px;border-top:1px solid var(--line);font-size:14px}
.margin b{font-variant-numeric:tabular-nums}
table{width:100%;border-collapse:collapse;font-size:14px;margin-top:6px}
th{text-align:left;font-weight:600;color:var(--mut);font-size:12px;
text-transform:uppercase;letter-spacing:.04em;padding:6px 8px 6px 0}
td{padding:6px 8px 6px 0;border-top:1px solid var(--line);font-variant-numeric:tabular-nums}
h2{font-size:13px;text-transform:uppercase;letter-spacing:.06em;color:var(--mut);
margin:26px 0 8px}
.bar{height:6px;border-radius:3px;background:var(--line);overflow:hidden;min-width:80px}
.bar>i{display:block;height:100%;background:var(--accent)}
.blk{display:grid;grid-template-columns:34px 1fr 92px;gap:10px;align-items:center;
padding:7px 0;border-top:1px solid var(--line);font-size:13px}
.blk .n{color:var(--mut);font-variant-numeric:tabular-nums}
.blk .s{text-align:right;font-weight:600}
.excerpt{color:var(--mut);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.foot{margin-top:40px;padding-top:18px;border-top:1px solid var(--line);
color:var(--mut);font-size:13px}
.promo{margin-top:34px;padding:18px 20px;border:1px dashed var(--line);
border-radius:8px;background:transparent}
.promo h3{margin:0 0 3px;font-size:14px;color:var(--fg)}
.promo p{margin:0 0 12px;color:var(--mut);font-size:13px}
.promo ul{margin:0;padding:0;list-style:none;display:flex;flex-wrap:wrap;gap:8px}
.promo a{display:inline-block;padding:6px 12px;border:1px solid var(--line);
border-radius:6px;color:var(--accent);text-decoration:none;font-size:13px;background:var(--card)}
.promo a:hover{border-color:var(--accent)}
.promo .aside{margin-top:10px;font-size:11px;color:var(--mut)}
"""


def _e(t: object) -> str:
    return html.escape(str(t), quote=True)


def _signals_table(signals) -> str:
    filas = []
    for s in sorted(signals, key=lambda x: x.name):
        pct = s.normalized_value
        pct_txt = "n/d" if pct != pct else f"{pct:.3f}"
        ancho = 0 if pct != pct else max(0, min(100, pct * 100))
        filas.append(
            f"<tr><td>{_e(s.name)}</td><td>{s.raw_value:+.4f}</td><td>{pct_txt}</td>"
            f'<td><div class="bar"><i style="width:{ancho:.0f}%"></i></div></td></tr>'
        )
    return (
        "<table><tr><th>señal</th><th>valor</th><th>percentil</th><th></th></tr>"
        + "".join(filas)
        + "</table>"
    )


def _blocks(result: AnalysisResult, texto: str | None) -> str:
    if not result.blocks:
        return ""
    filas = []
    for b in result.blocks:
        if isinstance(b.result, Reading):
            estado = f'<span class="level {b.result.level.value}" '
            estado += f'style="font-size:13px">{b.result.level.value}</span>'
        else:
            estado = (
                '<span class="s" style="color:var(--abst);font-weight:500">sin evidencia</span>'
            )
        frag = ""
        if texto:
            trozo = " ".join(texto[b.start : b.end].split())[:110]
            frag = _e(trozo)
        filas.append(
            f'<div class="blk"><span class="n">{b.index}</span>'
            f'<span class="excerpt">{frag}</span><span class="s">{estado}</span></div>'
        )
    return f"<h2>Desglose por bloque ({len(result.blocks)})</h2>" + "".join(filas)


def _promo(links: AuthorLinks) -> str:
    if links.empty:
        return ""
    items = []
    if links.youtube_url:
        etiqueta = links.youtube_label or "Canal de YouTube"
        items.append(f'<li><a href="{_e(links.youtube_url)}">▶ {_e(etiqueta)}</a></li>')
    for libro in links.books:
        titulo = libro.get("title", "Libro")
        url = libro.get("url", "")
        items.append(f'<li><a href="{_e(url)}">📕 {_e(titulo)}</a></li>')
    if links.site_url:
        items.append(f'<li><a href="{_e(links.site_url)}">🔗 {_e(links.site_url)}</a></li>')

    nombre = _e(links.name) if links.name else "el autor"
    tagline = f"<p>{_e(links.tagline)}</p>" if links.tagline else ""
    return (
        '<section class="promo">'
        f"<h3>Más de {nombre}</h3>{tagline}"
        f'<ul>{"".join(items)}</ul>'
        '<p class="aside">Enlaces del autor de la herramienta. No forman parte de la '
        "medición ni influyen en ella.</p></section>"
    )


def render_html(
    result: AnalysisResult,
    *,
    text: str | None = None,
    author: AuthorLinks | None = None,
    title: str = "Informe de medición — Nonio",
) -> str:
    """Devuelve un documento HTML completo y autocontenido."""
    links = author if author is not None else load_author_links()
    d = result.document
    r = result.result

    if isinstance(r, Reading):
        cuerpo = (
            f'<div class="verdict"><span class="level {r.level.value}">'
            f"señal {_e(r.level.value)}</span>"
            f'<span class="tag">categoría de referencia: {_e(r.fpr_category.value)}</span></div>'
            f'<div class="margin">Umbral aplicado <b>{r.applied_threshold:.4f}</b> · '
            f"Falsos positivos medidos de ese umbral <b>{r.measured_fpr:.1%}</b> · "
            f"cifra {'reproducible' if r.fpr_reproducible else '<b>no reproducible</b>'} "
            "por terceros</div>"
        )
        senales = _signals_table(r.signals)
    else:
        assert isinstance(r, Abstention)
        cuerpo = (
            f'<div class="verdict"><span class="level abst">'
            f"insufficient_evidence</span>"
            f'<span class="tag">{_e(r.cause.value)}</span></div>'
            f'<div class="margin">{_e(r.detail)}<br><br>'
            "La abstención es un resultado completo, no un fallo: Nonio no arriesga "
            "una medida que no se sostiene.</div>"
        )
        senales = _signals_table(r.signals) if r.signals else ""

    return f"""<!doctype html>
<html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="noindex,nofollow">
<title>{_e(title)}</title><style>{_CSS}</style></head><body><div class="wrap">

<h1>Informe de medición</h1>
<p class="sub">Nonio {_e(result.nonio_version)} · esquema {_e(result.schema_version)} ·
perfil {_e(result.profile.id)} ·
{_e(datetime.now(UTC).astimezone().strftime("%Y-%m-%d %H:%M"))}</p>

<div class="warn"><strong>Esto no es un veredicto sobre quién escribió el texto.</strong>
Nonio mide señales estadísticas y las reporta con su margen de error. No afirma
autoría humana ni automática. <b>Esta salida no debe ser base única de ninguna
decisión académica, laboral o editorial.</b></div>

<div class="card">{cuerpo}</div>

<h2>Documento</h2>
<table>
<tr><td>Origen</td><td>{_e(d.source)}</td></tr>
<tr><td>Idioma detectado</td><td>{_e(d.detected_language or "no determinado")}</td></tr>
<tr><td>Palabras medibles</td><td>{d.measurable_word_count}</td></tr>
<tr><td>Excluido del cálculo</td><td>{d.excluded_ratio:.1%}
 ({len(d.excluded_spans)} tramos: código, tablas y citas)</td></tr>
</table>

{"<h2>Señales</h2>" + senales if senales else ""}
{_blocks(result, text)}

<p class="foot">El nivel describe la intensidad de una señal estadística, no quién
escribió el texto. Cada cifra va acompañada de la tasa de error medida de su umbral
sobre un corpus declarado; sin ese dato Nonio se abstiene. Generado en local: ni el
texto ni este informe han salido de tu máquina.</p>

{_promo(links)}
</div></body></html>"""
