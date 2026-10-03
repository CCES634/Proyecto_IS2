Ingeniería de Software II

28/09/2026

## Investigación Sistemas de Gestión de Inventario

## Objetivos:

- Identificar y analizar como mínimo tres (3) sistemas de gestión de inventarios existentes (comerciales, de código abierto o corporativos).

- Elaborar un cuadro comparativo de funcionalidades, arquitectura (cuando sea posible identificarla) y experiencia de usuario.

- Extraer conclusiones que alimenten la definición del alcance del sistema propio.

## Definición del problema y alcance del sistema

# Contextualización de la empresa

MotoPartes Andina S.A.S. es una empresa ficticia ubicada en Manizales dedicada a la comercialización y distribución de repuestos y accesorios para motocicletas. La empresa se especializa en la distribución de productos de diversas marcas, tales como filtros, bujías, pastillas de freno, baterías, llantas, kits de arrastre y componentes eléctricos. Estos productos son destinados tanto a clientes particulares como a talleres de motocicletas.
En la actualidad, la empresa gestiona la mayor parte de su inventario mediante hojas de cálculo y registros manuales. A medida que ha aumentado la cantidad de productos, proveedores y movimientos entre sus bodegas, este método ha comenzado a generar problemas como diferencias entre las existencias físicas y las registradas, dificultad para conocer el stock disponible en cada ubicación, retrasos en el reabastecimiento y poca trazabilidad sobre las entradas, salidas, ajustes y traslados realizados.
Por otra parte, debido a la naturaleza del negocio, resulta imperativo mantener información organizada sobre la compatibilidad de los repuestos con diferentes marcas y modelos de motocicletas. Asimismo, es crucial controlar a los proveedores, las órdenes de compra, las devoluciones y los niveles mínimos de existencias con el fin de evitar faltantes de productos.
En este sentido, MotoPartes Andina busca implementar un sistema de gestión de inventarios que permita administrar de manera centralizada productos, categorías, proveedores, bodegas, existencias, movimientos, compras y usuarios, generando alertas, manteniendo la trazabilidad de las operaciones y proporcionando reportes e indicadores para respaldar la toma de decisiones. El sistema deberá ser diseñado para poder mantenerse y crecer con las necesidades de la empresa, mediante la separación de sus principales procesos de negocio mediante una arquitectura de microservicios.

# Definición del problema

MotoPartes Andina S.A.S. presenta dificultades en la gestión de su inventario debido al uso de hojas de cálculo y registros manuales para controlar productos, existencias, movimientos entre bodegas y compras. Esta situación genera diferencias entre el inventario físico y el registrado, dificulta conocer el stock disponible en cada ubicación, retrasa el reabastecimiento y limita la trazabilidad de las entradas, salidas, ajustes y traslados. Además, la variedad de repuestos y sus diferentes compatibilidades con marcas y modelos de motocicletas incrementan la complejidad de mantener la información organizada y actualizada.

Por lo anterior, la empresa requiere un sistema de gestión de inventarios que centralice y automatice la administración de productos, proveedores, bodegas, existencias, compras y movimientos, incorporando alertas y reportes que faciliten la toma de decisiones.

# Alcance

El sistema para MotoPartes Andina S.A.S. estará orientado a modernizar el control de inventario de repuestos y accesorios para motocicletas, actualmente manejado mediante registros manuales y hojas de cálculo. Permitirá gestionar productos, categorías, proveedores, bodegas, stock, movimientos, órdenes de compra, devoluciones, usuarios, alertas, trazabilidad, búsquedas, reportes e indicadores, cubriendo así los requerimientos funcionales mínimos establecidos para el proyecto.

## JD Edwards:

El sistema de gestión de inventarios no tiene un nombre comercial independiente; se

integra directamente bajo el ERP JD Edwards (en sus versiones JD Edwards EnterpriseOne y

JD Edwards World) dentro del módulo de Inventarios (Inventory) y la suite de Gestión de la

Cadena de Suministro (Supply Chain Management - SCM).

El módulo de Gestión de Inventarios de JD Edwards EnterpriseOne (Inventory

Management) constituye el núcleo de la cadena de suministro (Supply Chain Management)

