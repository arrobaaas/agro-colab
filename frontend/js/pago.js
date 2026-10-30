/* Agro-Colab - Pasarela de pago simulada (PagoService), expuesto como
   AgroColab.pago. cobrar(item) abre el checkout y devuelve una Promise con
   el pago aprobado, o null si el comprador cierra sin pagar.

   La validación definitiva la hace el servidor (routers/pagos.py); aquí se
   formatea la tarjeta, se muestra su vista previa y se avisa de errores
   evidentes antes de enviarla. El número y el CVV solo viajan en la petición
   de pago: no se guardan en el navegador. */

(function () {
  const AgroColab = (window.AgroColab = window.AgroColab || {});

  const ESPERA_MINIMA_MS = 1400; // el "procesando" se ve aunque el servidor responda al instante

  class PagoService {
    constructor() {
      this.item = null;
      this.resolver = null;
      this.pago = null;
    }

    get modal() {
      return document.getElementById("modal-pago");
    }

    campo(id) {
      return document.getElementById(`pago-${id}`);
    }

    /* ---------- Abrir y cerrar ---------- */

    cobrar(item) {
      if (this.resolver) this.resolver(null);
      this.item = item;
      this.pago = null;

      const esArbol = item.tipo === "arbol";
      this.campo("concepto").textContent = esArbol ? `Adopción de ${item.nombre}` : `Plan ${item.nombre}`;
      this.campo("detalle").textContent = esArbol
        ? "Primer mes. Se renueva cada mes hasta que canceles."
        : "Primer período de despacho. Se renueva hasta que canceles.";
      this.campo("total").textContent = AgroColab.ui.formatearMonto(item.precio);
      this.campo("boton-monto").textContent = AgroColab.ui.formatearMonto(item.precio);

      const sesion = AgroColab.auth.leerSesion();
      document.getElementById("form-pago").reset();
      this.campo("titular").value = (sesion && sesion.nombre) || "";
      this.actualizarVistaTarjeta();
      this.mostrarPaso("formulario");
      this.modal.classList.remove("hidden");
      window.setTimeout(() => this.campo("numero").focus(), 50);

      return new Promise((resolver) => {
        this.resolver = resolver;
      });
    }

    cerrar() {
      // Mientras se procesa no se puede cerrar: el cobro ya está en curso
      if (this.modal.dataset.paso === "procesando") return;
      this.modal.classList.add("hidden");
      if (this.resolver) this.resolver(this.pago);
      this.resolver = null;
    }

    mostrarPaso(paso) {
      this.modal.dataset.paso = paso;
      this.modal.querySelectorAll("[data-paso-pago]").forEach((el) => {
        el.classList.toggle("hidden", el.dataset.pasoPago !== paso);
      });
    }

    /* ---------- Formato y vista previa de la tarjeta ---------- */

    marca(numero) {
      if (/^4/.test(numero)) return "visa";
      if (/^(5[1-5]|2(2[2-9]|[3-6]\d|7[01]|720))/.test(numero)) return "mastercard";
      if (/^3[47]/.test(numero)) return "amex";
      return "";
    }

    formatearNumero(entrada) {
      const digitos = entrada.value.replace(/\D/g, "").slice(0, 19);
      entrada.value = digitos.replace(/(\d{4})(?=\d)/g, "$1 ");
      this.actualizarVistaTarjeta();
    }

    formatearVencimiento(entrada) {
      const digitos = entrada.value.replace(/\D/g, "").slice(0, 4);
      entrada.value = digitos.length > 2 ? `${digitos.slice(0, 2)}/${digitos.slice(2)}` : digitos;
      this.actualizarVistaTarjeta();
    }

    formatearCvv(entrada) {
      entrada.value = entrada.value.replace(/\D/g, "").slice(0, 4);
    }

    actualizarVistaTarjeta() {
      const numero = this.campo("numero").value.replace(/\D/g, "");
      const relleno = (numero + "•".repeat(16)).slice(0, Math.max(16, numero.length));
      this.campo("vista-numero").textContent = relleno.replace(/(.{4})(?=.)/g, "$1 ");
      this.campo("vista-titular").textContent = this.campo("titular").value.trim().toUpperCase() || "NOMBRE DEL TITULAR";
      this.campo("vista-vence").textContent = this.campo("vencimiento").value || "MM/AA";

      const marca = this.marca(numero);
      const nombres = { visa: "VISA", mastercard: "Mastercard", amex: "AMEX" };
      this.campo("vista-marca").textContent = nombres[marca] || "";
      this.campo("tarjeta").dataset.marca = marca;
    }

    /* Rellena una tarjeta de prueba (los chips bajo el formulario) */
    usarTarjetaPrueba(numero) {
      this.campo("numero").value = numero;
      this.formatearNumero(this.campo("numero"));
      this.campo("vencimiento").value = "12/29";
      this.campo("cvv").value = "123";
      this.actualizarVistaTarjeta();
      this.campo("numero").focus();
    }

    luhn(numero) {
      let suma = 0;
      [...numero].reverse().forEach((d, i) => {
        let n = Number(d);
        if (i % 2 === 1) {
          n *= 2;
          if (n > 9) n -= 9;
        }
        suma += n;
      });
      return numero.length >= 12 && suma % 10 === 0;
    }

    /* ---------- Envío ---------- */

    async enviar(evento) {
      evento.preventDefault();
      const alerta = this.campo("alerta");
      const numero = this.campo("numero").value.replace(/\D/g, "");
      const vencimiento = this.campo("vencimiento").value.trim();
      const cvv = this.campo("cvv").value.trim();
      const titular = this.campo("titular").value.trim();

      let error = "";
      if (!this.luhn(numero)) error = "El número de la tarjeta no es válido.";
      else if (!/^(0[1-9]|1[0-2])\/\d{2}$/.test(vencimiento)) error = "Ingresa el vencimiento como MM/AA.";
      else if (!/^\d{3,4}$/.test(cvv)) error = "El CVV tiene 3 o 4 dígitos.";
      else if (!titular) error = "Ingresa el nombre del titular.";
      if (error) {
        AgroColab.ui.mostrarAlerta(alerta, "error", error);
        return;
      }
      alerta.classList.add("hidden");

      this.mostrarPaso("procesando");
      const item = this.item;
      const datos = {
        tipo: item.tipo === "arbol" ? "arbol" : "plan",
        arbol_id: item.tipo === "arbol" ? item.id : null,
        plan_nombre: item.tipo === "arbol" ? null : item.nombre,
        numero, titular, vencimiento, cvv
      };

      let respuesta;
      try {
        [respuesta] = await Promise.all([
          AgroColab.api.pagar(datos),
          new Promise((r) => window.setTimeout(r, ESPERA_MINIMA_MS))
        ]);
      } catch (e) {
        respuesta = { status: "error", mensaje: "No hay conexión con el servidor. No se realizó ningún cobro." };
      }
      // Los datos de la tarjeta no quedan en el formulario
      this.campo("cvv").value = "";

      if (respuesta.status === "success") {
        this.pago = respuesta.pago;
        this.pintarComprobante(respuesta.pago);
        this.mostrarPaso("aprobado");
        this.campo("continuar").focus();
      } else {
        this.campo("motivo").textContent = respuesta.mensaje || "El pago no se pudo completar.";
        this.mostrarPaso("rechazado");
      }
    }

    pintarComprobante(pago) {
      const datos = [
        ["Monto", `${AgroColab.ui.formatearMonto(pago.monto_clp)} CLP`],
        ["Concepto", pago.concepto],
        ["Tarjeta", `${pago.marca} •••• ${pago.ultimos4}`],
        ["Autorización", pago.codigo_autorizacion],
        ["Transacción", pago.transaccion],
        ["Fecha", pago.fecha]
      ];
      const lista = this.campo("comprobante");
      lista.replaceChildren();
      datos.forEach(([etiqueta, valor]) => {
        const dt = document.createElement("dt");
        const dd = document.createElement("dd");
        dt.textContent = etiqueta;
        dd.textContent = valor || "-";
        lista.append(dt, dd);
      });
    }

    reintentar() {
      this.mostrarPaso("formulario");
      this.campo("numero").select();
      this.campo("numero").focus();
    }

    init() {
      const formulario = document.getElementById("form-pago");
      if (!formulario) return;
      formulario.addEventListener("submit", (evento) => this.enviar(evento));
      this.campo("titular").addEventListener("input", () => this.actualizarVistaTarjeta());
      document.addEventListener("keydown", (evento) => {
        if (evento.key === "Escape" && !this.modal.classList.contains("hidden")) this.cerrar();
      });
    }
  }

  AgroColab.pago = new PagoService();
})();
