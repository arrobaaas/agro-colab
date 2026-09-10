# Agro-Colab 🌳

> **Proyecto Semestral - INGT1003 Arquitectura de Desarrollo (Móvil y Web)**  
> *Plataforma de Adopción de Árboles Frutales*

## 📖 Resumen del Proyecto
Agro-Colab es una plataforma web innovadora que conecta a las personas con la agricultura a través de un modelo de "adopción de árboles frutales". El sistema permite a los clientes financiar y ser dueños de la producción de un árbol mediante suscripciones, acercando el campo a la ciudad, promoviendo la trazabilidad agrícola y entregando un modelo de financiamiento directo a los agricultores.

### 🪴 Planes de Suscripción
El modelo de negocio se basa en tres niveles de adopción, diseñados para adaptarse a distintos presupuestos y necesidades:
1. **Plan Básico:** El usuario comparte el árbol y su producción de temporada con 5 personas.
2. **Plan Intermedio:** El usuario comparte el árbol y su producción con 3 personas.
3. **Plan Premium:** El usuario es dueño exclusivo del 100% de lo que produzca el árbol en la temporada.

## 🏗️ Arquitectura del Sistema
Siguiendo los lineamientos del curso (Unidad 1), el proyecto se estructura bajo un **Modelo Cliente-Servidor** y una **Arquitectura de 3 Capas**:

*   **Capa de Presentación (Frontend):** Interfaz responsive (Mobile-first) enfocada en la experiencia del usuario (UI/UX), construida con HTML5, CSS3 y JavaScript.
*   **Capa de Negocio (Backend):** API REST que maneja la lógica de las suscripciones, el control de stock (cuántos cupos le quedan a un árbol) y la validación de usuarios, utilizando el patrón **MVC** (Modelo-Vista-Controlador).
*   **Capa de Datos:** Base de datos relacional responsable de la persistencia de usuarios, catálogo de árboles, suscripciones y transacciones.

## 🚀 Funcionalidades Principales
*   **Catálogo Interactivo:** Exploración de árboles frutales disponibles (filtrado por tipo de fruta, temporada y agricultor).
*   **Flujo de Suscripción:** Proceso de selección de planes (Básico, Intermedio, Premium) y pasarela de pago simulada.
*   **Dashboard de Usuario:** Panel privado para monitorear el estado del árbol adoptado, el avance de la cosecha y la gestión de la suscripción.
*   **Gestión de Agricultores:** (Proyección) Interfaz para que los productores publiquen sus árboles y actualicen el estado de crecimiento.

## 📂 Estructura del Proyecto
```text
agro-colab/
├── frontend/             # Archivos de la interfaz cliente (HTML, CSS, JS)
│   ├── css/              # Estilos separados
│   ├── js/               # Scripts y consumo de API (fetch)
│   └── img/              # Medios optimizados (WebP/AVIF)
├── backend/              # Lógica del servidor, API y controladores MVC
├── docs/                 # Documentación del proyecto (Propuesta, Wireframes)
└── README.md
```

## 🧑‍💻 Equipo de Desarrollo
*   *Joaquin Alveal Santos*
*   *Matias Gonzalez* 
*   *Nicolas Reyes Orellana* 
