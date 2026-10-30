/* Agro-Colab - Constelación de la portada (ConstelacionService), expuesta
   como AgroColab.constelacion.

   Miles de triángulos pequeños con contorno, en la paleta de la marca, que
   forman un árbol (copa, tronco y raíces) sobre el lienzo oscuro, con
   partículas sueltas alrededor. Se mueven suavemente y se apartan del cursor.
   Solo se anima mientras está en pantalla; con "reducir movimiento" se
   dibuja una vez y queda quieta. */

(function () {
  const AgroColab = (window.AgroColab = window.AgroColab || {});

  const COLORES = ["#34d399", "#10b981", "#6ee7b7", "#15846e", "#2dd4bf", "#a3e635", "#fbbf24", "#f59e0b"];
  // Pesos: predominan los verdes, con chispas ámbar
  const PESOS = [5, 4, 3, 3, 2, 2, 2, 1];

  class ConstelacionService {
    constructor() {
      this.canvas = null;
      this.contexto = null;
      this.particulas = [];
      this.visible = false;
      this.cuadro = null;
      this.mouse = { x: -9999, y: -9999 };
      this.reducirMovimiento = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    }

    colorAleatorio() {
      const total = PESOS.reduce((a, b) => a + b, 0);
      let r = Math.random() * total;
      for (let i = 0; i < COLORES.length; i++) {
        r -= PESOS[i];
        if (r <= 0) return COLORES[i];
      }
      return COLORES[0];
    }

    /* Punto aleatorio dentro de la silueta del árbol, en un espacio de 0 a 1 */
    puntoDelArbol() {
      const zona = Math.random();
      if (zona < 0.78) {
        // Copa: unión de varios círculos para un contorno orgánico
        const lobulos = [
          [0.5, 0.36, 0.25], [0.32, 0.42, 0.17], [0.68, 0.42, 0.17],
          [0.4, 0.24, 0.16], [0.6, 0.24, 0.16], [0.5, 0.17, 0.13]
        ];
        const [cx, cy, radio] = lobulos[Math.floor(Math.random() * lobulos.length)];
        const angulo = Math.random() * Math.PI * 2;
        // Más denso hacia el centro de cada lóbulo
        const distancia = radio * Math.sqrt(Math.random()) * (0.75 + Math.random() * 0.25);
        return { x: cx + Math.cos(angulo) * distancia, y: cy + Math.sin(angulo) * distancia, peso: 1 };
      }
      if (zona < 0.92) {
        // Tronco: se angosta hacia arriba
        const t = Math.random();
        const ancho = 0.022 + t * 0.03;
        return { x: 0.5 + (Math.random() - 0.5) * 2 * ancho, y: 0.6 + t * 0.22, peso: 0.9 };
      }
      // Raíces: se abren hacia los lados
      const lado = Math.random() < 0.5 ? -1 : 1;
      const t = Math.random();
      return { x: 0.5 + lado * t * 0.2 + (Math.random() - 0.5) * 0.02, y: 0.82 + t * 0.06 + (Math.random() - 0.5) * 0.015, peso: 0.8 };
    }

    crearParticulas() {
      const particulas = [];
      for (let i = 0; i < 1250; i++) {
        const punto = this.puntoDelArbol();
        particulas.push(this.nuevaParticula(punto.x, punto.y, 0.55 + Math.random() * 0.45));
      }
      // Partículas sueltas que dan profundidad alrededor
      for (let i = 0; i < 180; i++) {
        particulas.push(this.nuevaParticula(Math.random(), Math.random(), 0.12 + Math.random() * 0.2));
      }
      this.particulas = particulas;
    }

    nuevaParticula(x, y, opacidad) {
      return {
        x, y, opacidad,
        color: this.colorAleatorio(),
        tamano: 2 + Math.random() * 3.2,
        angulo: Math.random() * Math.PI * 2,
        giro: (Math.random() - 0.5) * 0.004,
        fase: Math.random() * Math.PI * 2,
        amplitud: 0.002 + Math.random() * 0.004,
        dx: 0, dy: 0
      };
    }

    ajustarTamano() {
      const caja = this.canvas.getBoundingClientRect();
      const densidad = Math.min(window.devicePixelRatio || 1, 2);
      this.ancho = caja.width;
      this.alto = caja.height;
      this.canvas.width = Math.round(caja.width * densidad);
      this.canvas.height = Math.round(caja.height * densidad);
      this.contexto.setTransform(densidad, 0, 0, densidad, 0, 0);
    }

    dibujar(tiempo) {
      const ctx = this.contexto;
      const lado = Math.min(this.ancho, this.alto);
      const margenX = (this.ancho - lado) / 2;
      const margenY = (this.alto - lado) / 2;
      ctx.clearRect(0, 0, this.ancho, this.alto);
      ctx.lineWidth = 1.1;

      for (const p of this.particulas) {
        const oscilacion = this.reducirMovimiento ? 0 : Math.sin(tiempo * 0.0006 + p.fase) * p.amplitud;
        let x = margenX + (p.x + oscilacion) * lado;
        let y = margenY + (p.y + Math.cos(tiempo * 0.0005 + p.fase) * p.amplitud * (this.reducirMovimiento ? 0 : 1)) * lado;

        // Las partículas se apartan del cursor y vuelven con suavidad
        const distX = x - this.mouse.x;
        const distY = y - this.mouse.y;
        const distancia2 = distX * distX + distY * distY;
        const radio = lado * 0.14;
        if (distancia2 < radio * radio && distancia2 > 0.01) {
          const fuerza = (1 - Math.sqrt(distancia2) / radio) * 18;
          const distancia = Math.sqrt(distancia2);
          p.dx += (distX / distancia) * fuerza * 0.08;
          p.dy += (distY / distancia) * fuerza * 0.08;
        }
        p.dx *= 0.9;
        p.dy *= 0.9;
        x += p.dx;
        y += p.dy;

        if (!this.reducirMovimiento) p.angulo += p.giro;
        const r = p.tamano;
        ctx.globalAlpha = p.opacidad;
        ctx.strokeStyle = p.color;
        ctx.beginPath();
        for (let k = 0; k < 3; k++) {
          const a = p.angulo + (k * Math.PI * 2) / 3;
          const px = x + Math.cos(a) * r;
          const py = y + Math.sin(a) * r;
          if (k === 0) ctx.moveTo(px, py);
          else ctx.lineTo(px, py);
        }
        ctx.closePath();
        ctx.stroke();
      }
      ctx.globalAlpha = 1;
    }

    animar(tiempo) {
      if (!this.visible) {
        this.cuadro = null;
        return;
      }
      this.dibujar(tiempo);
      this.cuadro = requestAnimationFrame((t) => this.animar(t));
    }

    arrancar() {
      if (this.reducirMovimiento || this.cuadro || !this.visible) return;
      this.cuadro = requestAnimationFrame((t) => this.animar(t));
    }

    init() {
      this.canvas = document.getElementById("constelacion");
      if (!this.canvas || !this.canvas.getContext) return;
      this.contexto = this.canvas.getContext("2d");
      this.crearParticulas();
      this.ajustarTamano();
      this.dibujar(0);

      window.addEventListener("resize", () => {
        this.ajustarTamano();
        this.dibujar(performance.now());
      }, { passive: true });

      this.canvas.parentElement.addEventListener("pointermove", (evento) => {
        const caja = this.canvas.getBoundingClientRect();
        this.mouse = { x: evento.clientX - caja.left, y: evento.clientY - caja.top };
      }, { passive: true });
      this.canvas.parentElement.addEventListener("pointerleave", () => {
        this.mouse = { x: -9999, y: -9999 };
      });

      /* Solo se anima mientras está en pantalla (y la vista no está oculta) */
      if ("IntersectionObserver" in window) {
        new IntersectionObserver((entradas) => {
          this.visible = entradas[0].isIntersecting;
          if (this.visible) {
            // Al volver a mostrarse la vista, el canvas pudo tener tamaño 0
            if (!this.ancho) this.ajustarTamano();
            this.dibujar(performance.now());
            this.arrancar();
          }
        }).observe(this.canvas);
      }
    }
  }

  const constelacion = new ConstelacionService();
  AgroColab.constelacion = constelacion;
})();
