/* Agro-Colab - Servicio de interfaz (alertas y estado visual) */

var AgroColab = window.AgroColab || {};

class UiService {
  constructor() {
    this.clasesAlerta = {
      exito: "alerta alerta--exito",
      error: "alerta alerta--error",
      info: "alerta alerta--info",
      exitoGrande: "alerta alerta--exito-lg",
      errorGrande: "alerta alerta--error-lg",
      infoGrande: "alerta alerta--info-lg"
    };
  }

  mostrarAlerta(elemento, tipo, mensaje) {
    if (!elemento) return;
    elemento.className = this.clasesAlerta[tipo] || this.clasesAlerta.info;
    elemento.classList.remove("hidden");
    elemento.textContent = mensaje;
  }

  ocultarAlerta(elemento) {
    if (!elemento) return;
    elemento.classList.add("hidden");
    elemento.textContent = "";
  }

  marcarRol(botonActivo, botonInactivo) {
    botonActivo.className = "rol-btn rol-btn--activo";
    botonInactivo.className = "rol-btn rol-btn--inactivo";
  }

  formatearMonto(monto) {
    return `$${Number(monto).toLocaleString("es-CL")}`;
  }
}

const uiService = new UiService();
window.AgroColab.ui = uiService;
