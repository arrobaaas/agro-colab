# Documentación de Agro-Colab

| Carpeta | Qué contiene |
|---|---|
| [`informes/`](informes) | **[Informe final · Hitos 2 y 3](informes/Informe_Final_Hitos_2_y_3.pdf)**, la [propuesta del Hito 1](informes/Informe_Hito1_Propuesta.pdf) y la [bitácora de decisiones](informes/BITACORA.md). En `informes/fuente/` está el HTML del informe y el script que genera el PDF |
| [`presentaciones/`](presentaciones) | Láminas del [Hito 1](presentaciones/Presentacion_Hito1.pdf) y del [Hito 2](presentaciones/Presentacion_Hito2.pdf), en PDF y PowerPoint |
| [`api/`](api) | [Contrato de la API](api/API.md) y [colección de Postman](api/AgroColab.postman_collection.json) con las peticiones de la demostración |
| [`guias/`](guias) | [Manual de uso e instalación](guias/MANUAL.md), [respuesta a incidentes](guias/INCIDENTES.md) y [guion del video](guias/GUION_VIDEO.md) |
| [`diagramas/`](diagramas) | [Arquitectura final](diagramas/arquitectura.png) y su fuente SVG. El modelo de datos está en [`db/`](../db) |
| [`capturas/`](capturas) | Capturas del producto en ejecución, usadas en el informe |

## Regenerar el informe

```bash
node docs/informes/fuente/generar_informe.mjs
```

Necesita Node 18 o superior, Google Chrome o Chromium y `poppler-utils` (`pdftotext`, `pdfunite`
y `pdfinfo`). Las tipografías (Inter y JetBrains Mono, licencia SIL OFL) vienen en
`informes/fuente/tipografias/`, así que no hace falta conexión.
