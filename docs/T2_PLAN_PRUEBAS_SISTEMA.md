# T2 – verificación del funcionamiento de VetAssistant IA

## Alcance del PC09

- 62 requisitos funcionales RF-01 a RF-62 y 14 requisitos no funcionales RNF-01 a RNF-14.
- El requisito de 100 % funcional de la rúbrica exige comprobar **el alcance aprobado**, no solo que Pytest termine sin errores.
- Las pruebas HTTP añadidas usan Flask test_client y dobles de servicios; no reemplazan la comprobación con MySQL, el navegador y la operación real.
- Las pruebas con jefe de almacén (UAT) se mantienen pendientes.

## Ejecución recomendada

```powershell
python -m pip install -r requirements-dev.txt
python -m pytest -q tests
python -m pytest -v tests/test_sistema_t2_controlado.py
python main.py
```

Capturar el resumen de Pytest y luego el resultado de cada MF-01 a MF-16; anotar fecha, operador, datos de entrada, esperado, obtenido, evidencia y estado.

## Casos HTTP preparados (sin ejecución acreditada en el entorno de preparación)

- **ST-01** – Inicio de aplicación y navegación (Asistente)
- **ST-02** – Consulta textual y respuesta (Asistente)
- **ST-03** – Historial de sesión y limpiar chat (Asistente)
- **ST-04** – Dashboard con indicadores y críticos (Dashboard)
- **ST-05** – Pantalla de predicción y prioridades (Predicción)
- **ST-06** – API de predicción a siete días (Predicción)
- **ST-07** – Rechazo del horizonte incorrecto (Predicción)
- **ST-08** – Detalle existente y producto no encontrado (Predicción)
- **ST-09** – API de alertas (Alertas)
- **ST-10** – Registro explícito sin guardar al consultar (Predicción)
- **ST-11** – Respuesta ante error de registro (Predicción)
- **ST-12** – Panel y API de calidad de datos (Control de datos)
- **ST-13** – Endpoint de salud y cabeceras HTTP (Seguridad)

## Recorrido manual (requerido para validar 100 % funcional)

- [ ] **MF-01** – Asistente: Ingresar «¿Cuál es el stock disponible de P001?»; contrastar con MySQL. **Criterios:** RF-01, RF-02, RF-10, RF-12, RF-21. **Esperado:** Respuesta y registro correctos.
- [ ] **MF-02** – Asistente: Consultar ubicación real del producto P001. **Criterios:** RF-13. **Esperado:** Ubicación coincide con base de datos.
- [ ] **MF-03** – Asistente: Consultar lotes, vencimientos y días restantes de un producto que tenga lotes. **Criterios:** RF-14 a RF-16. **Esperado:** Detalle corresponde a registros reales.
- [ ] **MF-04** – Asistente: Solicitar productos críticos y próximos a vencer. **Criterios:** RF-17 a RF-20. **Esperado:** Listados coinciden con el inventario.
- [ ] **MF-05** – Asistente: Consultar dos intenciones en una pregunta y luego pregunta de seguimiento. **Criterios:** RF-09, RF-11. **Esperado:** Retiene contexto y responde a ambas consultas.
- [ ] **MF-06** – Asistente: Probar entrada no reconocida, sugerencias y botón Limpiar chat. **Criterios:** RF-04, RF-07, RF-08. **Esperado:** Mensaje adecuado, sugerencias y sesión limpia.
- [ ] **MF-07** – Asistente: Probar accesos rápidos y dictado por voz en navegador compatible. **Criterios:** RF-22, RF-23. **Esperado:** Accesos funcionan y se registra limitación del navegador.
- [ ] **MF-08** – Predicción: Abrir Predicción 7 días y validar variables, modelo, totales y semáforo. **Criterios:** RF-24, RF-28 a RF-34, RF-39, RF-40. **Esperado:** Los totales concuerdan y el horizonte es 7 días.
- [ ] **MF-09** – Predicción: Consultar detalle de producto existente y de producto sin historial. **Criterios:** RF-25 a RF-27, RF-53, RF-54. **Esperado:** Detalle o error explicativo correcto.
- [ ] **MF-10** – Predicción: Utilizar búsqueda, filtros ALTO/MEDIO/BAJO/categoría y «Ver análisis». **Criterios:** RF-35 a RF-38. **Esperado:** Filtros y detalles corresponden a la selección.
- [ ] **MF-11** – Predicción: Registrar evaluación, consultar últimas seis y recargar vista. **Criterios:** RF-41 a RF-45. **Esperado:** Un solo registro explícito; sin duplicados por consulta.
- [ ] **MF-12** – Alertas: Abrir campana y cotejar alto/medio/bajo y Top 5 con predicción. **Criterios:** RF-46 a RF-49. **Esperado:** Cantidades y productos coinciden sin crear historial.
- [ ] **MF-13** – API: Consultar tres endpoints (alertas, predicciones 7d y detalle) y horizonte 14 días. **Criterios:** RF-50 a RF-54. **Esperado:** HTTP y contenido adecuados; 14 días rechazado.
- [ ] **MF-14** – Dashboard: Revisar métricas NLP, totales por intención y producto más consultado. **Criterios:** RF-55 a RF-59. **Esperado:** Datos coinciden con registros en MySQL.
- [ ] **MF-15** – Dashboard: Verificar alertas logísticas, tabla críticos y próximos a vencer. **Criterios:** RF-60 a RF-62. **Esperado:** Datos concuerdan con consultas reales.
- [ ] **MF-16** – Calidad y seguridad: Abrir /calidad-datos, /health y revisar acceso en entorno de demostración. **Criterios:** RNF-01 a RNF-14. **Esperado:** Panel y requisitos de entorno comprobados.

## Estados

- Todo caso manual: pendiente de ejecución y registro de evidencias.
- Integración con base de datos real: por verificar.
- Pruebas de aceptación: pendiente de disponibilidad del usuario representante.
- No registrar porcentajes de cumplimiento ni firmas sin ejecución real.
