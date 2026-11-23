import argparse
import csv
from dataclasses import dataclass
from datetime import datetime
import os
from pathlib import Path
import subprocess
import sys


CARPETA = Path(__file__).resolve().parent
LOCUSTFILE = CARPETA / "locustfile.py"


@dataclass(frozen=True)
class Perfil:
    usuarios: int
    llegada: int
    duracion_s: int


PERFILES = {
    "CE-01": (Perfil(20, 5, 60),),
    "CE-02": (Perfil(200, 25, 90),),
    "CE-03": (
        Perfil(50, 25, 60),
        Perfil(100, 25, 60),
        Perfil(200, 25, 60),
        Perfil(300, 25, 60),
    ),
    "CE-04": (Perfil(20, 5, 60),),
    "CE-05": (Perfil(60, 60, 30),),
    "CE-06": (
        Perfil(50, 25, 60),
        Perfil(100, 25, 60),
        Perfil(200, 25, 60),
        Perfil(300, 25, 60),
    ),
    "CE-07": (Perfil(20, 5, 60),),
    "CE-08": (Perfil(20, 5, 60),),
    "CE-09": (Perfil(20, 5, 60),),
    "CE-10": (Perfil(40, 20, 40),),
    "CE-11": (
        Perfil(50, 25, 60),
        Perfil(100, 25, 60),
        Perfil(200, 25, 60),
        Perfil(300, 25, 60),
    ),
}


def leer_agregado(ruta):
    if not ruta.is_file():
        return {}

    with ruta.open(encoding="utf-8-sig", newline="") as archivo:
        return next(
            (fila for fila in csv.DictReader(archivo)
             if fila.get("Name") == "Aggregated"),
            {},
        )


def leer_pico_usuarios(ruta):
    if not ruta.is_file():
        return "-"

    with ruta.open(encoding="utf-8-sig", newline="") as archivo:
        return max(
            (int(fila["User Count"]) for fila in csv.DictReader(archivo)
             if fila.get("Name") == "Aggregated" and fila.get("User Count")),
            default="-",
        )


def ejecutar(prueba_id, perfil, host, carpeta, total_ordenes):
    clase = prueba_id.replace("-", "")
    nombre = f"{prueba_id}-u{perfil.usuarios}"
    prefijo = carpeta / nombre
    ruta_log = carpeta / f"{nombre}.log"

    comando = [
        sys.executable, "-m", "locust",
        "-f", str(LOCUSTFILE), clase,
        "--headless", "--host", host,
        "-u", str(perfil.usuarios),
        "-r", str(perfil.llegada),
        "-t", f"{perfil.duracion_s}s",
        "--stop-timeout", "35",
        "--only-summary",
        "--csv", str(prefijo),
        "--csv-full-history",
        "--html", str(prefijo.with_suffix(".html")),
    ]

    entorno = os.environ.copy()
    if prueba_id == "CE-10":
        entorno["LOCUST_TOTAL_ORDENES"] = str(total_ordenes)

    print(
        f"{nombre}: {perfil.llegada} usuarios/s, "
        f"{perfil.duracion_s}s. Log: {ruta_log}",
        flush=True,
    )
    with ruta_log.open("w", encoding="utf-8") as log:
        proceso = subprocess.run(
            comando,
            env=entorno,
            stdout=log,
            stderr=subprocess.STDOUT,
            check=False,
        )

    agregado = leer_agregado(carpeta / f"{nombre}_stats.csv")
    pico = leer_pico_usuarios(carpeta / f"{nombre}_stats_history.csv")
    peticiones = int(agregado.get("Request Count") or 0)
    fallos = int(agregado.get("Failure Count") or 0)
    porcentaje = f"{fallos / peticiones:.2%}" if peticiones else "-"
    p95 = agregado.get("95%", "-") if peticiones else "-"
    rps = agregado.get("Requests/s", "-") if peticiones else "-"

    fila = (
        f"| {prueba_id} | {perfil.usuarios} | {pico} | {perfil.llegada} | "
        f"{perfil.duracion_s} | {peticiones} | {fallos} | {porcentaje} | "
        f"{p95} | {rps} | {proceso.returncode} |"
    )
    print(f"  Peticiones: {peticiones}, fallos: {fallos}, salida: {proceso.returncode}")

    return fila, proceso.returncode != 0 or peticiones == 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", required=True, help="URL del API Gateway")
    parser.add_argument("--ids", nargs="+", choices=PERFILES, default=list(PERFILES))
    parser.add_argument(
        "--ordenes-ce10",
        type=int,
        default=1800,
        help="Órdenes ENVIADAS que Locust prepara antes de medir CE-10",
    )
    args = parser.parse_args()
    if args.ordenes_ce10 < 1:
        parser.error("--ordenes-ce10 debe ser mayor que cero")

    fecha = datetime.now().astimezone()
    carpeta = CARPETA / "resultados" / fecha.strftime("%Y%m%d-%H%M%S-%f")
    carpeta.mkdir(parents=True)

    resumen = [
        "# Resultados de rendimiento de Cristian",
        "",
        f"- Fecha: {fecha.isoformat(timespec='seconds')}",
        f"- Gateway: `{args.host}`",
        "- Duración: incluye el periodo de subida de usuarios.",
        "",
        "| ID | Usuarios objetivo | Pico observado | Llegada (usuarios/s) | "
        "Duración (s) | Peticiones | Fallos | Fallos % | P95 (ms) | Req/s | "
        "Salida Locust |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]

    hubo_fallos = False
    for prueba_id in dict.fromkeys(args.ids):
        for perfil in PERFILES[prueba_id]:
            fila, fallo = ejecutar(
                prueba_id, perfil, args.host, carpeta, args.ordenes_ce10
            )
            resumen.append(fila)
            hubo_fallos |= fallo

    ruta_resumen = carpeta / "RESUMEN.md"
    ruta_resumen.write_text("\n".join(resumen) + "\n", encoding="utf-8")
    print(f"\nResumen: {ruta_resumen}")
    return int(hubo_fallos)


if __name__ == "__main__":
    sys.exit(main())