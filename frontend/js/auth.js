/* Agro-Colab - Servicio de sesión del usuario (en memoria) y del plan elegido.
   Este servicio solo guarda y lee datos: no navega, eso es tarea de views.js */

var AgroColab = window.AgroColab || {};

class AuthService {
  constructor() {
    this.config = window.AgroColab.config;
    this.claveSesion = this.config.claveSesion;
    this.clavePlan = this.config.clavePlan;
    this.sesion = null;
  }

  /* La sesión (con su token) vive solo en memoria: no se guarda en
     localStorage, donde cualquier script o extensión podía leerla después.
     Como cada visita parte en el login, no hace falta persistirla. */
  guardarSesion(usuario) {
    // Al actualizar el perfil el backend no reenvía el token: se conserva el
    // de la sesión actual para no cerrarla
    const anterior = this.sesion;
    this.sesion = {
      id: usuario.id,
      nombre: usuario.nombre,
      email: usuario.email,
      rol: usuario.rol,
      token: usuario.token || (anterior && anterior.id === usuario.id ? anterior.token : null),
      loginEn: new Date().toISOString()
    };
    return this.sesion;
  }

  leerSesion() {
    return this.sesion || null;
  }

  eliminarSesion() {
    this.sesion = null;
    // Borra la sesión que guardaban las versiones anteriores
    try {
      localStorage.removeItem(this.claveSesion);
    } catch (error) { /* almacenamiento no disponible */ }
  }

  guardarPlan(plan) {
    try {
      localStorage.setItem(this.clavePlan, JSON.stringify(plan));
    } catch (error) { /* almacenamiento no disponible */ }
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
