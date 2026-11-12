"use strict";

// Талисманы агентов: у каждого своя форма, цвет и два глаза (как в команде ботов на видео).
// talисман(ключ) → <svg>. Глаза моргают, у работающего агента талисман покачивается.
{
  const NS = "http://www.w3.org/2000/svg";
  const ЦВ = { голубой: "#22c3e6", фиолет: "#7c5cff", синий: "#2f8cff", розовый: "#ff5c9a", зелёный: "#2fd27a", небесный: "#79c7ff",
    оранж: "#ff9f43", жёлтый: "#ffd23f", коралл: "#ff6b6b", мята: "#4fe3c1", сирень: "#c58bff" };
  const ФОРМЫ = {
    круг: '<circle cx="20" cy="20" r="17"/>',
    квадрат: '<rect x="4" y="4" width="32" height="32" rx="10"/>',
    шестиугольник: '<path d="M20 4l14 8v16l-14 8-14-8V12z" stroke-width="3" stroke-linejoin="round"/>',
    ромб: '<path d="M20 4l16 16-16 16L4 20z" stroke-width="4" stroke-linejoin="round"/>',
    капля: '<path d="M20 3c4 6 13 14 13 22a13 13 0 0 1-26 0C7 17 16 9 20 3z"/>',
    конус: '<path d="M20 7l15 26H5z" stroke-width="4" stroke-linejoin="round"/>',
    щит: '<path d="M20 3l14 5v11c0 8-6 14-14 17C12 33 6 27 6 19V8z" stroke-width="2" stroke-linejoin="round"/>',
    восьмиугольник: '<path d="M13 4h14l9 9v14l-9 9H13l-9-9V13z" stroke-width="2" stroke-linejoin="round"/>',
    таблетка: '<rect x="3" y="9" width="34" height="23" rx="11.5"/>',
  };
  // [форма, цвет] — у каждого агента свой, по ключу и по имени значка
  const ТАБЛИЦА = {
    чат: ["круг", "голубой"], память: ["капля", "зелёный"], смысл: ["шестиугольник", "синий"], сводка: ["квадрат", "фиолет"],
    цели: ["ромб", "розовый"], мнения: ["щит", "коралл"], смотрящий: ["шар", ""],
    инженер: ["щит", "небесный"], механик: ["шестиугольник", "оранж"], диспетчер: ["квадрат", "голубой"], трассировщик: ["конус", "мята"],
    кадровик: ["круг", "сирень"], юрист: ["восьмиугольник", "фиолет"], водитель: ["таблетка", "синий"], экономист: ["капля", "жёлтый"],
    делопроизводитель: ["квадрат", "розовый"], снабженец: ["ромб", "оранж"], архивариус: ["конус", "небесный"],
    контрагенты: ["шестиугольник", "зелёный"], проверяющий: ["щит", "мята"], секретарь: ["круг", "розовый"], сроки: ["восьмиугольник", "коралл"],
    охрана: ["щит", "зелёный"], гсмконтроль: ["капля", "оранж"], склад: ["таблетка", "жёлтый"], бухгалтер: ["ромб", "синий"],
  };
  const названияФорм = Object.keys(ФОРМЫ), названияЦветов = Object.keys(ЦВ);
  function выбрать(ключ) {
    if (ТАБЛИЦА[ключ]) return ТАБЛИЦА[ключ];
    let х = 0;
    for (const с of String(ключ)) х = (х * 31 + с.charCodeAt(0)) >>> 0;
    return [названияФорм[х % названияФорм.length], названияЦветов[(х >> 3) % названияЦветов.length]];
  }

  // Общие градиенты для «шара» лидера: один скрытый svg на страницу
  function определения() {
    if (document.getElementById("талисманы-определения")) return;
    const с = document.createElementNS(NS, "svg");
    с.setAttribute("id", "талисманы-определения"); с.setAttribute("width", "0"); с.setAttribute("height", "0"); с.setAttribute("aria-hidden", "true");
    с.style.cssText = "position:absolute;width:0;height:0";
    с.innerHTML = '<defs><radialGradient id="талисман-шар" cx="38%" cy="32%" r="75%"><stop offset="0" stop-color="#ffffff"/><stop offset=".6" stop-color="#e4e4ea"/><stop offset="1" stop-color="#a9a9b6"/></radialGradient></defs>';
    document.body.prepend(с);
  }

  window.талисман = function (ключ, настройки = {}) {
    определения();
    const [форма, цвет] = выбрать(ключ);
    const с = document.createElementNS(NS, "svg");
    с.setAttribute("viewBox", "0 0 40 40");
    с.setAttribute("class", `талисман${настройки.работает ? " работает" : ""}`);
    с.setAttribute("aria-hidden", "true");
    const фон = форма === "шар" ? "url(#талисман-шар)" : ЦВ[цвет];
    const тело = document.createElementNS(NS, "g");
    тело.setAttribute("class", "тело-талисмана");
    тело.setAttribute("fill", фон);
    if (форма !== "шар") тело.setAttribute("stroke", фон);
    тело.innerHTML = форма === "шар" ? '<circle cx="20" cy="20" r="17"/>' : ФОРМЫ[форма];
    const глаза = document.createElementNS(NS, "g");
    глаза.setAttribute("class", "глаза");
    глаза.setAttribute("fill", форма === "шар" ? "#16161c" : "#ffffff");
    const задержка = `${(Math.random() * 4).toFixed(2)}s`;
    for (const x of [14.6, 25.4]) {
      const г = document.createElementNS(NS, "ellipse");
      г.setAttribute("cx", x); г.setAttribute("cy", 19); г.setAttribute("rx", 2.2); г.setAttribute("ry", 3.5);
      г.setAttribute("class", "глаз"); г.style.animationDelay = задержка;
      глаза.append(г);
    }
    с.append(тело, глаза);
    return с;
  };
  window.ЦВЕТ_ТАЛИСМАНА = (ключ) => { const [ф, ц] = выбрать(ключ); return ф === "шар" ? "#f4f4f8" : ЦВ[ц]; };
}
