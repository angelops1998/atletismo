/* JavaScript mínimo y sin dependencias.

   Todo lo que se puede resolver con HTML y CSS se resuelve así: los formularios
   funcionan aunque este archivo no cargue, que en la pista con mala señal pasa.
   Acá quedan solo las pocas cosas que el HTML no puede hacer solo. */
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

  // 3) Campos que envían su formulario al cambiar (el filtro de prueba, el
  //    selector de fecha de la lista). Estaba como onchange="" en el HTML y se
  //    movió acá porque la CSP no admite scripts inline. Ojo: estos dos
  //    formularios no tienen botón de envío, así que dependen de este archivo
  //    igual que antes dependían del onchange — sin JS no filtran. Las flechas
  //    "◀ ▶" y "Hoy" de la lista son links y sí funcionan siempre.
  document.querySelectorAll("[data-autoenviar]").forEach(function (campo) {
    campo.addEventListener("change", function () {
      if (campo.form) campo.form.submit();
    });
  });

  // 4) Filtro de la planilla de pruebas en el formulario de marcas: los radios
  //    con data-filtra-pruebas="id-del-select" esconden las pruebas que no son
  //    de la categoría elegida (cada <option> dice las suyas en data-cat). Al
  //    elegir un atleta, el select con data-elige-categoria marca solo el radio
  //    de su categoría. Sin JS se ven todas las pruebas, que también sirve.
  function filtrarPruebas(radio) {
    var select = document.getElementById(radio.getAttribute("data-filtra-pruebas"));
    if (!select) return;
    var cat = radio.value;
    Array.prototype.forEach.call(select.options, function (op) {
      var cats = op.getAttribute("data-cat");
      if (cats === null) return;
      var oculta = !!cat && cats.split(" ").indexOf(cat) === -1;
      op.hidden = oculta;
      op.disabled = oculta;
      if (oculta && op.selected) select.value = "";
    });
  }
  document.querySelectorAll("[data-filtra-pruebas]").forEach(function (radio) {
    radio.addEventListener("change", function () { if (radio.checked) filtrarPruebas(radio); });
    if (radio.checked) filtrarPruebas(radio);
  });
  document.querySelectorAll("[data-elige-categoria]").forEach(function (select) {
    var grupo = document.getElementById(select.getAttribute("data-elige-categoria"));
    if (!grupo) return;
    select.addEventListener("change", function () {
      var op = select.options[select.selectedIndex];
      var cat = op ? op.getAttribute("data-categoria") : "";
      var radio = grupo.querySelector('input[value="' + (cat || "") + '"]');
      if (radio && !radio.checked) {
        radio.checked = true;
        filtrarPruebas(radio);
      }
    });
  });

  // 5) Marcar a todos presentes de una: tomar lista es marcar las excepciones,
  //    no ir uno por uno cuando vinieron los treinta.
  var todos = document.querySelector("[data-todos-presentes]");
  if (todos) {
    todos.addEventListener("click", function () {
      document.querySelectorAll('input[type="radio"][value="presente"]')
        .forEach(function (r) { r.checked = true; });
    });
  }
})();
