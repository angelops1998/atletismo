/* JavaScript mínimo y sin dependencias.

   Todo lo que se puede resolver con HTML y CSS se resuelve así: los formularios
   funcionan aunque este archivo no cargue, que en la pista con mala señal pasa.
   Acá quedan solo las tres cosas que el HTML no puede hacer solo. */
(function () {
  "use strict";

  // 1) Bloques que aparecen según una respuesta anterior (la molestia del parte).
  //    data-abre="id-del-bloque" en el input que lo dispara.
  document.querySelectorAll("[data-abre]").forEach(function (input) {
    var bloque = document.getElementById(input.getAttribute("data-abre"));
    if (!bloque) return;
    var grupo = document.getElementsByName(input.name);
    function sincronizar() {
      bloque.classList.toggle("abierto", input.checked);
    }
    Array.prototype.forEach.call(grupo, function (otro) {
      otro.addEventListener("change", sincronizar);
    });
    sincronizar();
  });

  // 2) Confirmación antes de lo que no se puede deshacer (borrar un pago o una marca).
  document.querySelectorAll("[data-confirmar]").forEach(function (form) {
    form.addEventListener("submit", function (e) {
      if (!window.confirm(form.getAttribute("data-confirmar"))) e.preventDefault();
    });
  });

  // 3) Marcar a todos presentes de una: tomar lista es marcar las excepciones,
  //    no ir uno por uno cuando vinieron los treinta.
  var todos = document.querySelector("[data-todos-presentes]");
  if (todos) {
    todos.addEventListener("click", function () {
      document.querySelectorAll('input[type="radio"][value="presente"]')
        .forEach(function (r) { r.checked = true; });
    });
  }
})();
