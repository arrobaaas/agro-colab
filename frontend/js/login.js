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

  function init() {
    document.getElementById("btn-comprador").addEventListener("click", function () {
      setRol("comprador");
    });
    document.getElementById("btn-agricultor").addEventListener("click", function () {
      setRol("agricultor");
    });
    document.getElementById("login-form").addEventListener("submit", iniciarSesion);
    setRol("comprador");
  }

  AgroColab.login = { init };
})();
