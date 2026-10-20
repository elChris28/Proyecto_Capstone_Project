# Plan de validación pendiente del avance (UAT y entorno real)

Este documento separa lo implementado de aquello que **todavía no puede marcarse como aceptado**.

## Requisitos para completar el PB13

1. Hacer copia de seguridad de la base MySQL real y ejecutar `python -m scripts.database.init_schema --check`.
2. En una BD limpia de pruebas aplicar `--apply`; `--seed-stock` solo si se autoriza usar el CSV y la tabla de productos está vacía. Nunca hacerlo en producción sin respaldo.
3. Ejecutar `python -m pytest -q tests` desde el entorno Python con dependencias instaladas.
4. Ejecutar `python -m scripts.qa.verify_offline --output evidencias/verificacion_offline.json`.
5. Conectar el sistema a la MySQL operativa, repetir las consultas de riesgo y verificar que sus 500 productos correspondan al inventario real (no dar por válido el reparto de 95/44/361 sin confirmarlo).
6. Con los usuarios responsables aplicar los 25 casos INS-01 del Anexo G en PRE y POS, documentar resultado por caso, fecha, observación, firmas de aceptación y hallazgos.
7. Ejecutar en ambiente HTTPS de pruebas el login con contraseña, acceso restringido a API, CSRF, cierres de sesión y recuperación desde backup. Registrar evidencias.
8. Con eventos reales de quiebre a siete días, medir el impacto operativo; el PSI por sí solo no es validación de la exactitud del modelo.

## Procedimiento para producción

- Definir en `.env` (fuera de Git) `APP_ENV=production`, `SECRET_KEY` de 32+ caracteres, `ADMIN_USERNAME`, `ADMIN_PASSWORD_HASH`, conexión MySQL.
- Generar hash: `python -c "from werkzeug.security import generate_password_hash; import getpass; print(generate_password_hash(getpass.getpass()))"`.
- Ejecutar detrás de proxy HTTPS/TLS con Gunicorn. Después de confirmar TLS, definir `CAPSTONE_FORCE_HTTPS=1`; no confiar en encabezados de proxy de orígenes no controlados.
- Usar una cuenta MySQL de mínimo privilegio; programar copias de seguridad. El proyecto **no incluye** un proveedor de hosting/certificado ni un despliegue productivo ya acreditado.
- La interfaz HTML exige login solo cuando `APP_ENV=production`; el modo development se reserva para uso local confiable.

## Registro UAT (completar con evidencias reales)

| Caso | Perfil | Resultado esperado | Estado actual | Evidencia requerida |
| --- | --- | --- | --- | --- |
| UAT-01 | Almacén | Consultas de los 25 casos INS-01 | Pendiente con usuario | Acta y ficha de respuestas |
| UAT-02 | Supervisor | Alertas y semáforo coherentes con MySQL | Pendiente con usuario | Capturas y datos de origen |
| UAT-03 | Supervisor | Registro e historial persistentes | Pendiente con MySQL | ID, fecha y lectura posterior |
| UAT-04 | Administrador | Seguridad de sesión y permisos | Pendiente en servidor HTTPS | Registro de accesos y checklist |

No se inventan actas, resultados PRE/POS ni firmas de usuarios.
