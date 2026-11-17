// Genera docs/informes/Informe_Final_Hitos_2_y_3.pdf desde informe.html.
//
// Uso, desde la raíz del repositorio:  node docs/informes/fuente/generar_informe.mjs
// Requisitos: Node 18+, Google Chrome o Chromium, y poppler-utils (pdftotext,
// pdfunite, pdfinfo). Las tipografías vienen en ./tipografias.
//
// Pasos:
//   1. Completa el contrato y las reglas de la API leyendo docs/api/API.md, para
//      que el informe no pueda contradecir al contrato (que una prueba compara
//      con el código).
//   2. Imprime el cuerpo, numerado desde la introducción, con el nombre de cada
//      sección en el encabezado de sus páginas.
//   3. Busca en el texto del PDF la página de cada título, figura y tabla, y
//      completa el índice y el mapa de la rúbrica. Repite hasta que no cambie.
//   4. Imprime la portada y el índice sin número, y une las dos partes.
import { execFileSync } from "node:child_process";
import { mkdtempSync, readFileSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import { abrirChrome } from "./cdp.mjs";

const aqui = dirname(fileURLToPath(import.meta.url));
const raiz = resolve(aqui, "..", "..", "..");
const fuente = pathToFileURL(join(aqui, "informe.html")).href;
const destino = join(raiz, "docs", "informes", "Informe_Final_Hitos_2_y_3.pdf");
const tmp = mkdtempSync(join(tmpdir(), "informe-"));

// ---------- 1. Contrato desde docs/api/API.md ----------
const escapar = (s) => s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
const conCodigo = (s) => escapar(s).replace(/`([^`]+)`/g, "<code>$1</code>");
const sinComillas = (s) => s.replace(/`/g, "").trim();
const celdas = (linea) => linea.trim().replace(/^\||\|$/g, "").split("|").map((c) => c.trim());

function leerContrato() {
  const lineas = readFileSync(join(raiz, "docs", "api", "API.md"), "utf-8").split("\n");
  let parte = "", grupo = "";
  const contrato = [], reglas = [];
  for (const linea of lineas) {
    if (linea.startsWith("## ")) { parte = linea.slice(3).trim(); continue; }
    if (linea.startsWith("### ")) {
      grupo = linea.slice(4).trim();
      if (parte === "Recursos") contrato.push(`<tr class="grupo"><td colspan="6">${escapar(grupo)}</td></tr>`);
      continue;
    }
    if (!linea.startsWith("| `")) continue;
    const c = celdas(linea);
    if (parte === "Recursos" && c.length >= 7) {
      const [verbo, ruta, acceso, cuerpo, exito, errores, hace] = c;
      const codigos = errores === "—" ? "—" : errores.split(",").map((e) => `<span class="cod">${escapar(e.trim())}</span>`).join("");
      contrato.push(
        `<tr><td><span class="verbo ${sinComillas(verbo)}">${sinComillas(verbo)}</span></td>` +
        `<td><span class="ruta">${escapar(sinComillas(ruta))}</span><br><span style="color:#57534e;font-size:7.8pt">${conCodigo(hace)}</span></td>` +
        `<td>${escapar(acceso)}</td><td>${cuerpo === "—" ? "—" : conCodigo(cuerpo)}</td>` +
        `<td><span class="cod ex">${escapar(exito)}</span></td><td>${codigos}</td></tr>`
      );
    }
    if (parte === "Reglas de los cuerpos" && c.length >= 2) {
      reglas.push(`<tr><td>${conCodigo(c[0])}</td><td>${conCodigo(c[1])}</td></tr>`);
    }
  }
  const operaciones = contrato.filter((f) => !f.includes('class="grupo"')).length;
  if (operaciones !== 37) console.warn(`Atención: API.md tiene ${operaciones} operaciones y el informe dice 37.`);
  return { contrato: contrato.join(""), reglas: reglas.join("") };
}

// ---------- utilidades de PDF ----------
const paginasDe = (pdf) => Number(execFileSync("pdfinfo", [pdf]).toString().match(/Pages:\s+(\d+)/)[1]);
function textosPorPagina(pdf) {
  const textos = [];
  for (let p = 1; p <= paginasDe(pdf); p++) {
    textos.push(execFileSync("pdftotext", ["-f", String(p), "-l", String(p), pdf, "-"]).toString());
  }
  return textos;
}
const regex = (s) => s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
function buscarPagina(textos, buscar) {
  const figura = buscar.match(/^(Figura|Tabla) (\d+)\.$/);
  const re = figura
    ? new RegExp(`(^|\\n)\\s*${figura[1]} ${figura[2]}\\.\\s`)
    : new RegExp(`(^|\\n)\\s*(\\d+(\\.\\d+)?\\s+)?${regex(buscar).replace(/\s+/g, "\\s+")}\\s*(\\n|$)`);
  const i = textos.findIndex((t) => re.test(t));
  return i === -1 ? "" : String(i + 1);
}

