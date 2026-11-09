/* Agro-Colab - Diálogos propios (DialogoService), expuesto como
   AgroColab.dialogo. Reemplazan a window.alert y window.confirm, que muestran
   la ventana gris del navegador ("arrobaaas.github.io dice...") en vez de la
   estética del sitio.
   - avisar(mensaje, opciones)    -> Promise que se resuelve al cerrar.
   - confirmar(mensaje, opciones) -> Promise<boolean>.
   - pedirClave(mensaje, opciones) -> Promise<string|null> (null = canceló).
   Los textos se escriben con textContent: un nombre de árbol o un mensaje
   del backend nunca se interpreta como HTML. */

(function () {
  const AgroColab = (window.AgroColab = window.AgroColab || {});

  const ICONOS = {
    info: "fa-circle-info",
    exito: "fa-circle-check",
    error: "fa-circle-exclamation",
    peligro: "fa-triangle-exclamation"
  };

  class DialogoService {
    constructor() {
      this.raiz = null;
      this.cola = Promise.resolve();
    }

    crear() {
      if (this.raiz) return;
      this.raiz = document.createElement("div");
      this.raiz.className = "dialogo tema-comprador hidden";
      this.raiz.innerHTML = `
        <div class="dialogo__fondo"></div>
        <div class="dialogo__panel" role="alertdialog" aria-modal="true" aria-labelledby="dialogo-titulo" aria-describedby="dialogo-mensaje">
          <span class="dialogo__icono"><i class="fa-solid"></i></span>
          <h3 id="dialogo-titulo" class="tc-titulo-sm"></h3>
          <p id="dialogo-mensaje" class="tc-cuerpo-sm"></p>
          <dl class="dialogo__datos hidden"></dl>
          <label class="dialogo__campo hidden">
            <span class="dialogo__campo-etiqueta"></span>
            <input type="password" class="input" autocomplete="current-password" maxlength="128">
          </label>
          <div class="dialogo__acciones">
            <button type="button" class="tc-boton tc-boton--contorno" data-dialogo="cancelar"></button>
            <button type="button" class="tc-boton" data-dialogo="aceptar"></button>
          </div>
        </div>`;
      document.body.appendChild(this.raiz);
    }

    /* Muestra un diálogo y espera la respuesta. Si ya hay uno abierto, el
       nuevo espera su turno en vez de taparlo. */
    mostrar(opciones) {
      const turno = this.cola.then(() => this.abrir(opciones));
      this.cola = turno.catch(() => {});
      return turno;
    }

    abrir({ titulo, mensaje, tipo = "info", aceptar = "Entendido", cancelar = null, peligro = false, datos = null, campo = null }) {
      this.crear();
      const raiz = this.raiz;
      const panel = raiz.querySelector(".dialogo__panel");
      const botonAceptar = raiz.querySelector('[data-dialogo="aceptar"]');
      const botonCancelar = raiz.querySelector('[data-dialogo="cancelar"]');
      const lista = raiz.querySelector(".dialogo__datos");
      const envoltorioCampo = raiz.querySelector(".dialogo__campo");
      const entrada = envoltorioCampo.querySelector("input");

      panel.dataset.tipo = tipo;
      raiz.querySelector(".dialogo__icono i").className = `fa-solid ${ICONOS[tipo] || ICONOS.info}`;
      raiz.querySelector("#dialogo-titulo").textContent = titulo;
      raiz.querySelector("#dialogo-mensaje").textContent = mensaje || "";
      raiz.querySelector("#dialogo-mensaje").classList.toggle("hidden", !mensaje);

      lista.replaceChildren();
      (datos || []).forEach(([etiqueta, valor]) => {
        const dt = document.createElement("dt");
        const dd = document.createElement("dd");
        dt.textContent = etiqueta;
        dd.textContent = valor;
        lista.append(dt, dd);
      });
      lista.classList.toggle("hidden", !(datos && datos.length));

      // Campo de contraseña opcional (pedirClave): se vacía en cada apertura
      entrada.value = "";
      envoltorioCampo.classList.toggle("hidden", !campo);
      envoltorioCampo.querySelector(".dialogo__campo-etiqueta").textContent = campo || "";

      botonAceptar.textContent = aceptar;
      botonAceptar.classList.toggle("tc-boton--peligro", peligro);
      botonCancelar.textContent = cancelar || "";
      botonCancelar.classList.toggle("hidden", !cancelar);

      const focoAnterior = document.activeElement;
      raiz.classList.remove("hidden");
      // En una acción destructiva el foco parte en "cancelar": un Enter
      // apurado no debe borrar nada
      if (campo) entrada.focus();
      else (peligro && cancelar ? botonCancelar : botonAceptar).focus();

      return new Promise((resolver) => {
        const cerrar = (respuesta) => {
          raiz.classList.add("hidden");
          raiz.removeEventListener("click", alHacerClic);
          document.removeEventListener("keydown", alPresionar, true);
          if (focoAnterior && document.contains(focoAnterior)) focoAnterior.focus();
          // Con campo, "aceptar" entrega lo escrito; la clave no queda en el DOM
          const valor = campo && respuesta ? entrada.value : null;
          entrada.value = "";
          resolver(campo ? valor : respuesta);
        };
        const alHacerClic = (evento) => {
          if (evento.target.closest('[data-dialogo="aceptar"]')) cerrar(true);
          else if (evento.target.closest('[data-dialogo="cancelar"]') || evento.target.classList.contains("dialogo__fondo")) cerrar(false);
        };
        const alPresionar = (evento) => {
          if (evento.key === "Escape") {
            evento.preventDefault();
            cerrar(false);
          } else if (evento.key === "Enter" && campo && document.activeElement === entrada) {
            // Con la contraseña escrita, Enter confirma (es una decisión explícita)
            evento.preventDefault();
            if (entrada.value) cerrar(true);
          } else if (evento.key === "Tab") {
            // El foco no sale del diálogo mientras está abierto
            const botones = [campo ? entrada : null, botonCancelar, botonAceptar].filter((b) => b && !b.classList.contains("hidden"));
            const indice = botones.indexOf(document.activeElement);
            evento.preventDefault();
            botones[(indice + (evento.shiftKey ? botones.length - 1 : 1)) % botones.length].focus();
          }
        };
        raiz.addEventListener("click", alHacerClic);
        document.addEventListener("keydown", alPresionar, true);
      });
    }

    avisar(mensaje, opciones = {}) {
      const tipo = opciones.tipo || "info";
      const titulos = { info: "Aviso", exito: "Listo", error: "No se pudo completar" };
      return this.mostrar({ titulo: opciones.titulo || titulos[tipo] || "Aviso", mensaje, tipo, datos: opciones.datos, aceptar: opciones.aceptar || "Entendido" });
    }

    confirmar(mensaje, opciones = {}) {
      return this.mostrar({
        titulo: opciones.titulo || "¿Confirmas?",
        mensaje,
        tipo: opciones.peligro ? "peligro" : "info",
        aceptar: opciones.aceptar || "Confirmar",
        cancelar: opciones.cancelar || "Volver",
        peligro: Boolean(opciones.peligro)
      });
    }

    pedirClave(mensaje, opciones = {}) {
      return this.mostrar({
        titulo: opciones.titulo || "Confirma con tu contraseña",
        mensaje,
        tipo: opciones.peligro ? "peligro" : "info",
        aceptar: opciones.aceptar || "Confirmar",
        cancelar: opciones.cancelar || "Volver",
        peligro: Boolean(opciones.peligro),
        campo: opciones.campo || "Contraseña actual"
      });
    }
  }

  AgroColab.dialogo = new DialogoService();
})();
