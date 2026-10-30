/* Agro-Colab - Panel de monitoreo de seguridad (monitoreo.html).

   Pide el token de monitoreo, lo guarda solo en memoria y consulta
   GET /api/seguridad/resumen cada 30 segundos. Todo dato del servidor se
   escapa antes de insertarse como HTML. */

(function () {
  const AgroColab = window.AgroColab;
  const e = (valor) => AgroColab.ui.escapar(valor);
  const INTERVALO_MS = 30000;

  const NOMBRES = {
    login_fallido: "Login fallido",
    login_exitoso: "Login exitoso",
    token_invalido: "Token inválido",
    acceso_denegado: "Acceso denegado",
    limite_excedido: "Límite de intentos",
    entrada_html: "Intento de XSS",
    csp_violacion: "Bloqueo de CSP",
    cuenta_demo: "Ataque a cuenta demo",
    plan_inexistente: "Plan inexistente",
    cambio_password: "Cambio de contraseña",
    cambio_password_fallido: "Cambio de contraseña fallido",
    cuenta_eliminada: "Cuenta eliminada",
    registro: "Registro",
    verificacion_fallida: "Verificación fallida",
    alerta_enviada: "Alerta enviada"
  };

  const SEVERIDADES = {
    info: "bg-stone-100 text-stone-600",
    advertencia: "bg-amber-100 text-amber-800",
    critica: "bg-rose-100 text-rose-800"
  };

  class MonitoreoService {
    constructor() {
      this.token = null;
      this.temporizador = null;
    }

    async consultar() {
      const respuesta = await fetch(`${AgroColab.config.API_URL}/seguridad/resumen`, {
        headers: { "X-Monitoreo-Token": this.token }
      });
      const cuerpo = await respuesta.json().catch(() => null);
      if (!respuesta.ok) {
        const mensaje = cuerpo && cuerpo.detail && cuerpo.detail.mensaje;
        throw new Error(mensaje || `El servidor respondió ${respuesta.status}.`);
      }
      return cuerpo;
    }

    pintar(datos) {
      const severidad = datos.por_severidad || {};
      const total = Object.entries(datos.por_tipo || {})
        .filter(([tipo]) => tipo !== "alerta_enviada")
        .reduce((suma, [, cantidad]) => suma + cantidad, 0);
      document.getElementById("kpi-total").textContent = total;
      document.getElementById("kpi-advertencias").textContent = severidad.advertencia || 0;
      document.getElementById("kpi-criticos").textContent = severidad.critica || 0;
      document.getElementById("kpi-alertas").textContent = datos.alertas || 0;

      const estado = document.getElementById("estado-alertas");
      estado.className = `text-xs font-semibold px-3 py-1.5 rounded-full ${datos.alertas_configuradas ? "bg-emerald-100 text-emerald-800" : "bg-amber-100 text-amber-800"}`;
      estado.textContent = datos.alertas_configuradas
        ? "Alertas activas (correo o webhook)"
        : "Alertas sin destino: configura ALERTA_CORREO o ALERTA_WEBHOOK_URL";

      const tipos = Object.entries(datos.por_tipo || {}).sort((a, b) => b[1] - a[1]);
      const maximo = Math.max(1, ...tipos.map(([, cantidad]) => cantidad));
      document.getElementById("lista-tipos").innerHTML = tipos.length
        ? tipos.map(([tipo, cantidad]) => `
            <div>
              <div class="flex justify-between text-xs mb-1">
                <span class="font-semibold text-stone-700">${e(NOMBRES[tipo] || tipo)}</span>
                <span class="font-bold text-stone-900">${e(cantidad)}</span>
              </div>
              <div class="h-1.5 rounded-full bg-stone-100 overflow-hidden">
                <div class="h-full rounded-full bg-emerald-500" style="width:${Math.round((cantidad / maximo) * 100)}%"></div>
              </div>
            </div>`).join("")
        : '<p class="text-sm text-stone-500">Sin eventos en las últimas 24 horas.</p>';

      document.getElementById("tabla-eventos").innerHTML = (datos.eventos || []).length
        ? datos.eventos.map((evento) => `
            <tr class="align-top">
              <td class="px-4 py-2.5 whitespace-nowrap text-stone-500">${e(this.formatearHora(evento.momento))}</td>
              <td class="px-4 py-2.5"><span class="px-2 py-0.5 rounded-full font-bold ${SEVERIDADES[evento.severidad] || SEVERIDADES.info}">${e(evento.severidad)}</span></td>
              <td class="px-4 py-2.5 font-semibold text-stone-800 whitespace-nowrap">${e(NOMBRES[evento.tipo] || evento.tipo)}</td>
              <td class="px-4 py-2.5 text-stone-600">${e(evento.ip || "-")}<br><span class="text-stone-400">${e(evento.email || "")}</span></td>
              <td class="px-4 py-2.5 text-stone-600 break-words">${e(evento.detalle || "")}<br><span class="text-stone-400">${e(evento.ruta || "")}</span></td>
            </tr>`).join("")
        : '<tr><td colspan="5" class="px-4 py-6 text-center text-stone-500">Sin eventos registrados.</td></tr>';

      document.getElementById("estado-actualizacion").textContent =
        `Actualizado ${new Date().toLocaleTimeString("es-CL")}`;
    }

    formatearHora(iso) {
      if (!iso) return "-";
      return new Date(iso).toLocaleString("es-CL", { dateStyle: "short", timeStyle: "medium" });
    }

    async actualizar() {
      try {
        this.pintar(await this.consultar());
      } catch (error) {
        this.salir(error.message);
      }
    }

    async entrar(evento) {
      evento.preventDefault();
      const alerta = document.getElementById("alerta-monitoreo");
      this.token = document.getElementById("token-monitoreo").value;
      AgroColab.ui.mostrarAlerta(alerta, "info", "Consultando...");

      try {
        this.pintar(await this.consultar());
      } catch (error) {
        this.token = null;
        AgroColab.ui.mostrarAlerta(alerta, "error", error.message);
        return;
      }

      document.getElementById("form-monitoreo").reset();
      AgroColab.ui.ocultarAlerta(alerta);
      document.getElementById("acceso-monitoreo").classList.add("hidden");
      document.getElementById("panel-monitoreo").classList.remove("hidden");
      document.getElementById("btn-salir-monitoreo").classList.remove("hidden");
      this.temporizador = setInterval(() => this.actualizar(), INTERVALO_MS);
    }

    salir(mensaje) {
      clearInterval(this.temporizador);
      this.token = null;
      document.getElementById("panel-monitoreo").classList.add("hidden");
      document.getElementById("acceso-monitoreo").classList.remove("hidden");
      document.getElementById("btn-salir-monitoreo").classList.add("hidden");
      document.getElementById("estado-actualizacion").textContent = "";
      if (typeof mensaje === "string") {
        AgroColab.ui.mostrarAlerta(document.getElementById("alerta-monitoreo"), "error", mensaje);
      }
    }

    init() {
      document.getElementById("form-monitoreo").addEventListener("submit", (evento) => this.entrar(evento));
      document.getElementById("btn-salir-monitoreo").addEventListener("click", () => this.salir());
    }
  }

  const monitoreo = new MonitoreoService();
  AgroColab.monitoreo = monitoreo;
  document.addEventListener("DOMContentLoaded", () => monitoreo.init());
})();
