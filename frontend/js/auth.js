/* Agro-Colab - Sesión del usuario (persistencia en localStorage).
   Este módulo solo guarda y lee datos: no navega, eso es tarea de views.js */

(function () {
  const AgroColab = (window.AgroColab = window.AgroColab || {});
  const { CLAVE_SESION, CLAVE_PLAN } = AgroColab.config;

  function guardarSesion(usuario) {
    const sesion = {
      nombre: usuario.nombre,
      email: usuario.email,
      rol: usuario.rol,
      loginEn: new Date().toISOString()
    };
    localStorage.setItem(CLAVE_SESION, JSON.stringify(sesion));
    return sesion;
  }

  function leerSesion() {
    try {
      const raw = localStorage.getItem(CLAVE_SESION);
      return raw ? JSON.parse(raw) : null;
    } catch (error) {
      return null;
    }
  }

  function eliminarSesion() {
    localStorage.removeItem(CLAVE_SESION);
  }

  function guardarPlan(plan) {
    localStorage.setItem(CLAVE_PLAN, JSON.stringify(plan));
  }

  function leerPlan() {
    try {
      const raw = localStorage.getItem(CLAVE_PLAN);
      return raw ? JSON.parse(raw) : null;
    } catch (error) {
      return null;
    }
  }

  AgroColab.auth = { guardarSesion, leerSesion, eliminarSesion, guardarPlan, leerPlan };
})();
