"use strict";

// «Стол»: вкладка рядом с чатом. Вся команда на одном экране: схема со вспышками записок, «Вы» с подтверждением,
// таймер следующего обхода, правила в силе и журнал событий. Данные — GET /api/desk.
{
  const панель = document.querySelector("section.чат");
  const вкладки = $("чат-вкладки"), граф = $("стол-граф");
  const NS = "http://www.w3.org/2000/svg";
  const эл = (тег, атрибуты = {}, ...дети) => {
    const э = document.createElementNS(NS, тег);
    for (const [к, з] of Object.entries(атрибуты)) э.setAttribute(к, з);
    э.append(...дети);
    return э;
  };
  const ЦВЕТА = ["#3ecf9a", "#6aa9ff", "#f5a34b", "#c58bff", "#ff7aa8", "#5fd4e6", "#e6d35f"];
  let вид = "чат", таймер = 0, последняяЗаписка = null, данные = null, тикОт = 0, тикЧерез = null;
  const координаты = new Map();
  const ВЫ = { x: 738, y: 335 };

  function вкладка(новая) {
    вид = новая;
    панель.classList.toggle("вид-стол", вид === "стол");
    $("стол").hidden = вид !== "стол";
    for (const к of вкладки.children) к.setAttribute("aria-selected", String(к.dataset.вид === вид));
    if (вид === "стол") обновить(); else clearTimeout(таймер);
  }
  вкладки.addEventListener("click", (с) => { const к = с.target.closest("button[data-вид]"); if (к) вкладка(к.dataset.вид); });

  const время = (с) => (с || "").slice(11, 16);
  const мин = (с) => `${Math.floor(с / 3600) ? Math.floor(с / 3600) + " ч " : ""}${Math.floor((с % 3600) / 60)} мин ${с % 60} с`;

  function расставить(агенты) {
    координаты.clear();
    const лидер = агенты.find((а) => а.лидер);
    координаты.set(лидер.ключ, { x: 360, y: 190 });
    const внутри = агенты.filter((а) => а.поддержка && !а.лидер), снаружи = агенты.filter((а) => !а.поддержка && !а.лидер);
    внутри.forEach((а, i) => { const у = (i / внутри.length) * 2 * Math.PI - Math.PI / 2; координаты.set(а.ключ, { x: 360 + Math.cos(у) * 95, y: 190 + Math.sin(у) * 70 }); });
    снаружи.forEach((а, i) => { const у = (i / снаружи.length) * 2 * Math.PI - Math.PI / 2; координаты.set(а.ключ, { x: 360 + Math.cos(у) * 290, y: 190 + Math.sin(у) * 150 }); });
  }

  function нарисоватьГраф(д) {
    const цветГруппы = {}; [...new Set(д.агенты.map((а) => а.группа))].forEach((г, i) => { цветГруппы[г] = ЦВЕТА[i % ЦВЕТА.length]; });
    расставить(д.агенты);
    const лидер = д.агенты.find((а) => а.лидер);
    const слой = эл("g");
    const л = координаты.get(лидер.ключ);
    for (const а of д.агенты) if (!а.лидер) { const т = координаты.get(а.ключ); слой.append(эл("line", { class: "линия", x1: л.x, y1: л.y, x2: т.x, y2: т.y })); }
    const ждёт = д.ждёт.length > 0;
    слой.append(эл("line", { class: ждёт ? "линия красная" : "линия", x1: л.x, y1: л.y, x2: ВЫ.x, y2: ВЫ.y }));
    for (const а of д.агенты) {
      const т = координаты.get(а.ключ), главный = а.лидер;
      const г = эл("g", { class: `узел${а.работает ? " работает" : ""}${а.ошибка ? " ошибка" : ""}${!а.работает && !а.сегодня ? " спит" : ""}`,
        transform: `translate(${т.x} ${т.y})`, tabindex: 0, role: "button", "aria-label": `${а.имя}: ${а.роль}` });
      г.style.setProperty("--гц", цветГруппы[а.группа] || "#3ecf9a");
      const р = главный ? 21 : 13;
      г.append(эл("title", {}, `${а.имя}\n${а.роль}${а.правило ? `\nПравило: ${а.правило}` : ""}`),
        эл("circle", { class: "кольцо", r: р }), эл("circle", { class: "тело", r: р }));
      const путь = (window.ЗНАЧКИ_АГЕНТОВ || {})[а.значок];
      if (путь) { const з = эл("path", { class: "значок", d: путь, transform: `translate(${-р * .55} ${-р * .55}) scale(${р * 1.1 / 24})` }); г.append(з); }
      г.append(эл("text", { y: р + 12 }, главный ? а.имя : а.имя.split(" ")[0]));
      г.addEventListener("click", () => document.dispatchEvent(new CustomEvent("mizuyori:открыть-агента", { detail: а.ключ })));
      слой.append(г);
    }
    const вы = эл("g", { class: `вы узел${ждёт ? " ждёт" : ""}`, transform: `translate(${ВЫ.x} ${ВЫ.y})` },
      эл("circle", { class: "тело", r: 24 }), эл("text", { y: 4 }, "Вы"));
    слой.append(вы);
    if (ждёт) слой.append(эл("g", { class: "пузырь", transform: `translate(${ВЫ.x - 44} ${ВЫ.y - 52})` }, эл("rect", { width: 88, height: 20, rx: 10 }), эл("text", { x: 44, y: 14, "text-anchor": "middle" }, `подтвердить: ${д.ждёт.length}`)));
    граф.replaceChildren(слой);
  }

  function искра(от, кому) {
    const а = координаты.get(от) || координаты.get("смотрящий"), б = координаты.get(кому) || ВЫ;
    if (!а || !б || matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    const точка = эл("circle", { class: "искра", r: 4, cx: а.x, cy: а.y });
    точка.append(эл("animate", { attributeName: "cx", from: а.x, to: б.x, dur: "1.1s", fill: "freeze" }), эл("animate", { attributeName: "cy", from: а.y, to: б.y, dur: "1.1s", fill: "freeze" }));
    граф.append(точка);
    setTimeout(() => точка.remove(), 1300);
  }

  function нарисовать(д) {
    данные = д;
    const ждут = д.ждёт.length;
    $("стол-итоги").replaceChildren(
      ...[["идёт", д.работают, "работают"], ["", д.агенты.length, "в команде"], ["ждёт", ждут, "ждут вашего «да»"],
        ["", `${д.в_час.использовано}/${д.в_час.запросов_в_час}`, "запросов в час"]].map(([к, ч, п]) => создать("div", { класс: к }, создать("b", { текст: String(ч) }), создать("small", { текст: п }))));
    const с = $("стол-счёт"); с.hidden = !ждут; с.textContent = ждут || "";
    if (вид !== "стол") return;
    нарисоватьГраф(д);
    // искры для новых записок
    const новые = д.записки.filter((з) => з.id > (последняяЗаписка ?? Infinity)).reverse();
    if (д.записки.length) последняяЗаписка = Math.max(...д.записки.map((з) => з.id), последняяЗаписка ?? 0); else последняяЗаписка ??= 0;
    for (const з of новые.slice(-6)) искра(з.от, з.кому === "все" ? "смотрящий" : з.кому);
    тикЧерез = д.тик.через; тикОт = Date.now();
    нарисоватьТик();
    $("стол-правила").replaceChildren(создать("h3", { текст: "Правила в силе" }),
      создать("ul", {}, ...д.правила.filter((п) => п.текст).map((п) => создать("li", { класс: п.цвет },
        создать("i"), создать("span", {}, п.текст, п.доля != null ? создать("div", { класс: "полоса" }, создать("i", { style: `width:${Math.round(п.доля * 100)}%` })) : "")))));
    $("стол-журнал").replaceChildren(...(д.события.length ? д.события.slice(0, 14).map((е) => создать("div", { класс: `строка ${е.тип}` },
      создать("time", { текст: время(е.когда) }), создать("b", { текст: е.тип }), создать("span", { текст: е.текст, title: е.текст }))) : [создать("div", { класс: "пусто", текст: "Пока тихо: событий нет." })]));
  }

  function нарисоватьТик() {
    const место = $("стол-тик");
    if (!данные) return;
    const ост = тикЧерез == null ? null : Math.max(0, tикОсталось());
    const всего = данные.тик.интервал_часов * 3600;
    место.replaceChildren(создать("h3", { текст: "Следующий обход агентов" }),
      создать("div", { класс: "время-тика", текст: ост == null ? "—" : мин(ост) }),
      создать("div", { класс: "полоса" }, создать("i", { style: `width:${ост == null ? 0 : Math.round((1 - ост / всего) * 100)}%` })),
      создать("small", { текст: `Раз в ${данные.тик.интервал_часов} ч агенты сами смотрят данные: сроки, ТО, ГСМ.` }));
  }
  const tикОсталось = () => тикЧерез - Math.floor((Date.now() - тикОт) / 1000);
  setInterval(() => { if (вид === "стол" && !document.hidden) нарисоватьТик(); }, 1000);

  async function обновить() {
    clearTimeout(таймер);
    if (!document.hidden && !панель.closest("main").hidden) {
      try { нарисовать(await запрос("/api/desk")); } catch { /* сервер занят */ }
    }
    таймер = setTimeout(обновить, вид === "стол" ? (данные && данные.работают ? 1500 : 3000) : 20000);
  }
  document.addEventListener("visibilitychange", () => { if (!document.hidden) обновить(); });
  document.addEventListener("mizuyori:экран", (с) => { if (с.detail === "главная") обновить(); });
  document.addEventListener("mizuyori:открыть-стол", () => вкладка("стол"));
  обновить();
}
