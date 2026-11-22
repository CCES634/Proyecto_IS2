# Resultados preliminares — Pruebas de rendimiento de Manuela (MP-01 a MP-11)

- Fecha: 2026-11-21 17:59
- Host (API Gateway): `http://localhost:8000`
- Herramienta: Locust (`pruebas/rendimiento/manuela/locustfile.py`)
- Criterio de aceptación (RNF06): p95 < 2000 ms y errores < 1 %

| ID | Endpoint / clase | Escenario | Usuarios | Peticiones | Error % | Promedio (ms) | p50 (ms) | p95 (ms) | Máx (ms) | Throughput (req/s) | Resultado |
|---|---|---|---|---|---|---|---|---|---|---|---|
| MP-01 | BusquedaProductos | Carga normal | 20 | 575 | 0.00% | 14 | 13 | 22 | 56 | 9.8 | CUMPLE |
| MP-02 | BusquedaProductos | Carga pico | 200 | 5794 | 0.00% | 25 | 17 | 69 | 279 | 98.0 | CUMPLE |
| MP-03 | Compatibilidad | Carga normal | 20 | 589 | 0.00% | 17 | 16 | 23 | 59 | 10.0 | CUMPLE |
| MP-04 | Compatibilidad | Estrés | 400 | 9317 | 0.00% | 198 | 82 | 740 | 1024 | 103.4 | Sin quiebre hasta 400 usuarios |
| MP-05 | RegistroProductos | Carga normal | 10 | 288 | 0.00% | 15 | 15 | 21 | 38 | 4.9 | CUMPLE |
| MP-06 | ConsultaLote | Capacidad | 300 | 7920 | 0.00% | 14 | 11 | 31 | 83 | 88.9 | Sin quiebre hasta 300 usuarios |
| MP-07 | Login | Carga normal | 10 | 287 | 0.00% | 113 | 110 | 160 | 282 | 4.8 | CUMPLE |
| MP-08 | Login | Carga pico | 100 | 1221 | 0.00% | 3010 | 3700 | 4700 | 6533 | 19.7 | NO CUMPLE |
| MP-09 | Login | Estrés | 300 | 1894 | 0.00% | 6103 | 5700 | 15000 | 16714 | 20.1 | Quiebre ≈ 88 usuarios |
| MP-10 | ReporteAlertas | Carga normal | 20 | 526 | 0.00% | 45 | 19 | 66 | 3146 | 8.9 | CUMPLE |
| MP-11 | Dashboard | Estrés | 200 | 2110 | 0.00% | 3594 | 3000 | 8600 | 9306 | 22.4 | Quiebre ≈ 99 usuarios |

## Lectura de resultados

- **MP-01** (Búsqueda y filtrado en menos de 2 s): p95 de 22 ms con 0.00% de errores → cumple el criterio.
- **MP-02** (Búsqueda con 200 usuarios): p95 de 69 ms con 0.00% de errores → cumple el criterio.
- **MP-03** (Consulta de compatibilidad con motos): p95 de 23 ms con 0.00% de errores → cumple el criterio.
- **MP-04** (Punto de quiebre de compatibilidad): cumplió el criterio durante toda la rampa (hasta 400 usuarios); throughput máximo observado: 171 req/s.
- **MP-05** (Registro de productos con validación): p95 de 21 ms con 0.00% de errores → cumple el criterio.
- **MP-06** (Máximo de usuarios en consulta por lote): cumplió el criterio durante toda la rampa (hasta 300 usuarios); throughput máximo observado: 149 req/s.
- **MP-07** (Tiempo de inicio de sesión): p95 de 160 ms con 0.00% de errores → cumple el criterio.
- **MP-08** (Todos los empleados entran a la vez): p95 de 4700 ms con 0.00% de errores → no cumple el criterio.
- **MP-09** (Punto de quiebre del login): se mantuvo dentro del criterio hasta ~84 usuarios concurrentes y lo incumplió con ~88; throughput máximo observado: 23 req/s.
- **MP-10** (Reporte que consulta Inventario y Catálogo): p95 de 66 ms con 0.00% de errores → cumple el criterio.
- **MP-11** (Efecto de la carga en los servicios consultados): se mantuvo dentro del criterio hasta ~96 usuarios concurrentes y lo incumplió con ~99; throughput máximo observado: 26 req/s.
