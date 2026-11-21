# Estudiantes: Manuela Palacio Diaz, Cristian Camilo Echeverry Sánchez
## Docente: José Albeiro Montes Gil
Ingeniería de Software II
## 23/11/2026
Tercera entrega: Implementación e integración

## Qué se entrega

| Requisito de la Entrega 3 | Evidencia en el repositorio |
|---|---|
| Microservicios core implementados y funcionales | `servicios/usuarios`, `catalogo`, `inventario`, `compras`, `reportes` |
| Accesibles únicamente a través del API Gateway propio | `servicios/gateway` (Flask, sin Kong ni gateways de terceros). En Kubernetes es el único `NodePort`; los demás servicios son `ClusterIP` |
| Comunicación entre microservicios (REST) | Compras → Inventario (recepciones), Inventario/Compras → Catálogo (validación de productos), Reportes → Inventario + Catálogo |
| Contenerización individual (Dockerfile) | Un `Dockerfile` multietapa por servicio (6 en total) |
| Despliegue orquestado inicial en Kubernetes | `k8s/` (namespace, configmap, secret, mysql, 6 deployments/services, 3 HPA) |
| Avance de las 15 pruebas de rendimiento por integrante | Manuela: MP-01 a MP-11 ejecutadas (`pruebas/rendimiento/manuela`). Cristian: `pruebas/rendimiento/cristian` |
| Documentación de API (OpenAPI/Swagger) | `/api/<servicio>/docs/` en cada servicio, publicado a través del Gateway |
| Bitácora de uso de IA | `TerceraEntrega/BitacoraIA Entrega 3.md` |

## Cobertura de requerimientos funcionales

| RF | Endpoint(s) principales |
|---|---|
| RF01 Productos | `GET/POST /api/catalogo/productos`, `GET/PUT/DELETE /api/catalogo/productos/{id}` (DELETE = dar de baja) |
| RF02 Categorías y subcategorías | `GET/POST /api/catalogo/categorias`, `GET/PUT/DELETE /api/catalogo/categorias/{id}` |
| RF03 Proveedores | `GET/POST /api/compras/proveedores`, `/proveedores/{id}`, `/proveedores/{id}/productos` |
| RF04 Control de stock | `POST /api/inventario/movimientos/{entradas,salidas,ajustes,traslados}` |
| RF05 Bodegas | `GET/POST /api/inventario/bodegas`, `GET /api/inventario/existencias/producto/{id}` (stock por bodega) |
| RF06 Órdenes de compra | `POST /api/compras/ordenes`, `PATCH /ordenes/{id}/estado`, `POST /ordenes/{id}/recepciones` |
| RF07 Usuarios y roles | `GET/POST /api/usuarios/`, `PUT/DELETE /api/usuarios/{id}`, `GET /api/usuarios/roles` (ADMIN y OPERADOR) |
| RF08 Autenticación | `POST /api/auth/login`, `/logout`, `/recuperar`, `/restablecer`, `PUT /api/auth/password` |
| RF09 Alertas de stock | `PUT /api/inventario/umbrales/{producto_id}`, `GET /api/reportes/alertas/stock-bajo` |
| RF10 Trazabilidad (kardex) | `GET /api/inventario/kardex`, `GET /api/inventario/movimientos/{codigo}` |
| RF11 Reportes | `GET /api/reportes/existencias`, `/valorizacion`, `/rotacion` |
| RF12 Búsqueda y filtrado | `GET /api/catalogo/productos?q=&codigo=&categoria_id=&proveedor_id=` |
| RF13 Devoluciones | `POST /api/inventario/movimientos/devoluciones` (CLIENTE suma stock, PROVEEDOR resta) |
| RF14 Dashboard | `GET /api/reportes/dashboard` |
| RF15 Compatibilidad | `GET /api/catalogo/productos/compatibles?modelo=&marca=&anio=` |

## Flujo de comunicación principal: recepción de una orden de compra

```
Cliente ──POST /api/compras/ordenes/7/recepciones──► Gateway (valida JWT, agrega X-Usuario-*)
   Gateway ──► Compras: valida estado de la orden y cantidades pendientes
      Compras ──POST /api/inventario/movimientos/entradas──► Inventario   (contrato Entrega 2)
         Inventario ──POST /api/catalogo/productos/consulta──► Catálogo (¿existen y están activos?)
         Inventario: bloquea los saldos (SELECT ... FOR UPDATE), suma stock, registra kardex
      ◄── 201 {transaccion_id: "MOV-ENT-2026-00002"}
   Compras: guarda la recepción con la transacción, estado RECIBIDA_PARCIAL o RECIBIDA
```

