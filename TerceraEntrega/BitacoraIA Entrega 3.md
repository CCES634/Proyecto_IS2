| Proyecto | Sistema de Gestión de Inventarios – MotoPartes Andina S.A.S. |
|-----------|-----------|
| Equipo / integrantes | Manuela Palacio Diaz, Cristian Camilo Echeverry Sánchez |
| Entrega N° | 3 |
| Periodo cubierto | 27/10/2026 - 23/11/2026 |

| Fecha | Integrante | Herramienta de IA | Tarea / Actividad apoyada | Prompt Utilizado (resumen) | Nivel de intervención humana | Resultado / Aprendizaje |
|-----------|-----------|-----------|-----------|-----------|-----------|-----------|
| 08/11/2026 | Manuela Palacio Díaz | Claude | Análisis del alcance de la Entrega 3 | Se compartieron el enunciado, las diapositivas de las Entregas 1 y 2 y el repositorio, y se pidió revisar qué faltaba para la Entrega 3 antes de empezar. | Alto | La IA resumió los entregables y señaló que la Entrega 2 no estaba en el repositorio y que el enunciado exige evidencia individual de cada integrante (commits, ramas y PR). El equipo decidió las tecnologías (Python con Flask, MySQL) y la forma de repartir el trabajo. |
| 21/11/2026 | Manuela Palacio Díaz | Claude | Implementación de los microservicios | Con base en los contratos de API, los modelos E-R y el plan de pruebas de la Entrega 2, se pidió implementar los cinco microservicios en Flask + flask-smorest + SQLAlchemy con MySQL, con Swagger, validación con Marshmallow y roles ADMIN/OPERADOR. | Bajo | La IA generó el código de los servicios y los datos de ejemplo. Se revisó contra los diagramas E-R y se documentaron las diferencias con el diseño (tabla "Decisiones de implementación" del documento de la entrega). Aprendizaje: estructura de un servicio Flask con blueprints, esquemas y manejo de errores en JSON. |
| 21/11/2026 | Manuela Palacio Díaz | Claude | API Gateway propio | Se pidió un Gateway propio (sin Kong) que enrute por prefijo, valide el JWT y sea el único punto de entrada. | Bajo | La IA implementó el Gateway con Flask + requests. Se comprobó que sin token responde 401, que un servicio caído da 503 sin afectar a los demás y que el token deja de servir después del logout. Aprendizaje: por qué el Gateway debe borrar los encabezados de identidad que manda el cliente. |
| 21/11/2026 | Manuela Palacio Díaz | Claude | Verificación de punta a punta y corrección de errores | Se pidió levantar todos los servicios y probar el flujo completo (login → orden de compra → recepción → salida → traslado → alertas → logout) a través del Gateway, sobre MySQL. | Medio | Al probar aparecieron errores que la IA no había previsto: el Gateway no enrutaba rutas con "/" final, y con 40 salidas simultáneas MySQL generaba *deadlocks* (error 500). La causa era que el `SELECT ... FOR UPDATE` con JOIN bloqueaba también la fila de la bodega. Se corrigió bloqueando solo las existencias, en orden fijo, con reintento. Se verificó con 60 salidas simultáneas sobre 30 unidades: 30 aceptadas, 30 rechazadas y saldo final 0. |
| 21/11/2026 | Manuela Palacio Díaz | Claude | Alineación con el plan de pruebas de la Entrega 2 | Se pidió comparar los endpoints implementados con los del plan de pruebas y con los diagramas E-R. | Medio | Cuatro rutas no coincidían con el plan (`/productos/compatibles`, `/productos/consulta`, `/alertas/stock-bajo`, `/kardex`) y se renombraron. Se agregaron campos de los diagramas (años de compatibilidad, último acceso y costo promedio). |
| 21/11/2026 | Manuela Palacio Díaz | Claude | Docker Compose y manifiestos de Kubernetes | Se pidió un Dockerfile multietapa por servicio, un docker-compose para desarrollo y los manifiestos de Kubernetes planeados en la Entrega 2 (namespace, configmap, secret, deployments, services, HPA). | Bajo | Se generaron los archivos y se validaron los manifiestos contra el esquema de Kubernetes 1.30. Aprendizaje: diferencia entre Service ClusterIP y NodePort, y uso de readiness/liveness probes. |
| 21/11/2026 | Manuela Palacio Díaz | Claude | Pruebas de rendimiento MP-01 a MP-11 con Locust | Se pidió implementar las pruebas Locust del plan de la Entrega 2, un script que las ejecute por escenario y un análisis de resultados. | Medio | Primera corrida: 0.17 % de errores `RemoteDisconnected` por el keep-alive de Gunicorn (2 s); se subió a 75 s. También se corrigió un fallo de la propia prueba, que usaba categorías inexistentes. Resultado: las consultas de catálogo cumplen con 200-400 usuarios; el login (scrypt) y el dashboard son los cuellos de botella. |

## Reflexión final de la fase

En esta entrega delegamos a la IA la mayor parte de la escritura del código (servicios, Gateway, Dockerfiles,
manifiestos y pruebas de Locust), porque el diseño ya estaba definido en la Entrega 2 y el tiempo era corto. Nuestro
trabajo se concentró en dar el contexto (contratos, modelos E-R y plan de pruebas), revisar que lo generado
coincidiera con ese diseño y verificarlo ejecutándolo. La verificación fue lo más importante: el código generado
parecía correcto, pero al probarlo con MySQL y con peticiones concurrentes aparecieron errores reales (deadlocks,
rutas que no enrutaban, conexiones cerradas por keep-alive) y nombres de endpoints distintos a los del plan.
Aprendimos que una prueba de concurrencia y una prueba de punta a punta encuentran problemas que una revisión del
código no muestra, y que es necesario documentar las diferencias entre el diseño y la implementación en lugar de
ocultarlas. Como limitación, las pruebas de rendimiento de esta entrega se ejecutaron en un entorno local de 2 vCPU,
así que los números deben repetirse sobre Kubernetes en la Entrega 4.
