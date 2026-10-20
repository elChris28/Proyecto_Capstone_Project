# T2 — Sprint 2 con enfoque DevOps (guía de ejecución y evidencias)

## Alcance tomado del informe PC09

- **Periodo documentado:** 24/09/2026 – 21/10/2026 (sección 6.1.5).
- **Objetivo:** preparar los datos y entregar el dataset preparado.
- **Backlog:** PB05 (validar dataset histórico y stock actual, 5 SP); PB06 (limpiar y transformar datos, 8 SP); PB07 (variables 7/14/30 días, cobertura, tendencia y lead time, 8 SP); **21 SP planificados**, no equivale a 21 SP aceptados.
- **Herramientas del proyecto:** Python, Flask, Git/GitHub, pytest, datasets y modelos almacenados.

## Implementación añadida, sin modificar la inferencia ni reentrenar el modelo

1. `scripts/qa/sprint2_data_quality.py`: controles reproducibles de la estructura, duplicados, faltantes, valores y correspondencia entre histórico/inventario/variables (PB05-PB07). No edita archivos.
2. `tests/test_sprint2_data_quality.py`: cuatro escenarios nuevos para verificar que el control aprueba datos correctos y detecta datos erróneos.
3. `.github/workflows/sprint2-ci.yml`: automatización con GitHub Actions. En cada push/PR permitido ejecuta instalación, sintaxis, pruebas `pytest`, auditoría PB05-PB07 y verificación offline; guarda reportes como artefactos.
4. `scripts/devops/stage_release.py`: prepara versiones inmutables en `releases/<versión>`, prueba `/health` desde esa copia y actualiza `CURRENT.json` solo cuando el chequeo es correcto. El flujo principal de GitHub ejecuta esa fase después de pasar calidad.
5. `.env.example` e inclusión de `build/` en `.gitignore`: ejemplo no sensible y prevención de publicación accidental de secretos.

## Evidencia local verificada en el entorno de preparación

Se ejecutaron `python -m pytest -q tests/test_sprint2_data_quality.py` y la auditoría real de los tres CSV del ZIP enviado. Consultar `build/reports/sprint2_datos.json` para las cifras registradas. Las pruebas de toda la suite Flask **no pudieron ejecutarse en este entorno** porque faltan Flask y MySQL Connector; el flujo de GitHub las ejecutará cuando se publique y se instalen dependencias.

## Qué hacer en Visual Studio Code (Windows)

1. Crear una rama de trabajo `feature/sprint2-devops` desde el repositorio clonado, o copiar estos nuevos archivos a tu clon actual. No sobreescribir modificaciones ajenas del equipo.
2. Verificar con `git status` que `.env` **no** aparezca como archivo que se añadirá. Nunca utilizar `git add -f .env` ni publicar datos de conexión.
3. Abrir la terminal en la raíz e instalar dependencias:

   ```powershell
   python -m pip install -r requirements-dev.txt
   ```

4. Ejecutar pruebas y auditorías:

   ```powershell
   python -m pytest -q tests
   python -m scripts.qa.sprint2_data_quality --output build/reports/sprint2_datos.json
   python -m scripts.qa.verify_offline --output build/reports/verificacion_offline.json
   ```

5. Comprobar el staging local:

   ```powershell
   python -m scripts.devops.stage_release --target build/staging --release-id sprint2-local-001
   ```

   Evidencia: `build/staging/CURRENT.json` y salida `health: OK`. **Este staging es local**, no un despliegue público HTTPS.
6. Guardar los cambios y subir la rama mediante Git/VS Code:

   ```powershell
   git status
   git add .github/workflows/sprint2-ci.yml scripts/qa/sprint2_data_quality.py tests/test_sprint2_data_quality.py scripts/devops .env.example .gitignore docs/T2_SPRINT2_DEVOPS.md
   git commit -m "ci: pipeline y validacion de datos Sprint 2"
   git push -u origin feature/sprint2-devops
   ```

7. Crear Pull Request en GitHub a `develop` o `main`, según la estrategia de ramas autorizada. Revisar pestaña **Actions**. Para que corra `staging_incremental`, el código debe quedar integrado a `main` después de revisión.
8. Capturas para el T2: (a) historial de commit/PR; (b) archivo workflow; (c) ejecución Actions con todas las etapas en verde; (d) salida de auditoría y 21 SP planificados, **sin confundirlos con finalizados**; (e) artefacto de staging y resultado `/health`.

## Alcance y límites a declarar en el informe

- **CI local preparable ≠ CI de GitHub ejecutada.** Hasta que el workflow corra en la pestaña Actions no debe informarse como éxito remoto.
- **Staging efímero ≠ despliegue de producción.** El runner no mantiene un servidor accesible al usuario; publicar un servicio con HTTPS, roles y MySQL operativo requiere infraestructura aprobada.
- **Validación de datos ≠ limpieza efectuada en esta iteración.** El conjunto actual ya trae archivos preparados; el script certifica integridad y completitud, no modifica el proceso histórico de preparación.
- **Pruebas de componentes ≠ UAT/PRE/POS.** El informe PC09 mantiene pendientes la aceptación de usuarios y las mediciones de impacto.
- El ZIP original incluía un archivo `.env`; el ZIP ajustado **lo excluye** deliberadamente. Cambiar credenciales si estas fueron expuestas anteriormente.
