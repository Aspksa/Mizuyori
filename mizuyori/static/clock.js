"use strict";

// ---- Часы и календарь ------------------------------------------------------
{
  const месяцы = ["Январь", "Февраль", "Март", "Апрель", "Май", "Июнь",
    "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь"];

  const двузначное = (ч) => String(ч).padStart(2, "0");
  const ключДня = (д) => `${д.getFullYear()}-${д.getMonth()}-${д.getDate()}`;

  let показанный = new Date();          // какой месяц показан в календаре
  показанный.setDate(1);
  let сегодняКлюч = ключДня(new Date());
  let выбранный = null;                 // выбранный день «ГГГГ-ММ-ДД» или null
  let поДням = new Map();               // «ГГГГ-ММ-ДД» → { открыто, сделано }

  const деньISO = (д) => `${д.getFullYear()}-${двузначное(д.getMonth() + 1)}-${двузначное(д.getDate())}`;

  // ---- Часы ----

  function обновитьЧасы() {
    const сейчас = new Date();
    $("часы-время").textContent = `${двузначное(сейчас.getHours())}:${двузначное(сейчас.getMinutes())}`;
    $("часы-секунды").textContent = двузначное(сейчас.getSeconds());
    $("часы-дата").textContent = сейчас.toLocaleDateString("ru-RU",
      { weekday: "long", day: "numeric", month: "long", year: "numeric" });

    // Наступил новый день — перерисовываем календарь
    if (ключДня(сейчас) !== сегодняКлюч) {
      сегодняКлюч = ключДня(сейчас);
      нарисоватьКалендарь();
      document.dispatchEvent(new CustomEvent("mizuyori:новый-день"));
    }
    // Следующее обновление — ровно в начале следующей секунды
    setTimeout(обновитьЧасы, 1000 - сейчас.getMilliseconds() + 5);
  }

  // ---- Календарь ----

  function нарисоватьКалендарь() {
    const год = показанный.getFullYear();
    const месяц = показанный.getMonth();
    $("календарь-месяц").textContent = `${месяцы[месяц]} ${год}`;

    // Неделя начинается с понедельника
    const сдвиг = (new Date(год, месяц, 1).getDay() + 6) % 7;
    const начало = new Date(год, месяц, 1 - сдвиг);
    const дни = [];
    for (let i = 0; i < 42; i++) {
      const д = new Date(начало.getFullYear(), начало.getMonth(), начало.getDate() + i);
      const iso = деньISO(д);
      const задачиДня = поДням.get(iso);
      const классы = ["день"];
      if (д.getMonth() !== месяц) классы.push("чужой");
      if (ключДня(д) === сегодняКлюч) классы.push("сегодня");
      if ((д.getDay() + 6) % 7 >= 5) классы.push("выходной");
      if (iso === выбранный) классы.push("выбран");
      if (задачиДня?.открыто) классы.push("есть-задачи");
      else if (задачиДня?.сделано) классы.push("всё-сделано");

      let подсказка = д.toLocaleDateString("ru-RU", { weekday: "long", day: "numeric", month: "long", year: "numeric" });
      if (задачиДня?.открыто) подсказка += ` — задач: ${задачиДня.открыто}`;
      дни.push(создать("button", {
        type: "button",
        класс: классы.join(" "),
        текст: String(д.getDate()),
        title: подсказка,
        "aria-label": подсказка,
        "aria-pressed": String(iso === выбранный),
        // Клик по дню — показать задачи на этот день; повторный клик — снять выбор
        onclick: () => document.dispatchEvent(new CustomEvent("mizuyori:день",
          { detail: iso === выбранный ? null : iso })),
      }));
    }
    $("календарь-дни").replaceChildren(...дни);
  }

  function листать(насколько) {
    показанный = new Date(показанный.getFullYear(), показанный.getMonth() + насколько, 1);
    нарисоватьКалендарь();
  }

  $("календарь-назад").addEventListener("click", () => листать(-1));
  $("календарь-вперёд").addEventListener("click", () => листать(1));
  $("календарь-месяц").addEventListener("click", () => {
    показанный = new Date();
    показанный.setDate(1);
    нарисоватьКалендарь();
  });

  // ---- Связь с задачами ----

  document.addEventListener("mizuyori:задачи", (событие) => {
    поДням = new Map();
    for (const задача of событие.detail) {
      if (!задача.срок) continue;
      const счёт = поДням.get(задача.срок) || { открыто: 0, сделано: 0 };
      if (задача.готово) счёт.сделано++; else счёт.открыто++;
      поДням.set(задача.срок, счёт);
    }
    нарисоватьКалендарь();
  });

  document.addEventListener("mizuyori:день", (событие) => {
    выбранный = событие.detail;
    if (выбранный) {
      // Если день из другого месяца — переходим на его месяц
      const [г, м] = выбранный.split("-").map(Number);
      показанный = new Date(г, м - 1, 1);
    }
    нарисоватьКалендарь();
  });

  обновитьЧасы();
  нарисоватьКалендарь();
}

