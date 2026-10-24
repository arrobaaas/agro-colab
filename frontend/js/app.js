/* Agro-Colab - Punto de entrada. Decide qué vista se muestra al abrir la app:
   login si no hay sesión, o la vista del rol si ya estaba conectado. */

document.addEventListener("DOMContentLoaded", function () {
  const { views, parcelas, agricultor, perfil, login, autocomplete, dashboard } = window.AgroColab;

  parcelas.init();
  agricultor.init();
  perfil.init();
  login.init();
  autocomplete.init();
  dashboard.init();
  views.init();

  views.mostrarVista(views.vistaInicial());
});
