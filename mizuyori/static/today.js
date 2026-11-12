"use strict";

// Над чатом: «Ждёт вас» (поручения, предложения агентов и памяти) и «Сегодня» (замечания агентов по данным).
{
  const блок = $("сегодня"), ждёт = $("ждёт-вас"), список = $("сегодня-список"), итог = $("сегодня-итог"), замечания = $("сегодня-замечания");
  let таймер = 0, было = "";

  function открытьРешение(п) {
    if (п.вид === "поручение") $("агенты-поручения").click();
    else if (п.вид === "агент" && п.агент) document.dispatchEvent(new CustomEvent("mizuyori:открыть-агента", { detail: п.агент }));
    else if (п.вид === "память") location.hash = "#мозги";
  }

  function нарисовать(д) {
    const ключ = JSON.stringify(д);
    if (ключ === было) return;
    было = ключ;
    блок.hidden = !д.ждёт.length && !д.замечания.length;
    ждёт.hidden = !д.ждёт.length;
    ждёт.replaceChildren(...(д.ждёт.length ? [
      создать("b", { текст: `⏳ Ждёт вас: ${д.ждёт.length}` }),
      ...д.ждёт.map((п) => создать("button", { type: "button", текст: п.текст, title: "Открыть", onclick: () => открытьРешение(п) })),
    ] : []));
    список.hidden = !д.замечания.length;
    итог.replaceChildren(
      создать("span", { текст: "Сегодня:" }),
      д.срочных ? создать("span", { класс: "срочно", текст: `${д.срочных} срочно` }) : "",
      д.внимание ? создать("span", { класс: "внимание", текст: `${д.внимание} внимание` }) : "");
    замечания.replaceChildren(...д.замечания.slice(0, 40).map((н) => создать("li", {
      класс: н.важно >= 2 ? "срочно" : "", title: "Открыть агента",
      onclick: () => document.dispatchEvent(new CustomEvent("mizuyori:открыть-агента", { detail: н.агент })) },
      создать("i"), создать("span", { текст: н.текст }), создать("small", { текст: н.имя }))));
    const поАгентам = {};
    for (const н of д.замечания) поАгентам[н.агент] = (поАгентам[н.агент] || 0) + 1;
    document.dispatchEvent(new CustomEvent("mizuyori:сегодня", { detail: { поАгентам } }));
  }

  async function обновить() {
    clearTimeout(таймер);
    if (!document.hidden && !блок.closest("main").hidden) {
      try { нарисовать(await запрос("/api/today")); } catch { /* сервер занят */ }
    }
    таймер = setTimeout(обновить, 15000);
  }
  document.addEventListener("visibilitychange", () => { if (!document.hidden) обновить(); });
  document.addEventListener("mizuyori:экран", (с) => { if (с.detail === "главная") обновить(); });
  document.addEventListener("mizuyori:чат-отправлено", () => setTimeout(обновить, 4000));
  обновить();
}
