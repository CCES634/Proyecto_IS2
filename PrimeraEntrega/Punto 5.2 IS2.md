## Estudiantes: Manuela Palacio Diaz, Cristian Camilo Echeverry Sánchez
## Docente: José Albeiro Montes Gil
Ingeniería de Software II
## 28/09/2026
Justificación de la arquitectura de microservicios
## Objetivos
- Comparar arquitectura monolítica vs. arquitectura de microservicios para
el caso de estudio, con criterios técnicos explícitos.
- Definir los microservicios del sistema (identificación de dominios /
bounded contexts) y sus responsabilidades.
- Definir el mecanismo de comunicación entre microservicios (síncrono vía
REST y/o asíncrono vía mensajería).

## Arquitectura monolítica vs arquitectura de microservicios
Considerando el contexto de la empresa con la que se va a desarrollar el proyecto,
tiene ciertas características particulares como el alto número de referencias, una misma parte
para la motocicleta tiene varias versiones de varias marcas, esto hace que no solo haya una
gran variedad de partes, sino de versiones de esta, adicionalmente, debe haber alta velocidad
y disponibilidad ya que no solo los mecánicos van a revisar el stock, sino que clientes y
vendedores del negocio estarán consultando el stock disponible regularmente, por último, el
solo hecho de tener ventas en línea y punto físico da como resultado varias integraciones y
canales.
La empresa al estar creciendo debe pensar en escalar, esto pone en desventaja al
modelo monolítico, ya que es más difícil de escalar que un sistema de microservicios, esto
debido a su capacidad de poder actualizar servicios sin afectar los diferentes elementos del
software, adicionalmente el sistema de microservicios maneja una mejor tolerancia a fallos, si
un sistema monolítico falla, afecta a todo el sistema, caso contrario en el sistema de microservicios, si un servicio falla, no afecta a los demás ya que estos operan de forma independiente. El despliegue e independencia entre los dos es distinto, por ejemplo, si la
empresa debe realizar un cambio en cuanto a políticas de proveedores u otro cambio en la
lógica del sistema, se debe reiniciar todo el sistema completo, en cambio, si se debe realizar
un cambio en la lógica de algún servicio, el único que se reinicia él es el servicio actualizado.
La base de datos en el caso del sistema monolítico es única, en cambio, el sistema de
microservicios permite manejar y gestionar diferentes bases de datos y no necesariamente
deben ser del mismo tipo, esto sirve en caso de que la empresa en algún momento decida
tomar decisiones en cuanto al almacenamiento de la información, por ejemplo, manejar una
base de datos única para un tipo de proveedor o moto.

## Definición de los microservicios y sus responsabilidades
Para el sistema que vamos a desarrollar identificamos cinco dominios principales, los
cuales separaremos en microservicios con responsabilidades específicas. Esta división
permite que cada parte del sistema pueda desarrollarse y modificarse de manera
independiente, evitando que un cambio en una funcionalidad afecte necesariamente al resto
del sistema.
- Microservicio de Catálogo: se encargará de gestionar los productos, categorías y
subcategorías. También almacenará información propia del negocio, como la
compatibilidad de los repuestos con diferentes marcas y modelos de motocicletas,
y permitirá realizar búsquedas y filtros.
- Microservicio de Inventario: será responsable de manejar las bodegas, las
existencias de cada producto y los movimientos de inventario, como entradas,
salidas, ajustes, traslados y devoluciones. También conservará la trazabilidad de
los movimientos realizados.
- Microservicio de Compras y Proveedores: administrará la información de los
proveedores y su relación con los productos. Además, gestionará la creación y
seguimiento de órdenes de compra y la recepción de mercancía.
- Microservicio de Usuarios y Autenticación: gestionará los usuarios del sistema,
sus roles y permisos. También será responsable del inicio y cierre de sesión,
recuperación de contraseña y cambio de contraseña.
- Microservicio de Reportes y Alertas: se encargará de generar alertas cuando un
producto tenga existencias por debajo del mínimo establecido, además de producir
reportes e indicadores sobre existencias, valorización del inventario, rotación de
productos y demás información necesaria para el dashboard.

## Mecanismo de comunicación entre microservicios
La comunicación entre los microservicios del sistema la realizaremos de forma
síncrona mediante API REST, utilizando HTTP y JSON para el intercambio de información.
Cada microservicio expondrá únicamente las operaciones necesarias para que los demás
servicios puedan consultar información o solicitar acciones relacionadas con su dominio.
Las peticiones externas ingresarán al sistema mediante el API Gateway, encargado
de direccionarlas al microservicio correspondiente. Cuando un microservicio requiera
información administrada por otro, realizará una petición a su API en lugar de acceder
directamente a su base de datos, manteniendo así la independencia y separación entre los
servicios.
Por ejemplo, al recibir una orden de compra, el microservicio de Compras y
Proveedores podrá solicitar al microservicio de Inventario el registro de la entrada de
mercancía. De manera similar, el servicio de Reportes y Alertas podrá consultar información
del inventario para generar indicadores y detectar productos con niveles bajos de existencias.