en el ERP. Define y gestiona artículos discretos de inventario para rastrearlos y controlarlos a

lo largo de toda la cadena operativa.

# Funcionalidades clave:

- Integración nativa con el ERP: La gestión de inventarios está estrechamente integrada con la contabilidad general (General Ledger), costos de proyectos (Job Costing), activos fijos, nómina, compras y ventas.


- Soporte a la distribución y manufactura: Cubre la administración de distribución mayorista y operaciones de manufactura, incluyendo la emisión de inventario para órdenes de trabajo (Work Order Inventory Issues) con validación de números de producción.

- Planificación y ejecución de la cadena de suministro: Incluye herramientas divididas en módulos de planificación y ejecución para optimizar ventas, operaciones y el rendimiento logístico.

- Personalización del usuario: Incluye funciones definidas por el usuario (User-Defined Features), lo que permite crear consultas personalizadas y configurar formatos de cuadrícula para visualizar el inventario según las necesidades del negocio.

# Fortalezas:

- Visión global e integrada: Al estar diseñado para ver el panorama completo de la empresa, evita el manejo del inventario como un proceso aislado y asegura la sincronización contable y operativa.

- Flexibilidad multiplataforma: Puede ejecutarse y gestionarse en diversos entornos tecnológicos e infraestructuras existentes.

- Evolución y automatización continua: Incorpora mejoras periódicas para reducir verificaciones manuales y dar soporte a operaciones guiadas por inventario.

# Oportunidades de mejora:

- Alta complejidad de configuración: Requiere configurar constantes, sucursales/plantas, ubicaciones, unidades de medida, referencias, tipos de documento, AAIs, etc.
- Curva de aprendizaje elevada: La gran cantidad de parámetros y módulos hace que el usuario necesite capacitación específica.
- Funciones avanzadas pueden requerir módulos adicionales: JDE separa Inventory Management de Warehouse Management, Manufacturing, Quality Management, etc. Oracle incluso especifica productos/licencias adicionales para determinadas funcionalidades.

## SAP

SAP (siglas en alemán de Systemanalyse Programmentwicklung, traducido

originalmente como "Sistemas, Aplicaciones y Productos en Procesamiento de Datos") es una

empresa multinacional alemana fundada en 1972 por cinco antiguos ingenieros de IBM. Es el

líder mundial en desarrollo de software empresarial y uno de los principales proveedores de

sistemas ERP (Enterprise Resource Planning o Planificación de Recursos Empresariales).

Un sistema ERP como SAP sirve para unificar, automatizar e integrar los procesos

centrales de un negocio (finanzas, compras, ventas, producción, almacén y recursos

humanos) dentro de un único sistema integrado con una base de datos compartida que opera

en tiempo real. Esto permite eliminar silos de información y garantizar una única fuente de

información fiable para toda la organización.

El sistema SAP destaca por su arquitectura modular, escalable e integrada. Se

organiza en áreas funcionales y componentes técnicos que interactúan entre sí.

La gestión de inventarios y existencias se articula principalmente a través del módulo

MM (Gestión de Materiales) y se apoya en sistemas de gestión de almacenes (WMS/EWM) o

soluciones complementarias móviles (como SiMA o Intralog WMS). Funciona mediante las

siguientes dinámicas clave.

## Fortalezas:

- Integración nativa y visión unificada: Se conecta de forma fluida con las áreas centrales de la empresa, como compras y abastecimiento (MM), ventas (SD), planificación de la producción (PP) y contabilidad/finanzas (FI/CO). Esto centraliza la información en una única fuente de verdad y actualiza al instante la disponibilidad de existencias y los estados financieros.

- Cobertura del ciclo de vida del producto: Permite controlar minuciosamente todas las categorías de inventario, incluyendo materias primas y componentes, trabajo en curso (WIP), productos terminados y suministros de mantenimiento, reparación y funcionamiento (MRO).

- Soporte para múltiples técnicas de optimización: Incorpora de manera nativa metodologías estratégicas de control de existencias, tales como la segmentación (Análisis ABC), Just-in-Time (JIT), stock de seguridad, Cantidad de Pedido Económica (EOQ) y reglas de rotación de salidas como FIFO y LIFO.

