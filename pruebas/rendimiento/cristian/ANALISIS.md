# Análisis de rendimiento — CE-01 a CE-11

Las pruebas se ejecutaron con Locust 2.47.0 contra el API Gateway de MotoPartes Andina, desplegado en Kubernetes con minikube sobre Ubuntu 24.04. Locust y el clúster compartieron el mismo equipo. La corrida comenzó el 22 de noviembre de 2026 a las 23:52, hora de Colombia. La evidencia está en el [resumen de la corrida](./resultados/20261122-235210-152753/RESUMEN.md).

Como referencia de rendimiento se usaron **p95 inferior a 2.000 ms y menos del 1 % de fallos**. Para CE-01 también se revisó el tiempo máximo, ya que el objetivo era consultar existencias por bodega en menos de 2 segundos.

## Resultados por escenario

| Caso | Usuarios | Solicitudes | p95 | Solicitudes/s | Fallos | Resultado |
|---|---:|---:|---:|---:|---:|---|
| CE-01 | 20 | 568 | 21 ms | 9,62 | 0 | Cumplió el objetivo de consulta de stock por bodega. La solicitud más lenta tomó 89 ms. |
| CE-02 | 200 | 7.920 | 730 ms | 88,75 | 0 | La consulta de stock soportó los 200 usuarios previstos. |
| CE-03 | 50–300 | 17.959 | 22–160 ms | 25,07–135,27 | 0 | Existencias cumplió el criterio hasta el mayor nivel probado, 300 usuarios. |
| CE-04 | 20 | 577 | 43 ms | 9,79 | 0 | El saldo final coincidió con la cantidad de salidas aceptadas registrada en el log. |
| CE-05 | 60 | 868 | 480 ms | 29,90 | 0 | Se agotaron las 30 unidades disponibles y el saldo final fue cero. |
| CE-06 | 50–300 | 13.522 | 60–3.100 ms | 24,61–79,93 | 0 | A 300 usuarios se superó por primera vez el umbral de latencia entre los niveles probados. |
| CE-07 | 20 | 569 | 63 ms | 9,63 | 0 | Los traslados entre bodegas cumplieron el criterio de carga normal. |
| CE-08 | 20 | 584 | 23 ms | 9,91 | 0 | La consulta del kardex cumplió el criterio de carga normal. |
| CE-09 | 20 | 576 | 71 ms | 9,78 | 0 | La creación de órdenes cumplió el criterio de carga normal. |
| CE-10 | 0 de 40 previstos | 0 | — | — | — | La corrida terminó sin registrar solicitudes de recepción. |
| CE-11 | 50–300 | 13.928 | 94–3.500 ms | 24,47–78,86 | 2 | El rendimiento se estabilizó cerca de 79 solicitudes/s y el p95 superó el umbral a 300 usuarios. |

En los casos con varios niveles, la tabla suma las solicitudes y los fallos de las cuatro corridas. La latencia y las solicitudes por segundo se presentan como rangos observados por nivel.

## Hallazgos

### CE-04 y CE-05 · Consistencia de inventario

En CE-04, el log final registró **585 salidas aceptadas** y un saldo de **99.415** unidades, a partir de 100.000 unidades iniciales. En CE-05 se aceptaron **30 salidas**, se registraron **864 rechazos esperados por stock insuficiente** y el saldo final fue **0**. Locust contabilizó esos rechazos como respuestas esperadas porque validan la regla de negocio.

Los CSV y los informes finales de los logs difieren en el total de solicitudes. CE-04 reporta **577 en el CSV y 585 en el log**, mientras que CE-05 reporta **868 en el CSV y 894 en el log**. La tabla usa las cifras de los CSV. La validación de saldos usa los conteos finales de los logs.

### CE-06 · Estrés de entradas

Al pasar de 200 a 300 usuarios, el p95 aumentó de **1.300 a 3.100 ms** y el rendimiento pasó de **73,01 a 79,93 solicitudes/s**. El primer nivel probado que superó el umbral de latencia fue el de 300 usuarios. Todas las solicitudes medidas fueron aceptadas.

### CE-10 · Recepción de órdenes

Locust alcanzó el límite de **40 segundos** sin llegar a generar usuarios ni registrar solicitudes de recepción, aunque devolvió código de salida `0`. La preparación de órdenes es una causa probable. El log no permite confirmar hasta dónde avanzó esa etapa.

Queda pendiente repetir CE-10 con las órdenes preparadas antes de iniciar la ventana de medición y verificar que las recepciones confirmadas se reflejen en el stock de Inventario.

### CE-11 · Tráfico mixto por el Gateway

Con 200 usuarios se registraron **dos respuestas HTTP 503** en el endpoint de entradas de Inventario, equivalentes al **0,04 %** de las solicitudes de ese nivel. Al pasar de 200 a 300 usuarios, el rendimiento agregado se mantuvo cerca de **79 solicitudes/s** y el p95 aumentó de **1.600 a 3.500 ms**. A 300 usuarios, el kardex tuvo el mayor p95 por endpoint, con **4.300 ms**.

El rendimiento se estabilizó mientras aumentaba la latencia bajo tráfico mixto. Para atribuir ese comportamiento al Gateway, se necesitan métricas simultáneas del Gateway, los servicios internos y el equipo que ejecutó la prueba.

## Conclusión

La corrida produjo evidencia para **10 de los 11 escenarios**. Las operaciones de carga normal cumplieron el criterio de rendimiento. La consulta de existencias llegó a **300 usuarios con p95 de 160 ms y cero fallos**. El límite de capacidad de ese endpoint queda por determinar.

Las entradas de inventario y el tráfico mixto superaron el umbral de p95 a **300 usuarios**. La prueba de salidas concurrentes confirmó que el inventario quedó en **cero unidades**, con rechazo de las solicitudes que excedían el stock. **CE-10 requiere una nueva corrida** para completar la evidencia de recepción de órdenes.
