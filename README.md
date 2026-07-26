# 🤖 Asistente Inteligente de Inventarios con NLP

Un asistente conversacional desarrollado para optimizar la gestión de inventario en una veterinaria mediante **Procesamiento de Lenguaje Natural (NLP)**, **Machine Learning** y **reconocimiento de voz**.

El sistema permite consultar información del inventario utilizando lenguaje natural, facilitando la búsqueda de productos, control de stock, ubicación física y monitoreo de vencimientos desde una interfaz web.

---

# 📌 Objetivo

Desarrollar un asistente inteligente capaz de comprender consultas escritas o por voz sobre el inventario de una veterinaria, automatizando tareas de búsqueda y mejorando la eficiencia en la gestión logística.

---

# 🚀 Tecnologías utilizadas

### Backend
- Python
- Flask
- MySQL

### Inteligencia Artificial
- Scikit-Learn
- spaCy
- TF-IDF Vectorizer
- Multinomial Naive Bayes
- TheFuzz (Levenshtein)

### Frontend
- HTML5
- CSS3
- JavaScript
- Web Speech API

---

# 🧠 Arquitectura del sistema

```
Usuario
   │
Texto / Voz
   │
Web Speech API
   │
Flask
   │
NLP (spaCy)
   │
TF-IDF
   │
Naive Bayes
   │
Clasificación de intención
   │
MySQL
   │
Respuesta al usuario
```

---

# ⚙️ Funcionalidades

## 📦 Gestión de inventario

- Consulta de stock disponible
- Búsqueda de productos
- Localización dentro del almacén
- Información de lotes
- Control de fechas de vencimiento
- Alertas automáticas de stock bajo

---

## 🤖 Asistente Inteligente

El asistente comprende consultas escritas en lenguaje natural como:

> ¿Cuánto antibiótico queda?

> ¿Dónde está la Vitamina B12?

> ¿Qué productos vencen este mes?

> Muéstrame los productos con poco stock.

---

## 🎙️ Reconocimiento de voz

Gracias a **Web Speech API**, el sistema permite realizar consultas mediante comandos de voz, facilitando el uso manos libres en almacenes o entornos logísticos.

---

## 📊 Dashboard

Se desarrolló un panel interactivo con indicadores para el seguimiento del inventario.

Incluye:

- Productos con stock crítico
- Productos próximos a vencer
- Total de productos registrados
- Movimientos del inventario
- Indicadores de disponibilidad

---

# 🧠 Modelo de Machine Learning

Para interpretar las consultas del usuario se desarrolló un modelo de clasificación de intenciones basado en:

- TF-IDF Vectorizer
- Multinomial Naive Bayes
- Procesamiento de texto con spaCy

El modelo fue entrenado con múltiples ejemplos de consultas relacionadas con inventario.

## Resultados obtenidos

| Métrica | Valor |
|---------|--------|
| Accuracy | **88.3%** |
| Precision | Alta |
| Recall | Alto |
| F1-Score | Alto |

---

# 🔍 Búsqueda Inteligente

Se implementó búsqueda difusa utilizando **TheFuzz**, permitiendo encontrar productos incluso cuando existen errores ortográficos.

Ejemplo:

```
Amoxisilina
```

↓

```
Amoxicilina
```

Esto reduce significativamente los errores de escritura durante las consultas.

---

# 🗄️ Base de datos

El sistema utiliza MySQL como motor de base de datos para almacenar:

- Productos
- Categorías
- Lotes
- Stock
- Ubicaciones
- Fechas de vencimiento
- Historial de consultas

---

# 📈 Resultados del proyecto

✔ Modelo NLP con **88.3% de precisión**

✔ Clasificación automática de consultas

✔ Búsqueda inteligente tolerante a errores ortográficos

✔ Integración de reconocimiento de voz

✔ Dashboard para monitoreo del inventario

✔ Persistencia de información mediante MySQL

---

# 💡 Lo que aprendí

Este proyecto me permitió integrar diferentes áreas de la ciencia de datos y el desarrollo de software para construir un asistente conversacional aplicado a un problema real de logística.

Entre los principales aprendizajes destacan:

- Aplicación de Procesamiento de Lenguaje Natural (NLP) para comprender consultas de usuarios.
- Entrenamiento y evaluación de modelos de clasificación utilizando Naive Bayes y TF-IDF.
- Implementación de búsqueda difusa con distancia de Levenshtein para mejorar la experiencia del usuario.
- Desarrollo de APIs con Flask conectadas a una base de datos relacional.
- Integración de reconocimiento de voz mediante Web Speech API.
- Diseño de dashboards para visualizar indicadores clave de inventario.

---

# 📸 Capturas del proyecto

> Agrega aquí imágenes del chatbot, dashboard y funcionamiento del sistema.

| Chat Inteligente | Dashboard |
|-----------------|-----------|
| ![](images/chat.png) | ![](images/dashboard.png) |

---

# 👨‍💻 Autor

**Christofer J.**

Proyecto desarrollado como práctica de **Machine Learning, NLP, Desarrollo Web y Gestión Inteligente de Inventarios**, integrando Python, Flask, MySQL y Web Speech API para automatizar procesos logísticos.
