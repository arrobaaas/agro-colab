/* Configuración de Tailwind CSS. El CSS se compila con scripts/compilar-css.sh
   y se publica como frontend/css/tailwind.css (sin depender de una CDN). */
module.exports = {
  content: ["./frontend/**/*.html", "./frontend/js/**/*.js"],
  theme: { extend: {} },
  plugins: []
};
