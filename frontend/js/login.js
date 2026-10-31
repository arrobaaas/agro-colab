/* Agro-Colab - Servicio del formulario de acceso (vista de login).
   El login es lo primero que ve cualquier persona: si la sesión es válida
   la app salta directo a la vista del rol sin mostrar este formulario. */

class LoginService {
  constructor() {
    this.api = window.AgroColab.api;
    this.ui = window.AgroColab.ui;
    this.auth = window.AgroColab.auth;
    this.views = window.AgroColab.views;
    this.config = window.AgroColab.config;
    this.rolSeleccionado = "comprador";
    this.emailVerificacion = "";
    this.codigoVerificacion = "";
  }

  setRol(rol) {
    this.rolSeleccionado = rol;
    const btnComprador = document.getElementById("btn-comprador");
    const btnAgricultor = document.getElementById("btn-agricultor");

    if (rol === "comprador") {
      this.ui.marcarRol(btnComprador, btnAgricultor);
    } else {
      this.ui.marcarRol(btnAgricultor, btnComprador);
    }
    this.ui.ocultarAlerta(document.getElementById("alert-box"));
  }

  async iniciarSesion(evento) {
    if (evento) {
      evento.preventDefault();
      if (evento.stopPropagation) evento.stopPropagation();
    }

    const alertBox = document.getElementById("alert-box");
    const email = document.getElementById("email").value.trim();
    const password = document.getElementById("password").value;

    if (!email || !password) {
      this.ui.mostrarAlerta(alertBox, "error", "Completa tu correo y contraseña.");
      return;
    }

    this.ui.mostrarAlerta(alertBox, "info", "Verificando credenciales...");

    try {
      const data = await this.api.login(email, password, this.rolSeleccionado);

      if (data.status === "success") {
        // Verificar si la cuenta está verificada
        if (data.user.verificado === 0 || data.user.verificado === false) {
          this.auth.eliminarSesion();
          this.auth.guardarSesion(data.user);
          this.mostrarVerificacion(data.user.email, data.user.codigo_verificacion || "");
          return false;
        }

        this.auth.eliminarSesion();
        this.auth.guardarSesion(data.user);
        this.views.pintarNavbar();
        this.views.mostrarVistaPorRol(data.user.rol);
      } else {
        this.ui.mostrarAlerta(alertBox, "error", data.mensaje);
      }
    } catch (error) {
      this.ui.mostrarAlerta(
        alertBox,
        "error",
        error.message || `Error de conexión con el backend (${this.config.API_URL}). Revisa que Uvicorn esté activo.`
      );
    }
    return false;
  }

  alternarRegistro() {
    const loginForm = document.getElementById("login-form");
    const registerForm = document.getElementById("register-form");
    const btnAlternar = document.getElementById("btn-alternar");
    const titulo = document.getElementById("login-titulo");
    const subtitulo = document.getElementById("login-subtitulo");

    if (loginForm.classList.contains("hidden")) {
      loginForm.classList.remove("hidden");
      registerForm.classList.add("hidden");
      titulo.textContent = "Iniciar sesión";
      subtitulo.textContent = "Ingresa a tu panel de gestión colaborativa";
      btnAlternar.textContent = "¿No tienes cuenta? Regístrate";
    } else {
      loginForm.classList.add("hidden");
      registerForm.classList.remove("hidden");
      titulo.textContent = "Crear cuenta";
      subtitulo.textContent = "Regístrate para comenzar a adoptar árboles";
      btnAlternar.textContent = "¿Ya tienes cuenta? Inicia sesión";
    }
  }

  async registrarUsuario(evento) {
    if (evento) {
      evento.preventDefault();
      if (evento.stopPropagation) evento.stopPropagation();
    }

    const alerta = document.getElementById("alerta-registro");
    const nombre = document.getElementById("reg-nombre").value.trim();
    const email = document.getElementById("reg-email").value.trim();
    const password = document.getElementById("reg-password").value;
    const telefono = document.getElementById("reg-telefono").value.trim();
    const direccion = document.getElementById("reg-direccion").value.trim();

    if (!nombre || !email || !password) {
      this.ui.mostrarAlerta(alerta, "error", "Completa nombre, correo y contraseña.");
      return false;
    }

    this.ui.mostrarAlerta(alerta, "info", "Creando tu cuenta...");

    try {
      const data = await this.api.registrarUsuario({
        nombre,
        email,
        password,
        rol: this.rolSeleccionado,
        telefono: telefono || null,
        direccion: direccion || null
      });

      if (data.status === "success") {
        // Sin guardar sesión: la cuenta aún no está verificada ni tiene token
        this.ui.mostrarAlerta(alerta, "exito", data.mensaje);
        this.mostrarVerificacion(data.user.email, data.user.codigo_verificacion);
      } else {
        this.ui.mostrarAlerta(alerta, "error", data.mensaje);
      }
    } catch (error) {
      this.ui.mostrarAlerta(alerta, "error", error.message || "Error de comunicación con el backend.");
    }
    return false;
  }