- Tecnologías inteligentes y analítica avanzada: Las suites más recientes y soluciones ERP en la nube integran capacidades de inteligencia artificial, machine learning, IoT y analítica predictiva para la detección proactiva de la demanda.

- Reducción de costos y previsión de riesgos: Minimiza los costos de almacenamiento, el deterioro, la obsolescencia y los residuos, al mismo tiempo que evita la falta de stock y las pérdidas de ventas.

## Oportunidades de mejora:

- Interfaz poco adaptada para la movilidad en almacén: Las pantallas del sistema estándar de SAP están diseñadas principalmente para ordenadores de sobremesa. En dispositivos móviles o tabletas resultan poco intuitivas (navegación compleja, botones pequeños y sobrecarga de campos), lo que genera retrasos y lleva al personal a anotar datos en papel para digitarlos después.

- Desincronización entre el almacén físico y el ERP: Cuando los datos no se registran de forma digital en el momento exacto en que ocurren los movimientos en la planta, se crean desfases de tiempo, información obsoleta y silos de información entre el almacén real y SAP.

- Rigidez para la corrección inmediata de errores: En la función estándar, si un operario comete una equivocación en cantidades o ubicaciones, no


suele contar con la autonomía para corregir o anular la transacción desde el

almacén, dependiendo de un administrador o de un terminal PC

tradicional.

- Falta de evidencias digitales directas: La gestión tradicional dificulta certificar la responsabilidad y el estado físico de los materiales al momento del movimiento, ya que el estándar no captura de forma nativa pruebas fotográficas o firmas digitales vinculadas a la transacción (requiriendo soluciones complementarias o Add-Ons como SiMA o Intralog WMS).

- Altos costos e implementación compleja: La adopción del sistema requiere una inversión inicial considerable en licencias, infraestructura y consultoría, sumado a una curva de aprendizaje exigente para los usuarios y dependencia del lenguaje especializado ABAP para personalizar procesos.

## Obbo Inventory:

Odoo es una plataforma de gestión empresarial compuesta por diferentes aplicaciones

que permiten administrar procesos como ventas, compras, contabilidad, fabricación e

inventario. Dentro de esta plataforma se encuentra Odoo Inventory, la aplicación encargada

de gestionar existencias, almacenes, ubicaciones y movimientos de productos.

El sistema se caracteriza por su enfoque modular, ya que la aplicación de Inventario

puede trabajar de manera integrada con otros módulos de Odoo, como Compras, Ventas y

Manufactura. Desde el punto de vista técnico, Odoo utiliza una arquitectura cliente-servidor y

sus diferentes funcionalidades se organizan mediante módulos que pueden instalarse o

extenderse según las necesidades de la organización. Su cliente web funciona como una

aplicación de página única (SPA), permitiendo que la interfaz actualice únicamente la

información necesaria durante la interacción del usuario


## Funcionalidades clave:

- Gestión de múltiples almacenes y ubicaciones: permite administrar varios almacenes físicos y dividirlos en ubicaciones específicas como estantes, pisos o pasillos. También permite realizar y controlar movimientos de mercancía entre diferentes almacenes.

- Control y trazabilidad del inventario: permite realizar seguimiento a los productos mediante lotes y números de serie, facilitando conocer su origen, ubicación, movimientos realizados y destino dentro de la cadena de suministro.

- Reabastecimiento automático: permite configurar reglas de reposición para mantener niveles mínimos de inventario. Cuando las existencias disminuyen, el sistema puede sugerir o generar órdenes de compra o fabricación según la configuración establecida.

- Gestión mediante códigos de barras: permite identificar productos y ubicaciones mediante códigos de barras, agilizando actividades como selección de productos, traslados y ajustes de inventario, además de disminuir el ingreso manual de datos.

- Reportes y seguimiento de existencias: permite consultar productos disponibles, cantidades almacenadas, ubicaciones y movimientos históricos, facilitando el control sobre el estado actual del inventario.

## Fortalezas:

- Integración entre aplicaciones: el módulo de Inventario puede relacionarse con procesos de compras, ventas y fabricación, permitiendo que los movimientos generados en estas áreas se reflejen dentro de la gestión del inventario.

