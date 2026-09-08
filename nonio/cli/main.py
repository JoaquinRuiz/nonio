"""Punto de entrada de la CLI.

La CLI **no contiene lógica**: cada comando llama a su equivalente importable de
`nonio` y se limita a formatear y a elegir el código de salida (Artículo VI).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import nonio
from nonio.cli.exit_codes import ExitCode
from nonio.cli.render import render

__all__ = ["app", "main"]


def _cmd_analyze(args) -> int:
    source: str | Path = sys.stdin.read() if args.path in (None, "-") else Path(args.path)
    result = nonio.analyze(
        source, profile=args.profile, language=args.language, min_words=args.min_words
    )
    if args.html:
        texto = source if isinstance(source, str) else source.read_text(encoding="utf-8")
        salida = nonio.render_html(result, text=texto)
        if args.output:
            Path(args.output).write_text(salida, encoding="utf-8")
            print(f"informe escrito en {args.output}", file=sys.stderr)
        else:
            print(salida)
    elif args.json:
        print(result.model_dump_json(indent=2))
    else:
        print(render(result))
    return ExitCode.OK if result.result.type == "reading" else ExitCode.INSUFFICIENT_EVIDENCE


def _cmd_profiles(args) -> int:
    if args.use:
        nonio.set_default_profile(args.use)
        print(f"Perfil por defecto: {args.use}", file=sys.stderr)
        return ExitCode.OK
    data = [
        {
            "id": p.id,
            "observer": p.observer_model,
            "performer": p.performer_model,
            "validated_languages": list(p.validated_languages),
            "measured_runtime": p.measured_runtime,
            "note": p.note,
        }
        for p in nonio.profiles()
    ]
    print(json.dumps(data, indent=2, ensure_ascii=False) if args.json else _fmt_profiles(data))
    return ExitCode.OK


def _fmt_profiles(data) -> str:
    out = []
    for p in data:
        idiomas = ", ".join(p["validated_languages"]) or "ninguno validado todavía"
        out.append(f"{p['id']}\n  observer: {p['observer']}\n  performer: {p['performer']}")
        rt = p["measured_runtime"]
        tiempo = (
            f"{rt['median_s']:.1f}s mediana / {rt['p95_s']:.1f}s p95 " f"por {rt['words']} palabras"
            if rt
            else "sin medir"
        )
        out.append(f"  idiomas calibrados: {idiomas}\n  tiempo medido: {tiempo}\n  {p['note']}")
    return "\n".join(out)


def _cmd_check(args) -> int:
    estado = nonio.check_resources(args.profile)
    if args.json:
        print(json.dumps(estado, indent=2, ensure_ascii=False))
    else:
        print(
            f"perfil {estado['profile']}: "
            f"{'disponible' if estado['available'] else 'faltan recursos'}"
        )
        for papel, info in estado["models"].items():
            marca = "✓" if info["present"] else "✗"
            extra = "" if info["present"] else f"   -> {info['hint']}"
            print(f"  {marca} {papel:<10} {info['repo']}{extra}")
    return ExitCode.OK if estado["available"] else ExitCode.RESOURCE_UNAVAILABLE


def _cmd_download(args) -> int:
    nonio.download_profile(args.profile_id)
    print("Listo.", file=sys.stderr)
    return ExitCode.OK


def _cmd_schema(args) -> int:
    if args.version:
        print(nonio.SCHEMA_VERSION)
    else:
        print(json.dumps(nonio.output_schema(), indent=2, ensure_ascii=False))
    return ExitCode.OK


def _cmd_eval(args) -> int:
    report = nonio.evaluate(corpus=args.corpus, profile=args.profile)
    print(
        json.dumps(report.to_dict(), indent=2, ensure_ascii=False)
        if args.json
        else report.to_text()
    )
    return ExitCode.OK


def app() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        prog="nonio",
        description="Mide señales estadísticas asociadas a la generación automática de texto. "
        "No decide autoría.",
    )
    sub = ap.add_subparsers(dest="command", required=True)

    a = sub.add_parser("analyze", help="Analiza un fichero o la entrada estándar")
    a.add_argument("path", nargs="?", default="-")
    a.add_argument("--json", action="store_true")
    a.add_argument("--html", action="store_true", help="Informe HTML autocontenido")
    a.add_argument("-o", "--output", metavar="FICHERO", help="Escribe la salida a un fichero")
    a.add_argument("--profile")
    a.add_argument("--language", help="Fuerza el idioma; no autoriza a extrapolar umbrales")
    a.add_argument("--min-words", type=int)
    a.set_defaults(func=_cmd_analyze)

    p = sub.add_parser("profiles", help="Lista o elige el perfil de medición")
    p.add_argument("--json", action="store_true")
    p.add_argument("--use", metavar="ID")
    p.set_defaults(func=_cmd_profiles)

    c = sub.add_parser("check", help="Comprueba los recursos locales; no usa red")
    c.add_argument("--json", action="store_true")
    c.add_argument("--profile")
    c.set_defaults(func=_cmd_check)

    d = sub.add_parser("download", help="Descarga recursos. Único comando con red")
    d.add_argument("profile_id")
    d.set_defaults(func=_cmd_download)

    s = sub.add_parser("schema", help="Emite el JSON Schema de la salida")
    s.add_argument("--version", action="store_true")
    s.set_defaults(func=_cmd_schema)

    e = sub.add_parser("eval", help="Evalúa sobre el corpus; siempre por categoría")
    e.add_argument("--corpus", choices=["public", "private", "all"], default="public")
    e.add_argument("--profile")
    e.add_argument("--json", action="store_true")
    e.set_defaults(func=_cmd_eval)

    return ap


def main(argv: list[str] | None = None) -> int:
    args = app().parse_args(argv)
    try:
        return int(args.func(args))
    except nonio.ResourceUnavailableError as exc:
        print(f"error de recursos: {exc}", file=sys.stderr)
        return ExitCode.RESOURCE_UNAVAILABLE
    except (nonio.UnreadableInputError, nonio.ProfileMismatchError, KeyError) as exc:
        print(f"error de uso: {exc}", file=sys.stderr)
        return ExitCode.USAGE


if __name__ == "__main__":
    raise SystemExit(main())