  mostrarVerificacion(email, codigo) {
    this.emailVerificacion = email;
    this.codigoVerificacion = codigo;
    // El recuadro con el código solo existe en desarrollo (sin correo real)
    document.getElementById("codigo-simulado").textContent = codigo || "";
    document.getElementById("bloque-codigo-simulado").classList.toggle("hidden", !codigo);
    document.getElementById("modal-verificacion").classList.remove("hidden");
  }

  cerrarVerificacion() {
    document.getElementById("modal-verificacion").classList.add("hidden");
  }

  async verificarCuenta(evento) {
    if (evento) {
      evento.preventDefault();
      if (evento.stopPropagation) evento.stopPropagation();
    }

    const alerta = document.getElementById("alerta-verificacion");
    const codigo = document.getElementById("codigo-verificacion").value.trim();

    if (!codigo || codigo.length !== 6) {
      this.ui.mostrarAlerta(alerta, "error", "Ingresa el código de 6 dígitos.");
      return false;
    }

    this.ui.mostrarAlerta(alerta, "info", "Verificando tu cuenta...");

    try {
      const data = await this.api.verificarCuenta(this.emailVerificacion, codigo);

      if (data.status === "success") {
        this.ui.mostrarAlerta(alerta, "exito", data.mensaje);
        const usuario = data.user;
        setTimeout(() => {
          this.cerrarVerificacion();
          // Con la sesión que entrega el servidor se entra directo a la cuenta
          if (usuario && usuario.token) {
            // Al cerrar sesión no deben quedar a la vista la contraseña ni el código
            document.getElementById("register-form").reset();
            document.getElementById("form-verificacion").reset();
            this.ui.ocultarAlerta(document.getElementById("alerta-registro"));
            this.ui.ocultarAlerta(alerta);
            this.auth.eliminarSesion();
            this.auth.guardarSesion(usuario);
            this.views.pintarNavbar();
            this.views.mostrarVistaPorRol(usuario.rol);
          } else {
            AgroColab.dialogo.avisar("Ya puedes iniciar sesión con tu correo y contraseña.", { tipo: "exito", titulo: "Cuenta verificada" });
          }
        }, 1200);
      } else {
        this.ui.mostrarAlerta(alerta, "error", data.mensaje);
      }
    } catch (error) {
      this.ui.mostrarAlerta(alerta, "error", error.message || "Error de comunicación con el backend.");
    }
    return false;
  }

  async reenviarCodigo() {
    if (!this.emailVerificacion) return;
    const alerta = document.getElementById("alerta-verificacion");

    try {
      const data = await this.api.reenviarCodigo(this.emailVerificacion);
      this.ui.mostrarAlerta(alerta, data.status === "success" ? "info" : "error", data.mensaje);
      if (data.codigo_verificacion) {
        document.getElementById("codigo-simulado").textContent = data.codigo_verificacion;
      }
    } catch (error) {
      this.ui.mostrarAlerta(alerta, "error", "No se pudo reenviar el código.");
    }
  }

  togglePassword(inputId, btn) {
    const input = document.getElementById(inputId);
    const icon = btn.querySelector("i");
    if (input.type === "password") {
      input.type = "text";
      icon.classList.remove("fa-eye");
      icon.classList.add("fa-eye-slash");
    } else {
      input.type = "password";
      icon.classList.remove("fa-eye-slash");
      icon.classList.add("fa-eye");
    }
  }

  init() {
    document.getElementById("login-form").addEventListener("submit", (evento) => this.iniciarSesion(evento));
    document.getElementById("register-form").addEventListener("submit", (evento) => this.registrarUsuario(evento));
    document.getElementById("form-verificacion").addEventListener("submit", (evento) => this.verificarCuenta(evento));
    document.getElementById("btn-alternar").addEventListener("click", () => this.alternarRegistro());
    this.setRol("comprador");
  }
}

const loginService = new LoginService();
window.AgroColab.login = loginService;
