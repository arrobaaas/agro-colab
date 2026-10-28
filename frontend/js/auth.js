/* Agro-Colab - Servicio de sesión del usuario (persistencia en localStorage).
   Este servicio solo guarda y lee datos: no navega, eso es tarea de views.js */

var AgroColab = window.AgroColab || {};

class AuthService {
  constructor() {
    this.config = window.AgroColab.config;
    this.claveSesion = this.config.CLAVE_SESION;
    this.clavePlan = this.config.CLAVE_PLAN;
  }

  guardarSesion(usuario) {
    const sesion = {
      id: usuario.id,
      nombre: usuario.nombre,
      email: usuario.email,
      rol: usuario.rol,
      loginEn: new Date().toISOString()
    };
    localStorage.setItem(this.claveSesion, JSON.stringify(sesion));
    return sesion;
  }

  leerSesion() {
    try {
      const raw = localStorage.getItem(this.claveSesion);
      return raw ? JSON.parse(raw) : null;
    } catch (error) {
      return null;
    }
  }

  eliminarSesion() {
    localStorage.removeItem(this.claveSesion);
  }

  guardarPlan(plan) {
    localStorage.setItem(this.clavePlan, JSON.stringify(plan));
  }

  leerPlan() {
    try {
      const raw = localStorage.getItem(this.clavePlan);
      return raw ? JSON.parse(raw) : null;
    } catch (error) {
      return null;
    }
  }
}

const authService = new AuthService();
window.AgroColab.auth = authService;
