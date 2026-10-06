/* Agro-Colab - Formulario de acceso (vista de login).
   El login es lo primero que ve cualquier persona: si la sesión es válida
   la app salta directo a la vista del rol sin mostrar este formulario. */

(function () {
  const AgroColab = (window.AgroColab = window.AgroColab || {});
  const { api, ui, auth, views, config } = AgroColab;

  let rolSeleccionado = "comprador";

  function setRol(rol) {
    rolSeleccionado = rol;
    const btnComprador = document.getElementById("btn-comprador");
    const btnAgricultor = document.getElementById("btn-agricultor");

    if (rol === "comprador") {
      ui.marcarRol(btnComprador, btnAgricultor);
    } else {
      ui.marcarRol(btnAgricultor, btnComprador);
    }
    ui.ocultarAlerta(document.getElementById("alert-box"));
  }

  async function iniciarSesion(evento) {
    if (evento) {
      evento.preventDefault();
      if (evento.stopPropagation) evento.stopPropagation();
    }

    const alertBox = document.getElementById("alert-box");
    const email = document.getElementById("email").value.trim();
    const password = document.getElementById("password").value;

    if (!email || !password) {
      ui.mostrarAlerta(alertBox, "error", "Completa tu correo y contraseña.");
      return;
    }

    ui.mostrarAlerta(alertBox, "info", "Verificando credenciales...");

    try {
      const data = await api.login(email, password, rolSeleccionado);

      if (data.status === "success") {
        // Verificar si la cuenta está verificada
        if (data.user.verificado === 0 || data.user.verificado === false) {
          auth.eliminarSesion();
          auth.guardarSesion(data.user);
          mostrarVerificacion(data.user.email, data.user.codigo_verificacion || "");
          return false;
        }

        auth.eliminarSesion();
        auth.guardarSesion(data.user);
        views.pintarNavbar();
        views.mostrarVistaPorRol(data.user.rol);
      } else {
        ui.mostrarAlerta(alertBox, "error", data.mensaje);
      }
    } catch (error) {
      ui.mostrarAlerta(
        alertBox,
        "error",
        `Error de conexión con el backend (${config.API_URL}). Revisa que Uvicorn esté activo.`
      );
    }
    return false;
  }

  function alternarRegistro() {
    const loginForm = document.getElementById("login-form");
    const registerForm = document.getElementById("register-form");
    const btnAlternar = document.getElementById("btn-alternar");
    const titulo = document.getElementById("login-titulo");
    const subtitulo = document.getElementById("login-subtitulo");

    if (loginForm.classList.contains("hidden")) {
      loginForm.classList.remove("hidden");
      registerForm.classList.add("hidden");
      titulo.textContent = "Iniciar Sesión";
      subtitulo.textContent = "Ingresa a tu panel de gestión colaborativa";
      btnAlternar.textContent = "¿No tienes cuenta? Regístrate";
    } else {
      loginForm.classList.add("hidden");
      registerForm.classList.remove("hidden");
      titulo.textContent = "Crear Cuenta";
      subtitulo.textContent = "Regístrate para comenzar a adoptar árboles";
      btnAlternar.textContent = "¿Ya tienes cuenta? Inicia sesión";
    }
  }

  async function registrarUsuario(evento) {
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
      ui.mostrarAlerta(alerta, "error", "Completa nombre, correo y contraseña.");
      return false;
    }

    ui.mostrarAlerta(alerta, "info", "Creando tu cuenta...");

    try {
      const data = await api.registrarUsuario({
        nombre,
        email,
        password,
        rol: rolSeleccionado,
        telefono: telefono || null,
        direccion: direccion || null
      });

      if (data.status === "success") {
        ui.mostrarAlerta(alerta, "exito", data.mensaje);
        auth.guardarSesion(data.user);
        mostrarVerificacion(data.user.email, data.codigo_verificacion);
      } else {
        ui.mostrarAlerta(alerta, "error", data.mensaje);
      }
    } catch (error) {
      ui.mostrarAlerta(alerta, "error", "Error de conexión con el backend.");
    }
    return false;
  }

  let emailVerificacion = "";
  let codigoVerificacion = "";

  function mostrarVerificacion(email, codigo) {
    emailVerificacion = email;
    codigoVerificacion = codigo;
    document.getElementById("codigo-simulado").textContent = codigo;
    document.getElementById("modal-verificacion").classList.remove("hidden");
  }

  function cerrarVerificacion() {
    document.getElementById("modal-verificacion").classList.add("hidden");
  }

  async function verificarCuenta(evento) {
    if (evento) {
      evento.preventDefault();
      if (evento.stopPropagation) evento.stopPropagation();
    }

    const alerta = document.getElementById("alerta-verificacion");
    const codigo = document.getElementById("codigo-verificacion").value.trim();

    if (!codigo || codigo.length !== 6) {
      ui.mostrarAlerta(alerta, "error", "Ingresa el código de 6 dígitos.");
      return false;
    }

    ui.mostrarAlerta(alerta, "info", "Verificando tu cuenta...");

    try {
      const data = await api.verificarCuenta(emailVerificacion, codigo);

      if (data.status === "success") {
        ui.mostrarAlerta(alerta, "exito", data.mensaje);
        setTimeout(function() {
          cerrarVerificacion();
          window.alert("Tu cuenta ha sido verificada. Ahora puedes iniciar sesión.");
        }, 1500);
      } else {
        ui.mostrarAlerta(alerta, "error", data.mensaje);
      }
    } catch (error) {
      ui.mostrarAlerta(alerta, "error", "Error de conexión con el backend.");
    }
    return false;
  }

  async function reenviarCodigo() {
    if (!emailVerificacion) return;

    try {
      const data = await api.registrarUsuario({
        nombre: "",
        email: emailVerificacion,
        password: "",
        rol: "comprador"
      });

      if (data.status === "error" && data.mensaje.includes("ya está registrado")) {
        window.alert("El código ha sido reenviado a tu correo (simulado).");
      }
    } catch (error) {
      window.alert("Error al reenviar el código.");
    }
  }

  function togglePassword(inputId, btn) {
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

  function init() {
    document.getElementById("btn-comprador").addEventListener("click", function () {
      setRol("comprador");
    });
    document.getElementById("btn-agricultor").addEventListener("click", function () {
      setRol("agricultor");
    });
    document.getElementById("login-form").addEventListener("submit", iniciarSesion);
    document.getElementById("register-form").addEventListener("submit", registrarUsuario);
    document.getElementById("form-verificacion").addEventListener("submit", verificarCuenta);
    document.getElementById("btn-alternar").addEventListener("click", alternarRegistro);
    setRol("comprador");
  }

  AgroColab.login = { init, cerrarVerificacion, reenviarCodigo, togglePassword };
})();
