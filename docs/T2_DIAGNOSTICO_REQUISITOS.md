# T2 — Diagnóstico respecto del informe PC09 y el ZIP actualizado

Fuente principal: `Capstone_Project_Informe_PC09.docx`, secciones 5.14, 6.1.5, 6.3, 6.5, 6.9.3.1, 6.9.4, 6.10, 6.13; comprobación del ZIP aportado por el equipo.

| Exigencia T2 | Referente específico PC09 | Evidencia verificable / pendiente |
|---|---|---|
| Sprint 2 DevOps | 6.1.5: 24/09 a 21/10, preparar los datos. Product Backlog PB05-07: 5+8+8=21 SP | En ZIP: tres CSV y procesamiento existente. AÑADIDO: auditoría reproducible, workflow GitHub, paquete versionado staging. PENDIENTE: ejecutar workflow real en repositorio remoto y documentar PR/merge. |
| Mediciones control de calidad | 5.14 matriz de calidad; 6.9.3.1 registra 26 pruebas Pytest aprobadas el 18/10/2026; 6.9.1 Recall 81.48% y F1 79.18% | Añadida auditoría cuantitativa de los CSV. No atribuir a T2 nuevos resultados de suite completa no ejecutados. Performance, disponibilidad, UAT y PRE/POS requieren medición propia. |
| Calendario de recursos | 5.9 EDT y cronograma; 5.10 roles y presupuesto 360 horas y S/ 8,400; 6.2.1 cinco integrantes | Disponible la asignación de roles y fechas. Falta registro de horas reales, disponibilidad por recurso y fechas/tareas acordadas del Sprint 2. |
| Desarrollo de producto tecnológico profesional | 6.9 incremento funcional; 6.9.4 74/87 SP=85.1% propuestos y condicionados a aprobación | Software y modelos están en el ZIP. No confundir avance técnico propuesto con aceptación productiva. |
| Guía docente durante el desarrollo | El documento identifica docente y seguimiento Scrum; contiene observaciones técnicas y tareas | No consta por sí sola acta firmada ni cronograma completo de asesorías. Se requieren evidencias genuinas: fecha de reunión, indicación, responsable, levantamiento y validación. |
| Pruebas del producto | Informe PC09 indica 26 pruebas automatizadas y UAT pendiente. Entrega de pruebas unitarias e integración de KPI/subsistemas existió por separado. | Este ZIP NO incluye `tests/unit/test_kpi_por_subsistema.py` ni `tests/integration/test_cuatro_subsistemas.py` de la entrega anterior. Se debe decidir consolidar ambas suites en el repositorio. Faltan pruebas integrales del sistema con infraestructura apropiada y aceptación con usuarios. |

## Observaciones de trazabilidad

- El Sprint 2 **no consiste en reentrenar nuevos modelos** ni en implementar el sistema completo: la sección 6.1.5 restringe el entregable a dataset preparado; las actividades nuevas DevOps verifican y versionan la preparación de datos.
- La versión disponible del software puede estar adelantada respecto de la secuencia de sprints del informe. Documentar la diferencia como adelanto/versión y no modificar fechas retroactivamente.
- El ZIP original incluye `.env` y no trae `.env.example`, pese a que este último se menciona en el informe. En la copia preparada se excluyó `.env` y se añadió un ejemplo sin credenciales.
- No se han validado despliegue público HTTPS, conexión productiva MySQL, UAT ni PRE/POS.