const opciones = { preferCSSPageSize: true, printBackground: true, displayHeaderFooter: false };

const c = await abrirChrome({ ancho: 1200, alto: 1600 });
try {
  await c.ir(fuente);
  await c.esperar(`document.fonts.status === "loaded" && [...document.images].every((i) => i.complete)`);
  await c.evaluar(`document.fonts.check('12px "Inter"') && document.fonts.check('12px "JetBrains Mono"')`).then((ok) => {
    if (!ok) console.warn("Atención: no se cargaron las tipografías locales.");
  });

  const { contrato, reglas } = leerContrato();
  await c.evaluar(`(() => {
    document.querySelector("#contrato tbody").innerHTML = ${JSON.stringify(contrato)};
    document.querySelector("#reglas tbody").innerHTML = ${JSON.stringify(reglas)};
    // Una página con nombre por sección: su título va en el encabezado
    const reglasCss = [];
    document.querySelectorAll(".cuerpo .seccion").forEach((s, i) => {
      s.style.page = "sec" + i;
      const titulo = (s.dataset.titulo || "").replace(/"/g, '\\\\"');
      reglasCss.push('@page sec' + i + ' { @top-right { content: "' + titulo + '"; font: 600 7.5pt "Inter"; color: #15803d; } }');
    });
    const estilo = document.createElement("style");
    estilo.textContent = reglasCss.join("\\n");
    document.head.appendChild(estilo);
    document.documentElement.dataset.parte = "cuerpo";
    return true;
  })()`);

  // ---------- 2 y 3. Cuerpo, con páginas estables ----------
  const entradas = JSON.parse(await c.evaluar(`JSON.stringify([...document.querySelectorAll("#indice li, #indice-figuras li, #indice-tablas li")].map((li) => ({ buscar: li.dataset.buscar, id: li.dataset.id || null })))`));
  const cuerpo = join(tmp, "cuerpo.pdf");
  let anterior = "";
  let numeros = [];
  for (let intento = 1; intento <= 4; intento++) {
    await c.pdf(cuerpo, opciones);
    const textos = textosPorPagina(cuerpo);
    numeros = entradas.map((e) => buscarPagina(textos, e.buscar));
    const faltan = entradas.filter((_, i) => !numeros[i]).map((e) => e.buscar);
    if (faltan.length) console.warn("No se encontró en el PDF:", faltan.join(" | "));
    const actual = numeros.join(",");
    if (actual === anterior) break;
    anterior = actual;
    const porId = Object.fromEntries(entradas.map((e, i) => [e.id, numeros[i]]).filter(([id]) => id));
    await c.evaluar(`(() => {
      const porId = ${JSON.stringify(porId)};
      document.querySelectorAll(".pagina[data-pag]").forEach((s) => { s.textContent = porId[s.dataset.pag] || "?"; });
      return true;
    })()`);
  }

  // ---------- 4. Portada e índice ----------
  await c.evaluar(`(() => {
    const numeros = ${JSON.stringify(numeros)};
    document.querySelectorAll("#indice li, #indice-figuras li, #indice-tablas li").forEach((li, i) => {
      li.querySelector(".pag").textContent = numeros[i];
    });
    document.documentElement.dataset.parte = "inicio";
    return true;
  })()`);
  const inicio = join(tmp, "inicio.pdf");
  await c.pdf(inicio, opciones);

  execFileSync("pdfunite", [inicio, cuerpo, destino]);
  const anexos = Number(numeros[entradas.findIndex((e) => e.id === "anexos")]) || 0;
  console.log(`Escrito ${destino}`);
  console.log(`${paginasDe(destino)} páginas: ${paginasDe(inicio)} de portada e índice, ${paginasDe(cuerpo)} numeradas, ${anexos - 1} antes de los anexos.`);
  if (c.errores.length) console.warn("Errores de JavaScript:", c.errores);
} finally {
  c.cerrar();
  rmSync(tmp, { recursive: true, force: true });
}
