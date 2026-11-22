# Análisis preliminar — Pruebas de rendimiento de Manuela (Entrega 3)

**Servicios cubiertos:** Catálogo, Usuarios y Autenticación, Reportes y Alertas.
**Herramienta:** Locust 2.x. Todas las peticiones pasan por el **API Gateway**.
**Métricas:** tiempo de respuesta (promedio, p50, p95, máximo), throughput (req/s) y tasa de error.
**Criterio de aceptación (RNF06):** p95 < 2 s y menos de 1 % de errores en carga normal.

Los resultados completos están en [`resultados/RESUMEN.md`](resultados/RESUMEN.md) y cada prueba tiene su reporte
gráfico de Locust (`resultados/MP-XX.html`) y sus CSV (`_stats.csv` y `_stats_history.csv`).

## Entorno de esta corrida (importante para interpretar los números)

- Ejecución **preliminar en entorno local**: los 6 componentes (Gateway + 5 servicios con Gunicorn, 2 workers
  cada uno) + MySQL + Locust en **la misma máquina de 2 vCPU y 7 GB de RAM**. Locust compite por CPU con el sistema,
  así que los números son pesimistas.
- Para la Entrega 4 se repetirán sobre el despliegue en **Kubernetes** (con réplicas y HPA) para comparar.
- Tiempo de espera entre peticiones de cada usuario virtual: 1 a 3 s (`wait_time = between(1, 3)`).
- El token se obtiene una sola vez al iniciar cada prueba (excepto en MP-07/08/09, que miden el login).

## Resumen

| ID | Endpoint | Escenario | Usuarios | p95 | Errores | Resultado |
|---|---|---|---|---|---|---|
| MP-01 | GET /api/catalogo/productos | Carga normal | 20 | 22 ms | 0 % | Cumple |
| MP-02 | GET /api/catalogo/productos | Carga pico | 200 | 69 ms | 0 % | Cumple |
| MP-03 | GET /api/catalogo/productos/compatibles | Carga normal | 20 | 23 ms | 0 % | Cumple |
| MP-04 | GET /api/catalogo/productos/compatibles | Estrés (rampa a 400) | 400 | 740 ms | 0 % | Sin quiebre hasta 400 usuarios; satura en ~170 req/s |
| MP-05 | POST /api/catalogo/productos | Carga normal | 10 | 21 ms | 0 % | Cumple (incluye 20 % de peticiones inválidas → 422) |
| MP-06 | POST /api/catalogo/productos/consulta | Capacidad (rampa a 300) | 300 | 31 ms | 0 % | Sin quiebre hasta 300 usuarios |
| MP-07 | POST /api/auth/login | Carga normal | 10 | 160 ms | 0 % | Cumple |
| MP-08 | POST /api/auth/login | Carga pico (100 a la vez) | 100 | 4.7 s | 0 % | **No cumple** |
| MP-09 | POST /api/auth/login | Estrés (rampa a 300) | 300 | 15 s | 0 % | **Quiebre ≈ 88 usuarios**, máx ~23 logins/s |
| MP-10 | GET /api/reportes/alertas/stock-bajo | Carga normal | 20 | 66 ms | 0 % | Cumple |
| MP-11 | GET /api/reportes/dashboard | Estrés (rampa a 200) | 200 | 8.6 s | 0 % | **Quiebre ≈ 99 usuarios**, máx ~26 req/s |

## Interpretación

1. **Consultas del catálogo (MP-01 a MP-06):** muy por debajo del límite de 2 s, incluso con 200 a 400 usuarios.
   En la rampa de MP-04 el throughput dejó de crecer cerca de 170 req/s (alrededor de 360 usuarios): a partir de
   ahí la CPU está saturada y lo que crece es la latencia (el p95 pasó de ~60 ms a ~900 ms), sin errores.
   Ese es el punto donde conviene escalar horizontalmente (HPA de Catálogo y Gateway en Kubernetes).

2. **Login (MP-07 a MP-09) — principal cuello de botella:** el login es lento *a propósito*. Las contraseñas se
   verifican con **scrypt** (N=32768), que cuesta ~70 ms de CPU por intento para dificultar ataques de fuerza
   bruta. Con 2 vCPU eso limita el servicio a ~20-23 logins por segundo; cuando llegan más, las peticiones hacen
   fila y el tiempo de respuesta sube (no hay errores, solo espera). Con 100 usuarios entrando a la vez (MP-08) el
   p95 fue 4.7 s.
   Es un **compromiso entre seguridad y rendimiento**, no un error de programación.

3. **Reportes (MP-10, MP-11):** la consulta de alertas cumple holgadamente. El **dashboard** es el endpoint más
   costoso porque Reportes no tiene base de datos: por cada petición consulta a Inventario (existencias, alertas,
   resumen de salidas) y a Catálogo (todos los productos activos, ~620 al final de las pruebas porque MP-05 creó
   productos). Una petición individual tarda ~0.1 s, pero con ~100 usuarios concurrentes se satura (~26 req/s) y
   supera los 2 s. Esto muestra el costo de la composición de datos entre microservicios.

4. **Tasa de error 0 % en todas las pruebas:** con carga excesiva el sistema se vuelve lento pero no falla.
   Durante la primera corrida apareció un 0.17 % de errores `RemoteDisconnected`: Gunicorn cerraba conexiones
   inactivas a los 2 s (keep-alive por defecto) mientras Locust las reutilizaba. Se subió el keep-alive a 75 s en
   todos los servicios y el error desapareció.

## Optimizaciones propuestas (a validar en la Entrega 4 con comparación antes/después)

| Problema | Optimización propuesta | Prueba que la valida |
|---|---|---|
| Login limitado por CPU (scrypt) | Escalar horizontalmente el servicio de Usuarios (más réplicas/HPA); en Kubernetes cada réplica aporta ~20 logins/s. Alternativa a discutir: bajar el costo de scrypt (menos seguro). | MP-08, MP-09 |
| Dashboard lento con muchos usuarios | Caché en memoria de corta duración (p. ej. 30 s) en Reportes; ejecutar en paralelo las consultas a Inventario y Catálogo; pedir solo los productos con movimientos en lugar de todo el catálogo. | MP-11 |
| Saturación de CPU en consultas de catálogo | HPA de Catálogo y Gateway (ya definido en `k8s/`). | MP-04 |

## Pendiente

- **MP-12 a MP-15 (Cypress, E2E):** requieren la interfaz web, que está planeada para la Entrega 4.
  Mientras tanto, los mismos flujos se verifican vía API con `pruebas/flujo_demo.py` (login por rol, registro de
  producto con validación, búsqueda por moto y alertas).
- Repetir MP-01 a MP-11 sobre Kubernetes y comparar con estos resultados.
