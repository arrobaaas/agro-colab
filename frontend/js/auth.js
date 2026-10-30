/* Agro-Colab - Servicio de sesión del usuario, de su canasta y del plan elegido.
   Este servicio solo guarda y lee datos: no navega, eso es tarea de views.js

   La sesión y la canasta se guardan en sessionStorage: duran mientras la
   pestaña esté abierta (sobreviven a ir a Privacidad o Términos y volver, o a
   recargar), y se borran solas al cerrar la pestaña o el navegador. Así cada
   visita nueva parte en el login, sin que la sesión quede guardada a largo
   plazo como pasaba con localStorage. */

var AgroColab = window.AgroColab || {};

class AuthService {
  constructor() {
    this.config = window.AgroColab.config;
    this.claveSesion = this.config.claveSesion;
    this.clavePlan = this.config.clavePlan;
    this.claveCarrito = this.config.claveCarrito;
    this.claveVista = this.config.claveVista;
    this.sesion = null;
  }

  /* sessionStorage puede no estar disponible (modo privado estricto): en ese
     caso la sesión sigue funcionando en memoria */
  guardarEnPestana(clave, valor) {
    try {
      sessionStorage.setItem(clave, JSON.stringify(valor));
    } catch (error) { /* solo en memoria */ }
  }

  leerDePestana(clave) {
    try {
      const raw = sessionStorage.getItem(clave);
      return raw ? JSON.parse(raw) : null;
    } catch (error) {
      return null;
    }
  }

  guardarSesion(usuario) {
    // Al actualizar el perfil el backend no reenvía el token: se conserva el
    // de la sesión actual para no cerrarla
    const anterior = this.leerSesion();
    this.sesion = {
      id: usuario.id,
      nombre: usuario.nombre,
      email: usuario.email,
      rol: usuario.rol,
      token: usuario.token || (anterior && anterior.id === usuario.id ? anterior.token : null),
      loginEn: new Date().toISOString()
    };
    this.guardarEnPestana(this.claveSesion, this.sesion);
    return this.sesion;
  }

  leerSesion() {
    if (!this.sesion) this.sesion = this.leerDePestana(this.claveSesion);
    return this.sesion || null;
  }

  /* Al cerrar sesión se borra también la canasta: si no, la siguiente
     persona que entrara en el mismo navegador vería la del usuario anterior */
  eliminarSesion() {
    this.sesion = null;
    try {
      sessionStorage.removeItem(this.claveSesion);
      sessionStorage.removeItem(this.claveCarrito);
      sessionStorage.removeItem(this.claveVista);
    } catch (error) { /* almacenamiento no disponible */ }
    this.limpiarSesionAntigua();
  }

  /* Las versiones anteriores guardaban la sesión en localStorage, donde
     quedaba indefinidamente: se borra si existe */
  limpiarSesionAntigua() {
    try {
      localStorage.removeItem(this.claveSesion);
    } catch (error) { /* almacenamiento no disponible */ }
  }

  /* Última vista abierta: al volver de Privacidad o Términos se regresa a
     ella (por ejemplo, al panel) y no siempre al catálogo */
  guardarVista(nombre) {
    this.guardarEnPestana(this.claveVista, nombre);
  }

  leerVista() {
    return this.leerDePestana(this.claveVista);
  }

  guardarCarrito(items) {
    this.guardarEnPestana(this.claveCarrito, items);
  }

  leerCarrito() {
    const items = this.leerDePestana(this.claveCarrito);
    return Array.isArray(items) ? items : [];
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
