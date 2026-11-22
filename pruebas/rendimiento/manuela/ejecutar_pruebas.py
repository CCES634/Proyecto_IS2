"""Ejecuta las pruebas de rendimiento MP-01 a MP-11 de Manuela y genera un resumen.

Uso:
    python ejecutar_pruebas.py --host http://localhost:8000            # todas
    python ejecutar_pruebas.py --host http://<ip>:30080 --ids MP-01,MP-07
    python ejecutar_pruebas.py --host ... --escala 0.5                  # usuarios x 0.5 (equipos pequeños)

Por cada prueba se guardan en resultados/: <ID>_stats.csv, <ID>_stats_history.csv
y <ID>.html (reporte gráfico de Locust). Al final se escribe resultados/RESUMEN.md.

Criterio de aceptación (RNF06, definido en la Entrega 2):
    p95 < 2000 ms y tasa de error < 1 % en carga normal.
En estrés y capacidad se busca el punto de quiebre: el primer número de usuarios
concurrentes con el que se incumple alguno de los dos criterios.
"""
import argparse
import csv
import datetime
import os
import subprocess
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
RESULTADOS = os.path.join(AQUI, "resultados")

# id: (clase de usuario, escenario, usuarios, usuarios nuevos por segundo, duración, objetivo)
PRUEBAS = {
    "MP-01": ("BusquedaProductos", "Carga normal", 20, 5, "60s", "Búsqueda y filtrado en menos de 2 s"),
    "MP-02": ("BusquedaProductos", "Carga pico", 200, 50, "60s", "Búsqueda con 200 usuarios"),
    "MP-03": ("Compatibilidad", "Carga normal", 20, 5, "60s", "Consulta de compatibilidad con motos"),
    "MP-04": ("Compatibilidad", "Estrés", 400, 5, "90s", "Punto de quiebre de compatibilidad"),
    "MP-05": ("RegistroProductos", "Carga normal", 10, 2, "60s", "Registro de productos con validación"),
    "MP-06": ("ConsultaLote", "Capacidad", 300, 4, "90s", "Máximo de usuarios en consulta por lote"),
    "MP-07": ("Login", "Carga normal", 10, 2, "60s", "Tiempo de inicio de sesión"),
    "MP-08": ("Login", "Carga pico", 100, 100, "60s", "Todos los empleados entran a la vez"),
    "MP-09": ("Login", "Estrés", 300, 4, "90s", "Punto de quiebre del login"),
    "MP-10": ("ReporteAlertas", "Carga normal", 20, 5, "60s", "Reporte que consulta Inventario y Catálogo"),
    "MP-11": ("Dashboard", "Estrés", 200, 3, "90s", "Efecto de la carga en los servicios consultados"),
}
RAMPA = {"Estrés", "Capacidad"}
P95_MAX_MS = 2000
ERROR_MAX = 0.01


def ejecutar(prueba_id, host, escala):
    clase, escenario, usuarios, tasa, duracion, _ = PRUEBAS[prueba_id]
    usuarios = max(1, int(usuarios * escala))
    tasa = max(1, int(tasa * escala)) if escenario not in RAMPA else tasa
    prefijo = os.path.join(RESULTADOS, prueba_id)
    comando = [
        sys.executable, "-m", "locust", "-f", os.path.join(AQUI, "locustfile.py"), clase,
        "--headless", "--host", host, "-u", str(usuarios), "-r", str(tasa), "-t", duracion,
        "--csv", prefijo, "--html", f"{prefijo}.html", "--only-summary", "--stop-timeout", "5",
    ]
    comando.append("--csv-full-history")
    for viejo in os.listdir(RESULTADOS):
        if viejo.startswith(prueba_id):
            os.remove(os.path.join(RESULTADOS, viejo))
    print(f"\n>>> {prueba_id} {clase} [{escenario}] usuarios={usuarios} tasa={tasa}/s duración={duracion}", flush=True)
    subprocess.run(comando, check=False)
    return usuarios


def usuarios_ejecutados(prueba_id):
    """Máximo de usuarios concurrentes que alcanzó la prueba (según el historial de Locust)."""
    ruta = os.path.join(RESULTADOS, f"{prueba_id}_stats_history.csv")
    maximo = 0
    if os.path.exists(ruta):
        with open(ruta, encoding="utf-8") as f:
            for fila in csv.DictReader(f):
                if fila["Name"] == "Aggregated":
                    maximo = max(maximo, int(fila["User Count"] or 0))
    return maximo or PRUEBAS[prueba_id][2]


def leer_agregado(prueba_id):
    with open(os.path.join(RESULTADOS, f"{prueba_id}_stats.csv"), encoding="utf-8") as f:
        for fila in csv.DictReader(f):
            if fila["Name"] == "Aggregated":
                return fila
    return None