Si Inventario no responde, Compras devuelve 503/504 y **no** marca la orden como recibida.

## Decisiones de implementación (cambios respecto al diseño de la Entrega 2)

Durante la implementación se ajustaron algunos detalles del diseño. Se documentan aquí con su justificación:

| Diseño (Entrega 2) | Implementación | Justificación |
|---|---|---|
| Tablas separadas `CATEGORIA` y `SUBCATEGORIA` | Una tabla `categorias` con `padre_id` (autorrelación) | Permite subcategorías de cualquier nivel con una sola tabla y un solo CRUD; la API expone `?padre_id=` y `/categorias/{id}` devuelve sus subcategorías |
| `MARCA_MOTO` como tabla aparte | `modelos_moto` con columna `marca` | Simplificación: las marcas son pocas y no tienen atributos propios |
| `PRODUCTO` sin precio de costo | Se agregó `precio_costo` | El contrato Reportes → Catálogo (Entrega 2) lo devuelve y la valorización del inventario lo necesita |
| `stock_minimo` en cada `EXISTENCIA` (por bodega) | Tabla `umbrales_stock` (por producto) | El contrato de alertas de la Entrega 2 compara el **stock total** contra un único mínimo y muestra el desglose por bodega |
| Tabla `KARDEX` aparte | El kardex son las líneas de `detalles_movimiento` con `saldo_resultante` | Evita duplicar la misma información en dos tablas; el endpoint `GET /api/inventario/kardex` la presenta como kardex |
| `ROL_PERMISO` y `PERMISO` | Autorización por rol (ADMIN / OPERADOR) en cada endpoint | El enunciado pide al menos dos roles con permisos diferenciados; los permisos finos quedan como mejora |
| Una instancia de base de datos por servicio | Una instancia MySQL con **una base de datos y un usuario por servicio** | Cada usuario solo tiene permisos sobre su base (`GRANT ... ON catalogo_db.*`), así ningún servicio puede leer la base de otro (RNF02), con menor consumo de recursos en minikube |
| `POST /api/catalogo/productos/` para consulta por ids | `POST /api/catalogo/productos/consulta` | La ruta original chocaba con la creación de productos (`POST /api/catalogo/productos`) |

## Aspectos técnicos para la sustentación

- **Gateway propio:** enruta por prefijo (`/api/<servicio>/...`), valida el JWT (firma, expiración y lista de
  revocados con caché de 30 s), elimina los encabezados `X-Usuario-*` que mande el cliente y agrega los validados,
  genera el `X-Request-Id` y responde 503/504 cuando un servicio no está disponible o no responde.
- **Concurrencia en inventario:** las salidas simultáneas no pueden dejar stock negativo. Se usa
  `SELECT ... FOR UPDATE` sobre las filas de existencias, bloqueadas siempre en el mismo orden, y reintento
  automático si MySQL detecta un *deadlock*. Prueba: 60 salidas simultáneas de 1 unidad sobre un stock de 30 →
  exactamente 30 aceptadas (201), 30 rechazadas (409) y saldo final 0.
- **Tolerancia a fallos:** si se detiene Reportes, el Gateway responde 503 para Reportes y el resto del sistema
  sigue funcionando.
- **Validación (RNF18):** Marshmallow valida tipos, rangos, formatos (SKU, NIT, correo) y reglas de negocio
  (precio de venta ≥ costo, bodegas distintas en traslados, no recibir más de lo pendiente).
- **Datos de ejemplo:** al iniciar, cada servicio crea datos de MotoPartes Andina si su base está vacía
  (2 bodegas, 9 productos, 3 proveedores, 8 modelos de moto, umbrales con productos en alerta).

## Cómo verificar en la demo

```bash
python pruebas/flujo_demo.py http://<gateway>      # recorre todo el flujo y verifica 24 pasos
```

## Pendiente para la Entrega 4

- Interfaz web y pruebas E2E con Cypress (MP-12 a MP-15 y CE-12 a CE-15).
- Repetir las pruebas de rendimiento sobre Kubernetes y validar las optimizaciones propuestas
  (ver `pruebas/rendimiento/manuela/ANALISIS.md`).
- Manual de instalación final y documentación de arquitectura actualizada.
