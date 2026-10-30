/* Agro-Colab - Delegación de eventos (AccionesService), expuesto como
   AgroColab.acciones.

   Reemplaza los onclick / oninput / onsubmit / onerror escritos en el HTML.
   Sin manejadores en línea, la Content-Security-Policy puede prohibir todo
   script inline (sin 'unsafe-inline'): aunque se colara HTML malicioso, el
   navegador no ejecutaría sus atributos on*.

   Uso en el HTML:
     data-accion="parcelas.abrirCanasta"              llama al método
     data-accion="views.mostrarVista" data-args='["parcelas"]'
     data-accion="parcelas.cerrarCanasta|parcelas.establecerLinea:adopcion"
                                                      varias, con un argumento
     data-args='["password", "$el"]'                  "$el" = el elemento
     data-al-escribir="autocomplete.buscarDireccion"  en cada input (recibe el elemento)
     data-sin-envio                                   el formulario no se envía solo
     data-si-falla="ocultar" | "quitar"               imagen que no carga */

class AccionesService {
  constructor() {
    /* Solo se pueden invocar métodos de estos servicios */
    this.modulos = ["parcelas", "views", "perfil", "login", "dashboard", "agricultor", "autocomplete"];
  }

  /* Convierte un argumento escrito en el HTML a su tipo (número o texto) */
  convertir(valor) {
    return /^-?\d+$/.test(valor) ? Number(valor) : valor;
  }

  ejecutar(ruta, args, elemento) {
    const [modulo, metodo] = ruta.split(".");
    const servicio = this.modulos.includes(modulo) ? window.AgroColab[modulo] : null;
    if (!servicio || typeof servicio[metodo] !== "function") {
      console.error(`Agro-Colab: acción desconocida "${ruta}"`);
      return;
    }
    servicio[metodo](...args.map((arg) => (arg === "$el" ? elemento : arg)));
  }

  alHacerClic(evento) {
    const elemento = evento.target.closest("[data-accion]");
    if (!elemento) return;
    if (elemento.tagName === "A") evento.preventDefault();

    const partes = elemento.dataset.accion.split("|").map((parte) => parte.trim());
    partes.forEach((parte, indice) => {
      const [ruta, argumento] = parte.split(":");
      let args = [];
      if (argumento !== undefined) {
        args = [this.convertir(argumento)];
      } else if (indice === 0 && elemento.dataset.args) {
        args = JSON.parse(elemento.dataset.args);
      }
      this.ejecutar(ruta, args, elemento);
    });
  }

  init() {
    document.addEventListener("click", (evento) => this.alHacerClic(evento));

    document.addEventListener("input", (evento) => {
      const ruta = evento.target.dataset && evento.target.dataset.alEscribir;
      if (ruta) this.ejecutar(ruta, ["$el"], evento.target);
    });

    document.addEventListener(
      "submit",
      (evento) => {
        if (evento.target.hasAttribute("data-sin-envio")) evento.preventDefault();
      },
      true
    );

    /* El evento error de las imágenes no burbujea: se escucha en captura */
    document.addEventListener(
      "error",
      (evento) => {
        const imagen = evento.target;
        if (!(imagen instanceof HTMLImageElement) || !imagen.dataset.siFalla) return;
        if (imagen.dataset.siFalla === "quitar") imagen.remove();
        else imagen.style.display = "none";
      },
      true
    );
  }
}

const accionesService = new AccionesService();
window.AgroColab.acciones = accionesService;
