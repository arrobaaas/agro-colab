/* Agro-Colab - Servicio de efectos visuales (EfectosService), expuesto como
   AgroColab.efectos. Transiciones al estilo de diapositivas:
   - Aparición de bloques con data-reveal al entrar en pantalla, con variantes
     "up" (por defecto), "left", "right", "zoom", "flip" y "wipe" (barrido).
   - Portada fija que el contenido cubre al bajar, con parallax y fundido.
   - Inclinación 3D con brillo en las tarjetas con data-tilt.
   - Header que se esconde al bajar y reaparece al subir.
   - Barra de progreso de lectura.
   Si el usuario pidió reducir el movimiento en su sistema, no se anima nada. */

(function () {
  const AgroColab = (window.AgroColab = window.AgroColab || {});

  const DURACION_REVEAL_MS = 1400;
  const INCLINACION_MAX_GRADOS = 7;

  class EfectosService {
    constructor() {
      this.observador = null;
      this.ultimoScroll = 0;
      this.reducirMovimiento = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
      this.punteroFino = window.matchMedia("(hover: hover) and (pointer: fine)").matches;
    }

    /* ---------- Aparición al hacer scroll ---------- */

    iniciarReveal() {
      if (this.reducirMovimiento || !("IntersectionObserver" in window)) {
        this.observar(document);
        return;
      }

      /* Solo con JS activo se ocultan los bloques: si este archivo falla, la
         página se ve completa igual. */
      document.documentElement.classList.add("js-reveal");

      this.observador = new IntersectionObserver(
        (entradas) => {
          entradas.forEach((entrada) => {
            if (!entrada.isIntersecting) return;
            const objetivo = entrada.target;
            this.observador.unobserve(objetivo);

            /* Un grupo revela juntos todos sus bloques (por ejemplo, las tres
               tarjetas de planes), aunque cada uno entre con otra variante. */
            if (objetivo.hasAttribute("data-reveal-grupo")) {
              objetivo.querySelectorAll("[data-reveal]").forEach((el) => this.revelar(el));
            } else {
              this.revelar(objetivo);
            }
          });
        },
        { threshold: 0.15, rootMargin: "0px 0px -60px 0px" }
      );

      this.observar(document);
    }

    /* Registra los bloques data-reveal dentro de raiz. Se llama también al
       pintar contenido nuevo (por ejemplo, las tarjetas de árboles). */
    observar(raiz) {
      const elementos = (raiz || document).querySelectorAll("[data-reveal]");
      if (!this.observador) {
        elementos.forEach((el) => el.removeAttribute("data-reveal"));
        return;
      }
      /* Los bloques dentro de un grupo se observan a través del grupo: así se
         mide una caja sin transformar y todos aparecen a la vez. */
      elementos.forEach((el) => {
        const grupo = el.closest("[data-reveal-grupo]");
        this.observador.observe(grupo || el);
      });
    }

    revelar(el) {
      this.observador.unobserve(el);
      el.classList.add("revelado");

      /* Terminada la animación se quita el atributo para que el hover y la
         inclinación 3D vuelvan a controlar la transformación. */
      const retraso = parseInt(getComputedStyle(el).getPropertyValue("--reveal-delay"), 10) || 0;
      window.setTimeout(() => {
        el.removeAttribute("data-reveal");
        el.classList.remove("revelado");
      }, DURACION_REVEAL_MS + retraso + 100);
    }

    /* ---------- Scroll: header, portada y barra de progreso ---------- */

    iniciarScroll() {
      const headers = document.querySelectorAll("header.sticky");
      const raiz = document.documentElement;
      let pendiente = false;

      const actualizar = () => {
        const actual = window.scrollY;
        const bajando = actual > this.ultimoScroll;

        /* Cerca del inicio el header siempre se ve; más abajo se esconde al
           bajar y reaparece apenas se sube. */
        headers.forEach((header) => {
          header.classList.toggle("header--oculto", bajando && actual > 120);
          header.classList.toggle("header--con-scroll", actual > 10);
        });

        const recorrido = raiz.scrollHeight - window.innerHeight;
        raiz.style.setProperty("--progreso", recorrido > 0 ? (actual / recorrido).toFixed(4) : 0);

        /* Iluminación del tema del comprador: al pasar la portada la página
           se ilumina (1) y al volver arriba se oscurece (0). El fundido lo
           hace CSS (transición de --luz en styles.css) */
        const luz = actual > window.innerHeight * 0.45 ? "1" : "0";
        if (raiz.style.getPropertyValue("--luz") !== luz) raiz.style.setProperty("--luz", luz);

        /* Avance de la portada (0 arriba, 1 cuando el contenido ya la cubrió) */
        if (!this.reducirMovimiento) {
          document.querySelectorAll(".hero--portada").forEach((hero) => {
            if (!hero.offsetHeight) return;
            const avance = Math.min(Math.max(actual / hero.offsetHeight, 0), 1);
            hero.style.setProperty("--avance", avance.toFixed(4));
          });
        }

        this.ultimoScroll = Math.max(actual, 0);
        pendiente = false;
      };

      window.addEventListener(
        "scroll",
        () => {
          if (pendiente) return;
          pendiente = true;
          window.requestAnimationFrame(actualizar);
        },
        { passive: true }
      );
      window.addEventListener("resize", actualizar, { passive: true });
      actualizar();
      this.actualizarScroll = actualizar;
    }

    /* ---------- Interacción con el mouse ---------- */

    iniciarMouse() {
      if (this.reducirMovimiento || !this.punteroFino) return;

      /* Delegación: así también funcionan las tarjetas que se pintan después */
      document.addEventListener(
        "pointermove",
        (evento) => {
          const tarjeta = evento.target.closest("[data-tilt]");
          if (tarjeta && !tarjeta.hasAttribute("data-reveal")) {
            const caja = tarjeta.getBoundingClientRect();
            const x = (evento.clientX - caja.left) / caja.width;
            const y = (evento.clientY - caja.top) / caja.height;
            tarjeta.style.setProperty("--ry", `${((x - 0.5) * 2 * INCLINACION_MAX_GRADOS).toFixed(2)}deg`);
            tarjeta.style.setProperty("--rx", `${((0.5 - y) * 2 * INCLINACION_MAX_GRADOS).toFixed(2)}deg`);
            tarjeta.style.setProperty("--mx", `${(x * 100).toFixed(1)}%`);
            tarjeta.style.setProperty("--my", `${(y * 100).toFixed(1)}%`);
            tarjeta.classList.add("tilt--activo");
          }

          const hero = evento.target.closest(".hero--portada");
          if (hero) {
            const caja = hero.getBoundingClientRect();
            hero.style.setProperty("--luz-x", `${evento.clientX - caja.left}px`);
            hero.style.setProperty("--luz-y", `${evento.clientY - caja.top}px`);
          }
        },
        { passive: true }
      );

      document.addEventListener("pointerout", (evento) => {
        const tarjeta = evento.target.closest("[data-tilt]");
        if (!tarjeta || tarjeta.contains(evento.relatedTarget)) return;
        tarjeta.classList.remove("tilt--activo");
        tarjeta.style.setProperty("--rx", "0deg");
        tarjeta.style.setProperty("--ry", "0deg");
      });
    }

    init() {
      this.iniciarReveal();
      this.iniciarScroll();
      this.iniciarMouse();
    }
  }

  const efectosService = new EfectosService();
  window.AgroColab.efectos = efectosService;
})();