def punto_de_quiebre(prueba_id):
    """Analiza la rampa: primer número de usuarios con p95 > 2 s o errores > 1 % (ventana
    móvil de Locust), máximo de usuarios atendidos dentro del criterio y throughput máximo."""
    ruta = os.path.join(RESULTADOS, f"{prueba_id}_stats_history.csv")
    if not os.path.exists(ruta):
        return None, None, None
    maximo_ok, quiebre, rps_max = 0, None, 0.0
    with open(ruta, encoding="utf-8") as f:
        for fila in csv.DictReader(f):
            if fila["Name"] != "Aggregated" or fila["95%"] in ("N/A", ""):
                continue
            usuarios = int(fila["User Count"])
            rps = float(fila["Requests/s"] or 0)
            fallos = float(fila["Failures/s"] or 0)
            p95 = float(fila["95%"])
            rps_max = max(rps_max, rps)
            if quiebre is None and rps > 0 and (p95 > P95_MAX_MS or fallos / rps > ERROR_MAX):
                quiebre = usuarios
            if quiebre is None:
                maximo_ok = max(maximo_ok, usuarios)
    return quiebre, maximo_ok, rps_max


def resumen(ejecutadas, host):
    lineas = [
        "# Resultados preliminares — Pruebas de rendimiento de Manuela (MP-01 a MP-11)",
        "",
        f"- Fecha: {datetime.datetime.now():%Y-%m-%d %H:%M}",
        f"- Host (API Gateway): `{host}`",
        "- Herramienta: Locust (`pruebas/rendimiento/manuela/locustfile.py`)",
        "- Criterio de aceptación (RNF06): p95 < 2000 ms y errores < 1 %",
        "",
        "| ID | Endpoint / clase | Escenario | Usuarios | Peticiones | Error % | Promedio (ms) | p50 (ms) "
        "| p95 (ms) | Máx (ms) | Throughput (req/s) | Resultado |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    detalles = []
    for prueba_id, usuarios in ejecutadas:
        clase, escenario, *_ , objetivo = PRUEBAS[prueba_id]
        fila = leer_agregado(prueba_id)
        if not fila or int(fila["Request Count"]) == 0:
            lineas.append(f"| {prueba_id} | {clase} | {escenario} | {usuarios} | 0 | - | - | - | - | - | - | SIN DATOS |")
            continue
        total = int(fila["Request Count"])
        error = int(fila["Failure Count"]) / total
        p95 = float(fila["95%"])
        if escenario in RAMPA:
            quiebre, maximo_ok, rps_max = punto_de_quiebre(prueba_id)
            if quiebre:
                veredicto = f"Quiebre ≈ {quiebre} usuarios"
            else:
                veredicto = f"Sin quiebre hasta {maximo_ok} usuarios"
            detalles.append(f"- **{prueba_id}** ({objetivo}): " + (
                f"se mantuvo dentro del criterio hasta ~{maximo_ok} usuarios concurrentes y lo incumplió con ~{quiebre}"
                if quiebre else f"cumplió el criterio durante toda la rampa (hasta {maximo_ok} usuarios)")
                + f"; throughput máximo observado: {rps_max:.0f} req/s.")
        else:
            cumple = p95 < P95_MAX_MS and error < ERROR_MAX
            veredicto = "CUMPLE" if cumple else "NO CUMPLE"
            detalles.append(f"- **{prueba_id}** ({objetivo}): p95 de {p95:.0f} ms con {error:.2%} de errores "
                            f"→ {veredicto.lower()} el criterio.")
        lineas.append(
            f"| {prueba_id} | {clase} | {escenario} | {usuarios} | {total} | {error:.2%} | "
            f"{float(fila['Average Response Time']):.0f} | {float(fila['Median Response Time']):.0f} | {p95:.0f} | "
            f"{float(fila['Max Response Time']):.0f} | {float(fila['Requests/s']):.1f} | {veredicto} |"
        )
    lineas += ["", "## Lectura de resultados", ""] + detalles
    ruta = os.path.join(RESULTADOS, "RESUMEN.md")
    with open(ruta, "w", encoding="utf-8") as f:
        f.write("\n".join(lineas) + "\n")
    print(f"\nResumen escrito en {ruta}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="http://localhost:8000")
    parser.add_argument("--ids", default=",".join(PRUEBAS))
    parser.add_argument("--escala", type=float, default=1.0, help="Multiplica el número de usuarios")
    args = parser.parse_args()
    os.makedirs(RESULTADOS, exist_ok=True)
    for i in args.ids.split(","):
        ejecutar(i, args.host, args.escala)
    # El resumen incluye todas las pruebas que tengan resultados (permite correrlas por lotes)
    con_resultados = [
        (i, usuarios_ejecutados(i)) for i in PRUEBAS
        if os.path.exists(os.path.join(RESULTADOS, f"{i}_stats.csv"))
    ]
    resumen(con_resultados, args.host)


if __name__ == "__main__":
    main()
