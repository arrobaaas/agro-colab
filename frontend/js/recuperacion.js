/* Agro-Colab - Recuperación de contraseña (RecuperacionService), expuesto
   como AgroColab.recuperacion. Tres pasos en un mismo modal:
   1. correo: se pide un código (llega por correo; vence en 15 minutos).
   2. código: se ingresa el código y la nueva contraseña.
   3. listo: vuelve al login con el correo ya escrito.
   El servidor responde igual exista o no la cuenta, así que aquí tampoco
   se distingue: siempre se pasa al paso del código. */

(function () {
  const AgroColab = (window.AgroColab = window.AgroColab || {});

  class RecuperacionService {
    constructor() {
      this.email = "";
    }

    get modal() {
      return document.getElementById("modal-recuperar");
    }

    campo(id) {
      return document.getElementById(`recuperar-${id}`);
    }

    mostrarPaso(paso) {
      this.modal.querySelectorAll("[data-paso-recuperar]").forEach((el) => {
        el.classList.toggle("hidden", el.dataset.pasoRecuperar !== paso);
      });
      const foco = { correo: "email", codigo: "codigo", listo: "ir-login" }[paso];
      window.setTimeout(() => this.campo(foco).focus(), 50);
    }

    abrir() {
      // Si ya escribió su correo en el login, se reutiliza
      const emailLogin = document.getElementById("email");
      this.campo("email").value = (emailLogin && emailLogin.value.trim()) || "";
      ["codigo", "password", "password2"].forEach((id) => (this.campo(id).value = ""));
      ["alerta-correo", "alerta-codigo"].forEach((id) => this.campo(id).classList.add("hidden"));
      this.campo("codigo-desarrollo").classList.add("hidden");
      this.modal.classList.remove("hidden");
      this.mostrarPaso("correo");
    }

    cerrar() {
      this.modal.classList.add("hidden");
    }

    async pedirCodigo(evento) {
      if (evento) evento.preventDefault();
      const alerta = this.campo("alerta-correo");
      const email = this.campo("email").value.trim();
      if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
        AgroColab.ui.mostrarAlerta(alerta, "error", "Ingresa un correo válido.");
        return;
      }

      const boton = this.campo("enviar");
      boton.disabled = true;
      AgroColab.ui.mostrarAlerta(alerta, "info", "Enviando el código...");
      try {
        const data = await AgroColab.api.recuperarContrasena(email);
        if (data.status !== "success") {
          AgroColab.ui.mostrarAlerta(alerta, "error", data.mensaje || "No se pudo enviar el código.");
          return;
        }
        this.email = email;
        alerta.classList.add("hidden");
        this.campo("destino").textContent = email;
        // Solo en modo desarrollo el servidor devuelve el código
        const bloque = this.campo("codigo-desarrollo");
        bloque.classList.toggle("hidden", !data.codigo_desarrollo);
        bloque.querySelector("strong").textContent = data.codigo_desarrollo || "";
        this.mostrarPaso("codigo");
      } catch (error) {
        AgroColab.ui.mostrarAlerta(alerta, "error", "No hay conexión con el servidor. Intenta nuevamente en unos segundos.");
      } finally {
        boton.disabled = false;
      }
    }

    async restablecer(evento) {
      evento.preventDefault();
      const alerta = this.campo("alerta-codigo");
      const codigo = this.campo("codigo").value.trim();
      const password = this.campo("password").value;

      let error = "";
      if (!/^\d{6}$/.test(codigo)) error = "El código tiene 6 dígitos.";
      else if (password.length < 8) error = "La nueva contraseña debe tener al menos 8 caracteres.";
      else if (password !== this.campo("password2").value) error = "Las contraseñas no coinciden.";
      if (error) {
        AgroColab.ui.mostrarAlerta(alerta, "error", error);
        return;
      }

      const boton = this.campo("cambiar");
      boton.disabled = true;
      try {
        const data = await AgroColab.api.restablecerContrasena(this.email, codigo, password);
        if (data.status !== "success") {
          AgroColab.ui.mostrarAlerta(alerta, "error", data.mensaje || "No se pudo cambiar la contraseña.");
          return;
        }
        this.campo("password").value = "";
        this.campo("password2").value = "";
        this.mostrarPaso("listo");
      } catch (e) {
        AgroColab.ui.mostrarAlerta(alerta, "error", "No hay conexión con el servidor. Intenta nuevamente en unos segundos.");
      } finally {
        boton.disabled = false;
      }
    }

    reenviar() {
      this.campo("codigo").value = "";
      this.mostrarPaso("correo");
      this.pedirCodigo();
    }

    cambiarCorreo() {
      this.mostrarPaso("correo");
    }

    /* Vuelve al login con el correo listo para escribir la nueva contraseña */
    irAlLogin() {
      this.cerrar();
      const email = document.getElementById("email");
      const password = document.getElementById("password");
      if (email) email.value = this.email;
      if (password) {
        password.value = "";
        password.focus();
      }
    }

    init() {
      if (!this.modal) return;
      this.campo("form-correo").addEventListener("submit", (evento) => this.pedirCodigo(evento));
      this.campo("form-codigo").addEventListener("submit", (evento) => this.restablecer(evento));
      document.addEventListener("keydown", (evento) => {
        if (evento.key === "Escape" && !this.modal.classList.contains("hidden")) this.cerrar();
      });
    }
  }

  AgroColab.recuperacion = new RecuperacionService();
})();
