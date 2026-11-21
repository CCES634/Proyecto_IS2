# MotoPartes Andina — Sistema de Gestión de Inventarios con Microservicios

Proyecto de aula de **Ingeniería de Software II** (UNAL).
Integrantes: **Manuela Palacio Díaz** y **Cristian Camilo Echeverry Sánchez**. Docente: José Albeiro Montes Gil.

MotoPartes Andina S.A.S. es una empresa ficticia de Manizales que comercializa repuestos y accesorios para
motocicletas. El sistema reemplaza el control de inventario en hojas de cálculo por una solución basada en
microservicios, contenerizada con Docker y orquestada con Kubernetes.

## Arquitectura

```
                 Cliente (Swagger UI / Postman / Locust / futura interfaz web)
                                        │
                                        ▼
                         ┌─────────────────────────────┐
                         │   API Gateway propio :8000  │  ← único punto de entrada
                         │  enrutamiento · JWT · logs  │     (NodePort 30080 en K8s)
                         └──────────────┬──────────────┘
        ┌──────────────┬────────────────┼────────────────┬──────────────────┐
        ▼              ▼                ▼                ▼                  ▼
  ┌───────────┐  ┌───────────┐    ┌────────────┐   ┌────────────┐    ┌────────────┐
  │ Usuarios y│  │ Catálogo  │◄───│ Inventario │◄──│  Compras y │    │ Reportes y │
  │   Auth    │  │           │    │            │   │ Proveedores│    │  Alertas   │
  └─────┬─────┘  └─────┬─────┘    └─────┬──────┘   └─────┬──────┘    └──┬──────┬──┘
        │              │                │                │   (sin BD)    │      │
   usuarios_db    catalogo_db     inventario_db     compras_db           │      │
                       ▲                ▲                                │      │
                       └────────────────┴──── consultas REST ────────────┘      │
                                        └───────────────────────────────────────┘
```

| Microservicio | Responsabilidad | Requerimientos | Base de datos |
|---|---|---|---|
| **Usuarios y Autenticación** | Login/logout con JWT, roles ADMIN y OPERADOR, cambio y recuperación de contraseña | RF07, RF08, RNF07 | `usuarios_db` |
| **Catálogo** | Productos, categorías/subcategorías, compatibilidad con modelos de moto, búsqueda | RF01, RF02, RF12, RF15 | `catalogo_db` |
| **Inventario** | Bodegas, existencias, entradas, salidas, ajustes, traslados, devoluciones, kardex, umbrales | RF04, RF05, RF09, RF10, RF13 | `inventario_db` |
| **Compras y Proveedores** | Proveedores, órdenes de compra, estados y recepción de mercancía | RF03, RF06 | `compras_db` |
| **Reportes y Alertas** | Alertas de stock bajo, existencias, valorización, rotación y dashboard | RF09, RF11, RF14 | — (consulta Inventario y Catálogo) |
| **API Gateway** (propio) | Enrutamiento, validación de JWT, trazabilidad (X-Request-Id), manejo de fallas | RNF09, RNF10 | — |

**Comunicación:** REST síncrono con JSON. Contratos de la Entrega 2:
Compras → Inventario (`POST /api/inventario/movimientos/entradas`),
Reportes → Inventario (`GET /api/inventario/existencias/alertas`) y
Reportes → Catálogo (`POST /api/catalogo/productos/consulta`).
Los servicios se encuentran por nombre gracias a los *Services* de Kubernetes (Service Discovery por DNS).

**Tecnologías:** Python 3.12 · Flask · flask-smorest (Marshmallow + OpenAPI/Swagger) · SQLAlchemy · MySQL 8 ·
PyJWT · Gunicorn · Docker · Kubernetes · Locust.

## Estructura del repositorio

```
servicios/
  gateway/        API Gateway propio
  usuarios/       Usuarios y Autenticación
  catalogo/       Catálogo
  inventario/     Inventario
  compras/        Compras y Proveedores
  reportes/       Reportes y Alertas (sin base de datos)
mysql/init.sql    Una base de datos y un usuario por microservicio
k8s/              Manifiestos de Kubernetes (despliegue oficial)
docker-compose.yml  Entorno de desarrollo local (apoyo)
pruebas/
  flujo_demo.py   Prueba de humo / guion de la demo (todo pasa por el Gateway)
  rendimiento/    Pruebas de rendimiento con Locust por integrante
PrimeraEntrega/  SegundaEntrega/  TerceraEntrega/   Documentos y bitácoras de IA
```

## Cómo ejecutarlo

### Opción 1 — Docker Compose (desarrollo local)

```bash
docker compose up --build
# Gateway: http://localhost:8000
python pruebas/flujo_demo.py          # recorre el flujo completo y verifica cada paso
```

### Opción 2 — Kubernetes (minikube)

```bash
minikube start --cpus 4 --memory 6g
minikube addons enable metrics-server        # para el escalado automático (HPA)
eval $(minikube docker-env)                  # PowerShell: & minikube -p minikube docker-env --shell powershell | Invoke-Expression
for s in gateway usuarios catalogo inventario compras reportes; do
  docker build -t motopartes/$s:1.0 servicios/$s
done
kubectl apply -k k8s/
kubectl get pods -n motopartes -w            # esperar a que todo esté Running/Ready
python pruebas/flujo_demo.py http://$(minikube ip):30080
```

Ver [`k8s/README.md`](k8s/README.md) para el detalle de los manifiestos.

### Usuario inicial

| Correo | Contraseña | Rol |
|---|---|---|
| `admin@motopartes.com` | `Admin12345` | ADMIN |

## Documentación de la API (Swagger / OpenAPI)

Con el sistema arriba, cada servicio publica su documentación a través del Gateway:

| Servicio | Swagger UI |
|---|---|
| Usuarios y Autenticación | `/api/usuarios/docs/` |
| Catálogo | `/api/catalogo/docs/` |
| Inventario | `/api/inventario/docs/` |
| Compras y Proveedores | `/api/compras/docs/` |
| Reportes y Alertas | `/api/reportes/docs/` |

Para probar endpoints protegidos: hacer login en `POST /api/auth/login`, copiar el `token` y usar el botón
**Authorize** de Swagger.

## Seguridad

- Contraseñas cifradas con **scrypt** (Werkzeug); tokens de recuperación guardados solo como hash SHA-256.
- **JWT HS256** firmado por Usuarios y validado en el Gateway (firma, expiración y lista de tokens revocados).
- El Gateway elimina cualquier encabezado `X-Usuario-*` que venga del cliente y reenvía la identidad validada.
- Autorización por rol en cada microservicio (ADMIN / OPERADOR).
- Los microservicios son `ClusterIP`: desde fuera del clúster solo se llega al Gateway.

## Observabilidad

Todos los componentes escriben logs JSON a la salida estándar con `request_id`, ruta, estado, duración y usuario.
El Gateway genera el `X-Request-Id` y lo propaga a los servicios (y entre servicios), así una petición se puede
seguir en todos los logs:

```bash
kubectl logs -n motopartes -l app=gateway --tail=50
kubectl logs -n motopartes -l app=inventario --tail=50 | grep <request_id>
```
