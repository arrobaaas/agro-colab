/* Agro-Colab - Gráficos del panel del agricultor (GraficosService), expuesto
   como AgroColab.graficos. Se dibujan con HTML y CSS, sin librerías (la CSP
   solo permite scripts propios):
   - Ingreso mensual por árbol: barra del ingreso actual sobre la pista del
     ingreso con todos los cupos ocupados.
   - Cupos por árbol: un cuadrado por cupo, lleno si está ocupado.
   - Adopciones por mes: columnas con las suscripciones activas según el mes
     en que comenzaron (últimos 6 meses).
   Cada gráfico tiene tooltip al pasar el mouse (o al enfocarlo con el
   teclado) y una vista de tabla con los mismos datos. */

(function () {
  const AgroColab = (window.AgroColab = window.AgroColab || {});
  const e = (texto) => AgroColab.ui.escapar(texto);

  const MESES_VISIBLES = 6;
  const NOMBRES_MES = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"];

  class GraficosService {
    constructor() {
      this.tooltip = null;
      this.observador = null;
    }

    monto(valor) {
      return AgroColab.ui.formatearMonto(valor);
    }

    /* Atributos del tooltip. Se leen con dataset y se escriben con
       textContent, así que los nombres de los árboles no se interpretan */
    tip(valor, titulo, detalle) {
      return `tabindex="0" data-tip-valor="${e(valor)}" data-tip-titulo="${e(titulo)}" data-tip-detalle="${e(detalle || "")}"`;
    }

    tabla(encabezados, filas) {
      return `
        <details class="tc-grafico__tabla">
          <summary>Ver como tabla</summary>
          <table class="tc-tabla">
            <thead><tr>${encabezados.map((h) => `<th>${e(h)}</th>`).join("")}</tr></thead>
            <tbody>${filas.map((f) => `<tr>${f.map((c) => `<td>${e(c)}</td>`).join("")}</tr>`).join("")}</tbody>
          </table>
        </details>`;
    }

    /* ---------- Ingreso mensual por árbol ---------- */

    pintarIngresos(arboles) {
      const destino = document.getElementById("grafico-ingresos");
      if (!destino) return;

      const datos = arboles.map((a) => ({
        nombre: a.nombre,
        actual: (a.precio_mensual_clp || 0) * (a.cupos_ocupados || 0),
        potencial: (a.precio_mensual_clp || 0) * (a.cupos_totales || 0)
      }));
      const maximo = Math.max(...datos.map((d) => d.potencial), 1);

      destino.innerHTML =
        `<div class="grafico-filas">${datos
          .map((d) => {
            const pista = (d.potencial / maximo) * 100;
            const relleno = d.potencial ? (d.actual / d.potencial) * 100 : 0;
            return `
            <div class="grafico-fila" ${this.tip(this.monto(d.actual), d.nombre, `de ${this.monto(d.potencial)} posibles al mes`)}>
              <span class="grafico-fila__nombre">${e(d.nombre)}</span>
              <div class="grafico-fila__area">
                <div class="grafico-barra__pista" style="width:${pista.toFixed(2)}%">
                  <div class="grafico-barra__relleno" style="width:${relleno.toFixed(2)}%"></div>
                </div>
              </div>
              <span class="grafico-fila__valor">${e(this.monto(d.actual))}</span>
            </div>`;
          })
          .join("")}</div>` +
        this.tabla(
          ["Árbol", "Ingreso actual", "Con todos los cupos"],
          datos.map((d) => [d.nombre, this.monto(d.actual), this.monto(d.potencial)])
        );
    }

    /* ---------- Cupos por árbol ---------- */

    pintarCupos(arboles) {
      const destino = document.getElementById("grafico-cupos");
      if (!destino) return;

      destino.innerHTML =
        `<div class="grafico-filas">${arboles
          .map((a) => {
            const totales = a.cupos_totales || 0;
            const ocupados = Math.min(a.cupos_ocupados || 0, totales);
            const cuadros = Array.from(
              { length: totales },
              (_, i) => `<span class="grafico-cupo${i < ocupados ? " grafico-cupo--ocupado" : ""}"></span>`
            ).join("");
            const libres = totales - ocupados;
            return `
            <div class="grafico-fila" ${this.tip(`${ocupados} de ${totales}`, a.nombre, libres ? `${libres} cupo${libres === 1 ? "" : "s"} libre${libres === 1 ? "" : "s"}` : "Cupos completos")}>
              <span class="grafico-fila__nombre">${e(a.nombre)}</span>
              <div class="grafico-fila__area grafico-cupos">${cuadros}</div>
              <span class="grafico-fila__valor">${ocupados}/${totales}</span>
            </div>`;
          })
          .join("")}</div>` +
        this.tabla(
          ["Árbol", "Ocupados", "Totales"],
          arboles.map((a) => [a.nombre, String(a.cupos_ocupados || 0), String(a.cupos_totales || 0)])
        );
    }

    /* ---------- Adopciones por mes ---------- */

    /* "dd/mm/aaaa" -> clave "aaaa-mm" */
    claveMes(fecha) {
      const partes = String(fecha || "").split("/");
      if (partes.length !== 3) return null;
      return `${partes[2]}-${partes[1].padStart(2, "0")}`;
    }

    pintarAdopciones(suscripcionesPorArbol) {
      const destino = document.getElementById("grafico-adopciones");
      if (!destino) return;

      if (!Array.isArray(suscripcionesPorArbol)) {
        destino.innerHTML = '<p class="tc-cuerpo-sm">No se pudieron cargar las adopciones.</p>';
        return;
      }

      const hoy = new Date();
      const meses = [];
      for (let i = MESES_VISIBLES - 1; i >= 0; i--) {
        const fecha = new Date(hoy.getFullYear(), hoy.getMonth() - i, 1);
        meses.push({
          clave: `${fecha.getFullYear()}-${String(fecha.getMonth() + 1).padStart(2, "0")}`,
          corto: NOMBRES_MES[fecha.getMonth()],
          largo: `${NOMBRES_MES[fecha.getMonth()]} ${fecha.getFullYear()}`,
          cantidad: 0
        });
      }

      suscripcionesPorArbol.forEach((arbol) => {
        (arbol.suscriptores || []).forEach((s) => {
          const mes = meses.find((m) => m.clave === this.claveMes(s.fecha_suscripcion));
          if (mes) mes.cantidad += 1;
        });
      });

      const maximo = Math.max(...meses.map((m) => m.cantidad), 1);
      const total = meses.reduce((suma, m) => suma + m.cantidad, 0);

      destino.innerHTML =
        `<div class="grafico-columnas">${meses
          .map((m) => {
            const alto = (m.cantidad / maximo) * 100;
            return `
            <div class="grafico-columna" ${this.tip(`${m.cantidad} adopci${m.cantidad === 1 ? "ón" : "ones"}`, m.largo, "")}>
              <div class="grafico-columna__area">
                ${m.cantidad ? `<span class="grafico-columna__valor">${m.cantidad}</span>` : ""}
                <div class="grafico-columna__barra" style="height:${alto.toFixed(2)}%"></div>
              </div>
              <span class="grafico-columna__mes">${e(m.corto)}</span>
            </div>`;
          })
          .join("")}</div>` +
        (total ? "" : '<p class="tc-cuerpo-sm" style="margin-top:1rem">Aún no hay adopciones activas en los últimos meses.</p>') +
        this.tabla(
          ["Mes", "Adopciones"],
          meses.map((m) => [m.largo, String(m.cantidad)])
        );
    }

    /* ---------- Tooltip compartido ---------- */

    iniciarTooltip() {
      if (this.tooltip) return;
      const vista = document.getElementById("vista-agricultor");
      if (!vista) return;

      this.tooltip = document.createElement("div");
      this.tooltip.className = "tc-tooltip";
      this.tooltip.setAttribute("role", "tooltip");
      this.tooltip.innerHTML = '<strong></strong><span></span><small></small>';
      vista.appendChild(this.tooltip);

      const mostrar = (objetivo, x, y) => {
        const [valor, titulo, detalle] = this.tooltip.children;
        valor.textContent = objetivo.dataset.tipValor;
        titulo.textContent = objetivo.dataset.tipTitulo;
        detalle.textContent = objetivo.dataset.tipDetalle;
        this.tooltip.classList.add("tc-tooltip--visible");

        const caja = this.tooltip.getBoundingClientRect();
        const izquierda = Math.min(Math.max(x + 14, 8), window.innerWidth - caja.width - 8);
        const arriba = y - caja.height - 14 < 8 ? y + 18 : y - caja.height - 14;
        this.tooltip.style.transform = `translate(${izquierda}px, ${arriba}px)`;
      };
      const ocultar = () => this.tooltip.classList.remove("tc-tooltip--visible");

      vista.addEventListener("pointermove", (evento) => {
        const objetivo = evento.target.closest("[data-tip-valor]");
        if (objetivo) mostrar(objetivo, evento.clientX, evento.clientY);
        else ocultar();
      }, { passive: true });
      vista.addEventListener("pointerleave", ocultar);
      vista.addEventListener("focusin", (evento) => {
        const objetivo = evento.target.closest("[data-tip-valor]");
        if (!objetivo) return;
        const caja = objetivo.getBoundingClientRect();
        mostrar(objetivo, caja.left + caja.width / 2, caja.top);
      });
      vista.addEventListener("focusout", ocultar);
      window.addEventListener("scroll", ocultar, { passive: true });
    }

    /* Las barras crecen cuando el gráfico entra en pantalla */
    animarAlEntrar() {
      const graficos = document.querySelectorAll(".tc-grafico:not(.tc-grafico--visible)");
      if (!("IntersectionObserver" in window)) {
        graficos.forEach((g) => g.classList.add("tc-grafico--visible"));
        return;
      }
      if (!this.observador) {
        this.observador = new IntersectionObserver((entradas) => {
          entradas.forEach((entrada) => {
            if (!entrada.isIntersecting) return;
            entrada.target.classList.add("tc-grafico--visible");
            this.observador.unobserve(entrada.target);
          });
        }, { threshold: 0.25 });
      }
      graficos.forEach((g) => this.observador.observe(g));
    }

    pintarHuerto(arboles) {
      this.iniciarTooltip();
      const contenedor = document.getElementById("graficos-huerto");
      if (contenedor) contenedor.classList.toggle("hidden", !arboles.length);
      if (!arboles.length) return;
      this.pintarIngresos(arboles);
      this.pintarCupos(arboles);
      this.animarAlEntrar();
    }
  }

  AgroColab.graficos = new GraficosService();
})();
