// «Дела»: дата в шапке и цвет приоритета у выпадающего списка.
(function () {
  "use strict";
  function дата() {
    const э = document.getElementById("дела-дата");
    if (!э) return;
    const т = new Date().toLocaleDateString("ru-RU", { weekday: "long", day: "numeric", month: "long" });
    э.textContent = т.charAt(0).toUpperCase() + т.slice(1);
  }
  function приоритет() {
    const с = document.getElementById("задача-приоритет");
    if (!с) return;
    const обновить = () => { с.dataset.значение = с.value; };
    с.addEventListener("change", обновить);
    new MutationObserver(обновить).observe(с, { attributes: true, attributeFilter: ["value"] });
    обновить();
  }
  function запуск() { дата(); приоритет(); }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", запуск); else запуск();
})();