// ---- Вокзальные часы ------------------------------------------------------
// Как железнодорожные часы: секундная стрелка с красным диском обегает круг за ~58,5 с и замирает на 12,
// ждёт сигнала, и минутная стрелка делает «шаг» с лёгким отскоком. Тени, блик стекла, подсветка текущей
// секунды и кольцо-вспышка на каждой минуте. При «уменьшить анимацию» стрелки просто переходят по секундам.
{
  const место = document.getElementById("вокзал");
  if (место) строитьВокзал(место);

  function строитьВокзал(корень) {
    const NS = "http://www.w3.org/2000/svg";
    const э = (тег, атр = {}, ...дети) => {
      const у = document.createElementNS(NS, тег);
      for (const [к, з] of Object.entries(атр)) у.setAttribute(к, з);
      у.append(...дети);
      return у;
    };
    const спокойно = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const ПЕРИОД = 58.5;                         // секунд на оборот, остальное — пауза на 12

    // деления: 60 тонких, 12 толстых; живая — та, на которой секундная стрелка
    const деления = [];
    for (let и = 0; и < 60; и++) {
      const час = и % 5 === 0;
      деления.push(э("rect", {
        class: "в-деление" + (час ? " час" : ""),
        x: час ? 98.3 : 99.3, y: 6, width: час ? 3.4 : 1.4, height: час ? 12 : 5,
        transform: `rotate(${и * 6} 100 100)`,
      }));
    }
    const часовая = э("g", { class: "в-стрелка в-часовая" },
      э("rect", { x: 96.6, y: 50, width: 6.8, height: 58, rx: 1.4 }));
    const минутная = э("g", { class: "в-стрелка в-минутная" },
      э("rect", { x: 97.4, y: 20, width: 5.2, height: 92, rx: 1.2 }));
    const диск = э("circle", { class: "в-диск", cx: 100, cy: 32, r: 7.2 });
    const секундная = э("g", { class: "в-секундная" },
      э("line", { x1: 100, y1: 120, x2: 100, y2: 38, class: "в-нить" }),
      диск,
      э("circle", { class: "в-ось", cx: 100, cy: 100, r: 3.6 }));
    const кольцо = э("circle", { class: "в-кольцо", cx: 100, cy: 100, r: 95 });

    const svg = э("svg", { viewBox: "0 0 200 200", class: "в-циферблат", role: "img", "aria-label": "Часы" },
      э("defs", {},
        э("linearGradient", { id: "в-блик", x1: "0", y1: "0", x2: "1", y2: "1" },
          э("stop", { offset: "0", "stop-color": "#fff", "stop-opacity": ".16" }),
          э("stop", { offset: ".5", "stop-color": "#fff", "stop-opacity": ".03" }),
          э("stop", { offset: "1", "stop-color": "#fff", "stop-opacity": "0" })),
        э("clipPath", { id: "в-обрезка" }, э("circle", { cx: 100, cy: 100, r: 94 }))),
      э("circle", { class: "в-обод", cx: 100, cy: 100, r: 97 }),
      э("circle", { class: "в-лицо", cx: 100, cy: 100, r: 93 }),
      кольцо,
      э("g", {}, ...деления),
      э("text", { class: "в-надпись", x: 100, y: 70, "text-anchor": "middle" }, "MIZUYORI"),
      э("g", { class: "в-стрелки" }, часовая, минутная, секундная),
      э("ellipse", { class: "в-блик", cx: 66, cy: 52, rx: 46, ry: 20, transform: "rotate(-38 66 52)", fill: "url(#в-блик)", "clip-path": "url(#в-обрезка)" }));
    корень.append(svg);

    const живые = svg.querySelectorAll(".в-деление");
    let минутВсего = null, прошлаяСекунда = -1, прошлаяПометка = "";

    function кадр() {
      const т = new Date();
      const с = т.getSeconds() + т.getMilliseconds() / 1000;
      const минут = т.getHours() * 60 + т.getMinutes();

      // минутная и часовая: накопленный угол (без обнуления), чтобы переход шёл вперёд, а не откатывался
      if (минутВсего !== минут) {
        const первый = минутВсего === null;
        минутВсего = минут;
        минутная.style.transform = `rotate(${минут * 6}deg)`;
        часовая.style.transform = `rotate(${минут * 0.5}deg)`;
        if (первый) {                           // при загрузке — сразу на место, без отскока
          for (const г of [минутная, часовая]) { г.style.transition = "none"; г.getBoundingClientRect(); г.style.transition = ""; }
        } else {
          кольцо.classList.remove("вспышка"); void кольцо.getBoundingClientRect(); кольцо.classList.add("вспышка");
        }
        svg.setAttribute("aria-label", `Часы: ${двузначное(т.getHours())}:${двузначное(т.getMinutes())}`);
      }

      // секундная: 58,5 с до 12, потом пауза; минутная «шагает», когда секундная замерла
      const целая = Math.floor(с);
      const угол = спокойно ? целая * 6 : Math.min(с, ПЕРИОД) / ПЕРИОД * 360;
      секундная.setAttribute("transform", `rotate(${угол} 100 100)`);
      const ждёт = !спокойно && с >= ПЕРИОД;
      диск.classList.toggle("ждёт", ждёт);

      const живая = Math.round(угол / 6) % 60;
      if (живая !== прошлаяСекунда) {
        живые[прошлаяСекунда]?.classList.remove("живая");
        живые[живая].classList.add("живая");
        прошлаяСекунда = живая;
      }
      requestAnimationFrame(кадр);
    }
    requestAnimationFrame(кадр);
  }
}