- Flexibilidad y modularidad: Odoo está compuesto por módulos que pueden ampliar o modificar las funciones del sistema, lo cual permite adaptar la plataforma a diferentes necesidades empresariales.


- Automatización del abastecimiento: las reglas de reabastecimiento permiten mantener niveles mínimos de productos y reducir la necesidad de revisar manualmente cuándo se debe realizar una nueva compra o fabricación.

- Trazabilidad detallada: el uso de lotes, números de serie y registros de movimientos permite realizar seguimiento al recorrido de los productos y consultar las operaciones realizadas sobre el inventario.

## Oportunidades de mejora:

- Configuración de funcionalidades avanzadas: herramientas como las ubicaciones de almacenamiento, rutas de varios pasos, lotes y números de serie deben ser habilitadas y configuradas previamente, lo que aumenta el trabajo inicial de configuración del sistema.

- Dependencia de aplicaciones adicionales: algunas funcionalidades requieren instalar otros módulos de Odoo. Por ejemplo, para utilizar completamente las operaciones mediante códigos de barras es necesario contar con la aplicación correspondiente.

- Mayor complejidad al aumentar las necesidades: aunque la modularidad facilita adaptar el sistema, una empresa con procesos muy específicos puede necesitar configurar o desarrollar módulos adicionales para cubrir sus requerimientos particulares.

- Cantidad de opciones de configuración: la existencia de almacenes, ubicaciones, rutas, reglas de reabastecimiento, tipos de operación y diferentes mecanismos de trazabilidad puede hacer que la configuración inicial requiera un mayor conocimiento de la plataforma. Esto se identifica a partir de las diferentes configuraciones requeridas por las funciones documentadas de Odoo.


| Sistema | Funcionalidades | Arquitectura | Experiencia de usuario |
| --- | --- | --- | --- |
| JD Edwards | Gestión de artículos e inventario, integración con compras, ventas, contabilidad, manufactura y planificación de la cadena de suministro. | Integrado dentro del ERP JD Edwards EnterpriseOne y conectado con otros módulos empresariales. | Orientado a entornos empresariales. Permite personalizar consultas y formatos de visualización según las necesidades del usuario. |
| SAP | Gestión de materiales, existencias, almacenes, compras, producción, trazabilidad y técnicas como ABC, JIT, FIFO y LIFO. | Arquitectura modular e integrada, organizada en diferentes áreas funcionales que comparten información dentro del ERP. | Muy completo, pero algunas operaciones pueden resultar complejas. La interfaz tradicional presenta dificultades de uso en dispositivos móviles y puede requerir mayor aprendizaje. |
| Odoo Inventory | Gestión de productos, existencias, almacenes, ubicaciones, movimientos, trazabilidad, reabastecimiento automático y códigos de barras. | Arquitectura modular y cliente- servidor, donde Inventario se integra con aplicaciones como Compras, Ventas y Manufactura. | Interfaz web más sencilla y orientada a operaciones de almacén. El uso de códigos de barras y dispositivos móviles facilita tareas como recepciones, traslados y ajustes. |

## Conclusiones

A partir del análisis identificamos que los sistemas de gestión de inventarios más

completos comparten elementos como el control de productos y existencias, manejo de

múltiples ubicaciones, integración con proveedores y compras, trazabilidad de movimientos,

automatización del reabastecimiento y generación de información para apoyar la toma de

decisiones, pero evidenciamos también que aunque soluciones como SAP y JD Edwards

ofrecen una gran cantidad de funcionalidades, su complejidad puede dificultar su uso, por lo

que para nuestro sistema buscaremos mantener únicamente las funciones necesarias y una

interacción más sencilla para los usuarios.


Con base en estas conclusiones y en las necesidades de la empresa, el alcance inicial

del sistema incluirá la gestión de productos y categorías, compatibilidad de repuestos con

marcas y modelos de motocicletas, proveedores, bodegas, control de stock, movimientos de

inventario, órdenes de compra, alertas de existencias bajas, usuarios y roles, devoluciones,

trazabilidad y reportes básicos.
