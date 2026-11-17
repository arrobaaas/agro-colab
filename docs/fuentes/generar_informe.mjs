// Genera docs/Informe_Final_AgroColab.pdf desde informe_final.html.
//
// Uso, desde la raíz del repositorio:  node docs/fuentes/generar_informe.mjs
// Requisitos: Node 18+, Google Chrome o Chromium, y poppler-utils (pdftotext,
// pdfunite, pdfinfo).
//
// La pauta pide numerar las páginas desde la introducción, así que se imprimen
// dos PDF: la portada y el índice sin número, y el cuerpo numerado desde 1.
// Después se busca en el texto del cuerpo la página de cada título, figura y
// tabla, se completa el índice y se unen las dos partes.
import { execFileSync } from "node:child_process";
import { mkdtempSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import { abrirChrome } from "./cdp.mjs";

const aqui = dirname(fileURLToPath(import.meta.url));
const fuente = pathToFileURL(join(aqui, "informe_final.html")).href;
const destino = join(aqui, "..", "Informe_Final_AgroColab.pdf");
const tmp = mkdtempSync(join(tmpdir(), "informe-"));

const PIE = `
  <div style="width:100%; font-family:'Noto Sans','DejaVu Sans',Arial,sans-serif; font-size:8pt; color:#57534e;
              padding:0 2.5cm; display:flex; justify-content:space-between;">
    <span>Agro-Colab · Documentación final del producto · INGT1003 · Universidad Mayor</span>
    <span class="pageNumber"></span>
  </div>`;

const opciones = (conPie) => ({
  preferCSSPageSize: true,
  printBackground: true,
  displayHeaderFooter: conPie,
  headerTemplate: "<span></span>",
  footerTemplate: conPie ? PIE : "<span></span>",
});

const c = await abrirChrome({ ancho: 1200, alto: 1600 });
try {
  await c.ir(fuente);
  await c.esperar(`document.fonts.status === "loaded" && [...document.images].every((i) => i.complete)`);

  // 1. Cuerpo, numerado desde la introducción
  await c.evaluar(`document.documentElement.dataset.parte = "cuerpo"; true`);
  const cuerpo = join(tmp, "cuerpo.pdf");
  await c.pdf(cuerpo, opciones(true));

  // 2. Página de cada entrada del índice
  const paginas = Number(execFileSync("pdfinfo", [cuerpo]).toString().match(/Pages:\s+(\d+)/)[1]);
  const textos = [];
  for (let p = 1; p <= paginas; p++) {
    textos.push(execFileSync("pdftotext", ["-f", String(p), "-l", String(p), cuerpo, "-"]).toString());
  }
  const entradas = await c.evaluar(`JSON.stringify([...document.querySelectorAll("#indice li, #indice-figuras li, #indice-tablas li")].map((li) => li.dataset.buscar))`);
  const escapar = (s) => s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  const patron = (buscar) => {
    const figura = buscar.match(/^(Figura|Tabla) (\d+)\.$/);
    if (figura) return new RegExp(`(^|\\n)\\s*${figura[1]} ${figura[2]}\\.\\s`);
    const titulo = buscar.match(/^(\d+(?:\.\d+)?)(.+)$/);
    if (titulo) return new RegExp(`(^|\\n)\\s*${escapar(titulo[1])}\\s*${escapar(titulo[2].trim())}\\s*(\\n|$)`);
    return new RegExp(`(^|\\n)\\s*${escapar(buscar)}\\s*(\\n|$)`);
  };
  const numeros = JSON.parse(entradas).map((buscar) => {
    const re = patron(buscar);
    const i = textos.findIndex((t) => re.test(t));
    if (i === -1) console.warn(`No se encontró en el PDF: ${buscar}`);
    return i === -1 ? "" : String(i + 1);
  });

  // 3. Portada e índice, sin número de página
  await c.evaluar(`(() => {
    const numeros = ${JSON.stringify(numeros)};
    document.querySelectorAll("#indice li, #indice-figuras li, #indice-tablas li").forEach((li, i) => {
      li.querySelector(".pag").textContent = numeros[i];
    });
    document.documentElement.dataset.parte = "inicio";
    return true;
  })()`);
  const inicio = join(tmp, "inicio.pdf");
  await c.pdf(inicio, opciones(false));

  execFileSync("pdfunite", [inicio, cuerpo, destino]);
  const total = execFileSync("pdfinfo", [destino]).toString().match(/Pages:\s+(\d+)/)[1];
  const sinAnexos = (numeros[JSON.parse(entradas).indexOf("Anexos")] || "?") - 1;
  console.log(`Escrito ${destino}: ${total} páginas en total, ${paginas} numeradas, ${sinAnexos} antes de los anexos.`);
  if (c.errores.length) console.warn("Errores de JavaScript:", c.errores);
} finally {
  c.cerrar();
  rmSync(tmp, { recursive: true, force: true });
}
