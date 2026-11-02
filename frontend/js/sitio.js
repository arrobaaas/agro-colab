/* Agro-Colab - Comportamiento común a todas las páginas, expuesto como
   AgroColab.cookies: el aviso de cookies y el bloqueo del clic derecho.

   El clic derecho bloqueado no protege nada por sí solo: el código del
   navegador siempre se puede leer. Por eso ninguna clave va en el frontend. */

(function () {
  const AgroColab = (window.AgroColab = window.AgroColab || {});
  const CLAVE = "agrocolab_cookies";
  const CLAVE_PLAN = "agrocolab_plan";

  /* Mantener presionado un campo en el celular también dispara este evento:
     ahí se deja pasar, porque es la única forma de pegar un código o una
     contraseña desde el teclado táctil. */
  function bloquearMenu(evento) {
    const enCampo = evento.target.closest && evento.target.closest("input, textarea");
    if (enCampo && evento.pointerType === "touch") return;
    evento.preventDefault();
  }

  class CookiesService {
    leerDecision() {
      try {
        return localStorage.getItem(CLAVE);
      } catch (error) {
        return null;
      }
    }

    aceptaPreferencias() {
      return this.leerDecision() === "aceptadas";
    }

    decidir(decision) {
      try {
        localStorage.setItem(CLAVE, decision);
        // Rechazarlas también borra lo que se hubiera guardado antes
        if (decision !== "aceptadas") localStorage.removeItem(CLAVE_PLAN);
      } catch (error) { /* almacenamiento no disponible */ }
      this.cerrarAviso();
      this.pintarEstado();
    }

    cerrarAviso() {
      const aviso = document.getElementById("aviso-cookies");
      if (aviso) aviso.remove();
    }

    mostrarAviso() {
      this.cerrarAviso();
      const aviso = document.createElement("section");
      aviso.id = "aviso-cookies";
      aviso.className = "aviso-cookies tema-comprador";
      aviso.setAttribute("aria-label", "Aviso de cookies");
      aviso.innerHTML = `
        <p>
          <strong>Tu navegador, tus reglas</strong>
          Guardamos lo necesario para mantener tu sesión y tu canasta. Si aceptas, también
          recordamos tu último plan para tu próxima visita. No usamos publicidad ni seguimiento.
          <a href="cookies.html">Política de cookies</a>
        </p>
        <div class="aviso-cookies__acciones">
          <button type="button" class="tc-boton" data-decision="aceptadas">Aceptar</button>
          <button type="button" class="tc-boton tc-boton--contorno" data-decision="necesarias">Solo necesarias</button>
        </div>`;
      aviso.addEventListener("click", (evento) => {
        const boton = evento.target.closest("[data-decision]");
        if (boton) this.decidir(boton.dataset.decision);
      });
      document.body.appendChild(aviso);
    }

    /* Texto y botón de la página de la política */
    pintarEstado() {
      const estado = document.getElementById("cookies-estado");
      if (!estado) return;
      const decision = this.leerDecision();
      estado.textContent = decision === "aceptadas"
        ? "Aceptaste todas: recordamos tu último plan."
        : decision === "necesarias"
          ? "Elegiste solo las necesarias."
          : "Todavía no eliges.";
    }

    init() {
      document.addEventListener("contextmenu", bloquearMenu);
      const boton = document.getElementById("cookies-cambiar");
      if (boton) boton.addEventListener("click", () => this.mostrarAviso());
      this.pintarEstado();
      if (!this.leerDecision()) this.mostrarAviso();
    }
  }

  AgroColab.cookies = new CookiesService();
  AgroColab.cookies.init();
})();
