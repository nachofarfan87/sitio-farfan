#!/usr/bin/env python3
"""Lee el valor del UMA del sitio del Colegio de Abogados de Jujuy y actualiza
honorarios/uma.json si cambió. Corre en GitHub Actions: desde un servidor no hay
CORS, así que la lectura es directa y no depende de proxies de terceros.

Vive dentro de .github/ a propósito: Netlify publica la raíz del repo tal cual,
y las carpetas que empiezan con punto no se sirven. Así el script queda fuera
del sitio sin necesidad de reglas de redirección."""
import json
import re
import sys
import datetime
import pathlib
import urllib.request

SITE = "https://colabogadosjujuy.com.ar/"
UMA_JSON = pathlib.Path(__file__).resolve().parents[2] / "honorarios" / "uma.json"


def fetch(url):
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (compatible; EstudioFarfan/1.0; +https://estudiofarfan.netlify.app/honorarios/)",
        "Accept": "text/html",
    })
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8", "ignore")


def parse_arg_number(s):
    s = re.sub(r"[^\d.,]", "", s)
    if not s:
        return None
    if "." in s and "," in s:        # 51.186,00 -> 51186.00
        s = s.replace(".", "").replace(",", ".")
    elif "," in s:                   # coma decimal
        s = s.replace(",", ".")
    elif "." in s:                   # puntos = miles
        s = s.replace(".", "")
    try:
        return round(float(s))
    except ValueError:
        return None


def extract(html):
    text = re.sub(r"<[^>]+>", " ", html)   # quitar etiquetas -> texto plano
    m = re.search(r"UMA\s+([A-Za-zÁÉÍÓÚáéíóúÜüÑñ]+)?\s*\$\s*([\d.,]+)", text, re.I)
    if m:
        valor = parse_arg_number(m.group(2))
        if valor and valor > 1000:
            return (m.group(1) or "").strip(), valor
    return None


def main():
    try:
        html = fetch(SITE)
    except Exception as e:
        print(f"::warning::No se pudo leer el sitio del Colegio: {e}")
        return 0  # no fallamos el workflow; se conserva el último valor

    found = extract(html)
    if not found:
        print("::warning::No se encontró el valor del UMA en el sitio (sin cambios).")
        return 0

    mes, valor = found
    hoy = datetime.date.today().isoformat()

    actual = {}
    if UMA_JSON.exists():
        try:
            actual = json.loads(UMA_JSON.read_text(encoding="utf-8"))
        except Exception:
            pass

    igual = (actual.get("valor") == valor
             and str(actual.get("mes", "")).lower() == mes.lower())

    # Aunque el valor no cambie, refrescamos la fecha: la página avisa
    # "valor a confirmar" cuando uma.json lleva más de 45 días sin verificarse.
    nuevo = {"mes": mes, "valor": valor, "actualizado": hoy}
    if igual and actual.get("actualizado") == hoy:
        print(f"Sin cambios: {mes} ${valor}")
        return 0

    UMA_JSON.write_text(json.dumps(nuevo, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(("Verificado" if igual else "Actualizado") + f": {mes} ${valor}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
