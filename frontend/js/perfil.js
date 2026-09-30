/* Agro-Colab - Modal de perfil de usuario: ver y editar información
   personal (nombre, correo, teléfono, dirección, contraseña). */

(function () {
  const AgroColab = (window.AgroColab = window.AgroColab || {});
  const { auth, ui } = AgroColab;

  function abrir() {
    const sesion = auth.leerSesion();
    if (!sesion) return;

    document.getElementById("perfil-nombre").textContent = sesion.nombre;
    document.getElementById("perfil-rol").textContent = sesion.rol;
    document.getElementById("perfil-input-nombre").value = sesion.nombre || "";
    document.getElementById("perfil-input-email").value = sesion.email || "";
    document.getElementById("perfil-input-telefono").value = sesion.telefono || "";
    document.getElementById("perfil-input-direccion").value = sesion.direccion || "";
    document.getElementById("perfil-input-password").value = "";

    document.getElementById("modal-perfil").classList.remove("hidden");
  }

  function cerrar() {
    document.getElementById("modal-perfil").classList.add("hidden");
  }

  async function guardar(evento) {
    evento.preventDefault();

    const alerta = document.getElementById("alerta-perfil");
    const sesion = auth.leerSesion();
    if (!sesion) return;

    const nombre = document.getElementById("perfil-input-nombre").value.trim();
    const email = document.getElementById("perfil-input-email").value.trim();
    const telefono = document.getElementById("perfil-input-telefono").value.trim();
    const direccion = document.getElementById("perfil-input-direccion").value.trim();
    const password = document.getElementById("perfil-input-password").value;

    if (!nombre || !email) {
      ui.mostrarAlerta(alerta, "error", "Nombre y correo son obligatorios.");
      return;
    }

    const cambios = {
      nombre,
      email,
      telefono,
      direccion,
      password: password || undefined
    };

    try {
      const data = await AgroColab.api.actualizarPerfil(cambios);

      if (data.status === "success") {
        auth.guardarSesion(data.user);
        ui.mostrarAlerta(alerta, "exito", "Perfil actualizado correctamente.");
        setTimeout(cerrar, 1500);
      } else {
        ui.mostrarAlerta(alerta, "error", data.mensaje || "No se pudo actualizar el perfil.");
      }
    } catch (error) {
      ui.mostrarAlerta(alerta, "error", "Error de comunicación con el backend.");
    }
  }

  function init() {
    document.getElementById("form-perfil").addEventListener("submit", guardar);
  }

  AgroColab.perfil = { init, abrir, cerrar };
})();
