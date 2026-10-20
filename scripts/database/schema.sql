-- VetAssistant IA: esquema mínimo compatible con los repositorios existentes.
-- NO incluye datos ficticios de ubicaciones, lotes o fechas de vencimiento.
-- Aplicar únicamente después de un respaldo en un servidor autorizado.
CREATE TABLE IF NOT EXISTS productos (
    id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
    producto_id VARCHAR(12) NOT NULL,
    producto VARCHAR(200) NOT NULL,
    categoria VARCHAR(80) NULL,
    stock INT NOT NULL DEFAULT 0,
    stock_minimo INT NOT NULL DEFAULT 0,
    stock_seguridad INT NOT NULL DEFAULT 0,
    punto_reorden INT NOT NULL DEFAULT 0,
    lead_time_dias INT NOT NULL DEFAULT 1,
    ubicacion VARCHAR(120) NULL,
    lote VARCHAR(80) NULL,
    fecha_vencimiento DATE NULL,
    activo TINYINT(1) NOT NULL DEFAULT 1,
    KEY idx_productoid (producto_id),
    KEY idx_producto_nombre (producto),
    KEY idx_producto_vencimiento (fecha_vencimiento),
    KEY idx_producto_critico (stock, stock_minimo),
    CHECK (stock >= 0),
    CHECK (lead_time_dias >= 1)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS historial_consultas (
    id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
    pregunta TEXT NOT NULL,
    intencion VARCHAR(120) NULL,
    producto VARCHAR(200) NULL,
    respuesta TEXT NULL,
    fecha_consulta DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    KEY idx_consulta_fecha (fecha_consulta),
    KEY idx_consulta_intencion (intencion)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS evaluaciones_riesgo_stock (
    id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
    fecha_evaluacion DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    fecha_corte DATE NULL,
    horizonte_dias INT NOT NULL DEFAULT 7,
    modelo VARCHAR(100) NULL,
    umbral_alto DECIMAL(6,4) NULL,
    umbral_medio DECIMAL(6,4) NULL,
    total_productos INT NOT NULL DEFAULT 0,
    alto_riesgo INT NOT NULL DEFAULT 0,
    medio_riesgo INT NOT NULL DEFAULT 0,
    bajo_riesgo INT NOT NULL DEFAULT 0,
    probabilidad_promedio DECIMAL(6,2) NULL,
    KEY idx_eval_fecha (fecha_evaluacion)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS historial_predicciones_stock (
    id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
    evaluacion_id INT NOT NULL,
    fecha_evaluacion DATETIME NOT NULL,
    producto_id VARCHAR(10) NOT NULL,
    producto VARCHAR(150) NOT NULL,
    categoria VARCHAR(80) NULL,
    stock_actual INT NOT NULL DEFAULT 0,
    demanda_estimada_7d INT NOT NULL DEFAULT 0,
    stock_proyectado_7d INT NOT NULL DEFAULT 0,
    probabilidad_riesgo DECIMAL(7,6) NOT NULL DEFAULT 0,
    nivel_riesgo VARCHAR(10) NOT NULL,
    KEY idx_hist_eval (evaluacion_id),
    KEY idx_hist_producto (producto_id),
    KEY idx_hist_fecha (fecha_evaluacion),
    CONSTRAINT fk_hist_eval FOREIGN KEY (evaluacion_id)
        REFERENCES evaluaciones_riesgo_stock(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
