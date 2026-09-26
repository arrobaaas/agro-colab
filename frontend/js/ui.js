/* Agro-Colab - Helpers de interfaz (alertas y estado visual) */

(function () {
  const AgroColab = (window.AgroColab = window.AgroColab || {});

  const CLASES_ALERTA = {
    exito: "alerta alerta--exito",
    error: "alerta alerta--error",
    info: "alerta alerta--info",
    exitoGrande: "alerta alerta--exito-lg",
    errorGrande: "alerta alerta--error-lg",
    infoGrande: "alerta alerta--info-lg"
  };

  function mostrarAlerta(elemento, tipo, mensaje) {
    if (!elemento) return;
    elemento.className = CLASES_ALERTA[tipo] || CLASES_ALERTA.info;
    elemento.classList.remove("hidden");
    elemento.textContent = mensaje;
  }

  function ocultarAlerta(elemento) {
    if (!elemento) return;
    elemento.classList.add("hidden");
    elemento.textContent = "";
  }

  function marcarRol(botonActivo, botonInactivo) {
    botonActivo.className = "rol-btn rol-btn--activo";
    botonInactivo.className = "rol-btn rol-btn--inactivo";
  }

  function formatearMonto(monto) {
    return `$${Number(monto).toLocaleString("es-CL")}`;
  }

  AgroColab.ui = { mostrarAlerta, ocultarAlerta, marcarRol, formatearMonto };
})();
