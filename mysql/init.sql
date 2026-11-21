-- Una base de datos por microservicio (RNF02).
-- Cada servicio tiene su propio usuario con permisos SOLO sobre su base de datos,
-- así ningún servicio puede acceder a los datos de otro.
-- (Reportes y Alertas no tiene base de datos.)

CREATE DATABASE IF NOT EXISTS usuarios_db   CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE DATABASE IF NOT EXISTS catalogo_db   CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE DATABASE IF NOT EXISTS inventario_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE DATABASE IF NOT EXISTS compras_db    CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

CREATE USER IF NOT EXISTS 'usuarios_app'@'%'   IDENTIFIED BY 'UsuariosPass2026';
CREATE USER IF NOT EXISTS 'catalogo_app'@'%'   IDENTIFIED BY 'CatalogoPass2026';
CREATE USER IF NOT EXISTS 'inventario_app'@'%' IDENTIFIED BY 'InventarioPass2026';
CREATE USER IF NOT EXISTS 'compras_app'@'%'    IDENTIFIED BY 'ComprasPass2026';

GRANT ALL PRIVILEGES ON usuarios_db.*   TO 'usuarios_app'@'%';
GRANT ALL PRIVILEGES ON catalogo_db.*   TO 'catalogo_app'@'%';
GRANT ALL PRIVILEGES ON inventario_db.* TO 'inventario_app'@'%';
GRANT ALL PRIVILEGES ON compras_db.*    TO 'compras_app'@'%';
FLUSH PRIVILEGES;
