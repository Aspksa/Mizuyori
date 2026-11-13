// =============================================================================
// Герои агентов, вид сверху: большая голова с волосами или шлемом, светящиеся глаза под чёлкой,
// наушники, форма по роли, предмет в руке и голограмма в другой. У каждого агента свои волосы,
// головной убор, одежда, аксессуар, предмет и значок голограммы.
// window.персонаж(ключ) → <svg class="персонаж">; старые роботы остаются в window.персонажРобот.
// =============================================================================
{
  const NS = "http://www.w3.org/2000/svg";
  let счётчик = 0;

  // ---- палитры -------------------------------------------------------------------------------
  const ВОЛОСЫ = { серебро: "#cfd3de", чёрный: "#2b2f3d", каштан: "#6b4a3a", блонд: "#e6c98a", рыжий: "#c4602d", бирюза: "#3fc7c0",
    сирень: "#a888e0", белый: "#f1f3f8", розовый: "#e88aa8", синий: "#4a6bd6", золото: "#f2c230" };
  const ФОРМА = { синий: "#17243f", графит: "#232733", бордо: "#4a1a2c", зелёный: "#12372c", коричневый: "#4a3322", халат: "#eef1f7",
    оранж: "#2a2f3d", хаки: "#4a5236", фиолет: "#2f2350", бирюза: "#14444a" };
  const КОЖА = ["#f4dccb", "#e8c4a6", "#d3a583"];

  const светлее = (hex, т) => {
    const н = parseInt(hex.slice(1), 16);
    const р = (х) => Math.round(х + (255 - х) * т);
    return `#${[(н >> 16) & 255, (н >> 8) & 255, н & 255].map((х) => р(х).toString(16).padStart(2, "0")).join("")}`;
  };
  const темнее = (hex, к) => {
    const н = parseInt(hex.slice(1), 16);
    const р = (х) => Math.max(0, Math.min(255, Math.round(х * к)));
    return `#${[(н >> 16) & 255, (н >> 8) & 255, н & 255].map((х) => р(х).toString(16).padStart(2, "0")).join("")}`;
  };

  // ключ → [волосы, цвет волос, форма, цвет формы, наушники, аксессуар, предмет, значок голограммы]
  const П = {
    чат: ["двойной", "бирюза", "худи", "бирюза", 1, "гарнитура", "телефон", "чат"],
    память: ["каре", "каштан", "халат", "халат", 1, "очки", "папка", "мозг"],
    смысл: ["рога", "сирень", "худи", "фиолет", 1, "", "шар", "связь"],
    сводка: ["пучок", "серебро", "пиджак", "графит", 1, "очки", "свиток", "документ"],
    цели: ["хвост", "розовый", "пиджак", "бордо", 1, "", "флаг", "цель"],
    мнения: ["двойной", "розовый", "худи", "бордо", 0, "", "сердце", "сердце"],
    смотрящий: ["ёжик", "чёрный", "мундир", "синий", 1, "визор", "планшет", "лупа"],
    кадровик: ["каре", "рыжий", "пиджак", "фиолет", 1, "бейдж", "папка", "люди"],
    контрагенты: ["ёжик", "каштан", "пиджак", "графит", 0, "галстук", "портфель", "связь"],
    секретарь: ["хвост", "блонд", "пиджак", "бирюза", 1, "гарнитура", "блокнот", "письмо"],
    инженер: ["каска", "золото", "жилет", "оранж", 1, "", "чертёж", "шестерня"],
    механик: ["кепка", "чёрный", "комбез", "хаки", 0, "", "ключ", "гаечный"],
    диспетчер: ["ёжик", "бирюза", "пиджак", "синий", 1, "гарнитура", "планшет", "часы"],
    трассировщик: ["очки-лоб", "сирень", "худи", "графит", 1, "", "лупа", "маршрут"],
    мастер_ремзоны: ["каска", "белый", "комбез", "синий", 0, "", "ключ", "шестерня"],
    дефектовщик: ["кепка", "каштан", "фартук", "коричневый", 0, "очки", "планшет", "галка"],
    шины_акб: ["шапка", "чёрный", "комбез", "графит", 0, "", "шина", "колесо"],
    снабженец: ["кепка", "синий", "жилет", "зелёный", 0, "", "коробка", "тележка"],
    склад: ["каска", "золото", "жилет", "оранж", 0, "", "коробка", "ящик"],
    проверяющий: ["ёжик", "серебро", "пиджак", "графит", 1, "очки", "планшет", "галка"],
    охрана: ["каска", "белый", "жилет", "оранж", 1, "", "щит", "щит"],
    сроки: ["берет", "сирень", "пиджак", "фиолет", 1, "", "часы", "календарь"],
    водитель: ["кепка", "каштан", "комбез", "хаки", 0, "", "руль", "машина"],
    экономист: ["пучок", "блонд", "пиджак", "синий", 1, "очки", "монеты", "график"],
    аналитик: ["хвост", "синий", "худи", "синий", 1, "очки", "планшет", "пирог"],
    плановик: ["каре", "серебро", "пиджак", "графит", 1, "", "блокнот", "календарь"],
    себестоимость: ["ёжик", "бирюза", "пиджак", "бирюза", 0, "", "калькулятор", "монета"],
    цены: ["двойной", "рыжий", "пиджак", "коричневый", 1, "", "ценник", "процент"],
    парк_экономист: ["кепка", "чёрный", "пиджак", "зелёный", 1, "", "машинка", "машина"],
    главбух: ["пучок", "серебро", "пиджак", "зелёный", 1, "очки", "книга", "монета"],
    замглав: ["каре", "каштан", "пиджак", "зелёный", 1, "", "папка", "график"],
    ос_ведущий: ["ёжик", "чёрный", "пиджак", "синий", 0, "", "машинка", "машина"],
    ос_бух: ["хвост", "блонд", "пиджак", "графит", 1, "очки", "калькулятор", "машина"],
    мат_ведущий: ["кепка", "синий", "жилет", "зелёный", 0, "", "коробка", "ящик"],
    зап_бух: ["двойной", "рыжий", "фартук", "коричневый", 0, "", "шестерня", "шестерня"],
    зп_ведущий: ["каре", "розовый", "пиджак", "бордо", 1, "", "монеты", "монета"],
    зп_водители: ["кепка", "чёрный", "пиджак", "хаки", 0, "", "руль", "монета"],
    зп_ауп: ["пучок", "сирень", "пиджак", "фиолет", 1, "", "папка", "монета"],
    кон_ведущий: ["ёжик", "каштан", "пиджак", "бирюза", 1, "", "папка", "связь"],
    реализация: ["хвост", "бирюза", "пиджак", "бирюза", 0, "", "грузовик", "документ"],
    подотчёт: ["каре", "блонд", "пиджак", "графит", 1, "", "портфель", "галка"],
    налоги: ["пучок", "чёрный", "мундир", "графит", 1, "очки", "щит", "процент"],
    касса_старший: ["ёжик", "рыжий", "жилет", "коричневый", 1, "", "касса", "монета"],
    кассир: ["хвост", "розовый", "фартук", "бордо", 0, "", "касса", "монета"],
    делопроизводитель: ["каре", "серебро", "пиджак", "графит", 1, "очки", "папка", "документ"],
    архивариус: ["пучок", "белый", "халат", "халат", 1, "очки", "коробка", "замок"],
    гсмконтроль: ["кепка", "синий", "комбез", "синий", 0, "", "канистра", "бензин"],
    бухгалтер: ["ёжик", "каштан", "пиджак", "зелёный", 1, "", "калькулятор", "монета"],
    юрист: ["пучок", "серебро", "мантия", "синий", 1, "", "книга", "весы"],
    дог_ведущий: ["пучок", "каштан", "мантия", "синий", 1, "", "книга", "документ"],
    дог_перевозки: ["хвост", "рыжий", "пиджак", "синий", 1, "", "грузовик", "документ"],
    дог_аренда: ["каре", "бирюза", "пиджак", "синий", 1, "", "ключ", "ключик"],
    прет_ведущий: ["ёжик", "чёрный", "мантия", "бордо", 1, "", "книга", "весы"],
    прет_дтп: ["двойной", "розовый", "пиджак", "бордо", 1, "", "машинка", "щит"],
    прет_дебиторка: ["каре", "синий", "пиджак", "бордо", 1, "", "монеты", "колокол"],
    закуп_юрист: ["хвост", "серебро", "пиджак", "фиолет", 1, "", "ценник", "галка"],
    регуляция: ["ёжик", "блонд", "мундир", "синий", 1, "", "щит", "щит"],
    дог_архив: ["пучок", "сирень", "халат", "халат", 1, "очки", "папка", "замок"],
  };
  const ВОЖДИ = new Set(["главбух", "юрист"]);
  const ЗВЁЗДЫ = new Set(["замглав", "ос_ведущий", "мат_ведущий", "зп_ведущий", "кон_ведущий", "касса_старший", "мастер_ремзоны", "плановик", "цены",
    "дог_ведущий", "прет_ведущий", "закуп_юрист", "регуляция", "дог_архив", "инженер", "снабженец", "охрана", "налоги", "экономист", "смотрящий", "чат"]);

  // ---- голограммы: значок внутри стеклянной панели (рисуется в квадрате 24×24) -----------------
  const О = 'fill="none" stroke="var(--cg)" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"';
  const ЗНАЧКИ = {
    весы: `<path d="M12 3V20M7 20H17M4 7H20M4 7L1.5 14H6.5ZM20 7L17.5 14H22.5Z" ${О}/>`,
    график: `<path d="M3 21V3M3 21H21M6 16L10 11L14 14L20 6" ${О}/>`,
    шестерня: `<circle cx="12" cy="12" r="3.6" ${О}/><path d="M12 2.5V6M12 18V21.5M2.5 12H6M18 12H21.5M5.3 5.3L7.8 7.8M16.2 16.2L18.7 18.7M18.7 5.3L16.2 7.8M7.8 16.2L5.3 18.7" ${О}/>`,
    машина: `<path d="M3 16V12L6 7H18L21 12V16ZM3 16H21M7 19.5A1.6 1.6 0 1 0 7 16.3M17 19.5A1.6 1.6 0 1 0 17 16.3" ${О}/>`,
    щит: `<path d="M12 2L20 5V12Q20 18.5 12 22Q4 18.5 4 12V5Z" ${О}/><path d="M8.5 12L11 14.6L15.8 9" ${О}/>`,
    монета: `<circle cx="12" cy="12" r="9" ${О}/><path d="M14.8 8.5Q13.8 7.2 12 7.2Q9.4 7.2 9.4 9.2Q9.4 11 12 11.4Q14.6 11.9 14.6 13.8Q14.6 16.2 12 16.2Q10 16.2 9 14.8M12 5.2V7.2M12 16.2V18.4" ${О}/>`,
    документ: `<path d="M6 2.5H14L19 7.5V21.5H6ZM14 2.5V7.5H19M9 12H16M9 15.5H16M9 19H13" ${О}/>`,
    часы: `<circle cx="12" cy="12" r="9" ${О}/><path d="M12 6.5V12L15.8 14" ${О}/>`,
    ключик: `<circle cx="8" cy="12" r="4.6" ${О}/><path d="M12.6 12H22M18.5 12V16M21.5 12V15" ${О}/>`,
    процент: `<path d="M19 5L5 19" ${О}/><circle cx="7" cy="7" r="2.6" ${О}/><circle cx="17" cy="17" r="2.6" ${О}/>`,
    гаечный: `<path d="M14.7 6.3A4.6 4.6 0 0 0 20.2 4L17.4 6.8L17.4 9.4L20 9.4L22.8 6.6A4.6 4.6 0 0 1 17 14.3L7.2 22A2.2 2.2 0 0 1 3.8 18.6L11.4 8.8A4.6 4.6 0 0 1 14.7 6.3Z" transform="scale(.9) translate(-1 1)" ${О}/>`,
    сердце: `<path d="M12 21Q3 14 3 8.4A4.8 4.8 0 0 1 12 6.4A4.8 4.8 0 0 1 21 8.4Q21 14 12 21Z" ${О}/>`,
    цель: `<circle cx="12" cy="12" r="9" ${О}/><circle cx="12" cy="12" r="5" ${О}/><circle cx="12" cy="12" r="1.4" fill="var(--cg)"/>`,
    мозг: `<path d="M9 4A3.4 3.4 0 0 0 5.6 7.4A3.4 3.4 0 0 0 4 12.6A3.6 3.6 0 0 0 7.6 18A3.2 3.2 0 0 0 12 20.2V4.6A3.2 3.2 0 0 0 9 4ZM15 4A3.4 3.4 0 0 1 18.4 7.4A3.4 3.4 0 0 1 20 12.6A3.6 3.6 0 0 1 16.4 18A3.2 3.2 0 0 1 12 20.2" ${О}/>`,
    чат: `<path d="M4 4H20V16H12L7 20.5V16H4Z" ${О}/><path d="M8 9H16M8 12.5H13" ${О}/>`,
    связь: `<path d="M10 14A4 4 0 0 0 15.6 14.2L19 10.8A4 4 0 0 0 13.4 5.2L12 6.6M14 10A4 4 0 0 0 8.4 9.8L5 13.2A4 4 0 0 0 10.6 18.8L12 17.4" ${О}/>`,
    лупа: `<circle cx="10.5" cy="10.5" r="6.5" ${О}/><path d="M15.4 15.4L21 21" ${О}/>`,
    люди: `<circle cx="9" cy="8" r="3.4" ${О}/><path d="M2.5 20Q2.5 13.6 9 13.6Q15.5 13.6 15.5 20M16 4.8A3.2 3.2 0 0 1 16 11.2M18 13.8Q21.5 14.6 21.5 20" ${О}/>`,
    письмо: `<path d="M3 5.5H21V18.5H3ZM3 6L12 13L21 6" ${О}/>`,
    маршрут: `<circle cx="6" cy="18" r="2.4" ${О}/><circle cx="18" cy="6" r="2.4" ${О}/><path d="M8 17.4C14 17.4 9.6 6.6 15.6 6.6" ${О}/>`,
    галка: `<circle cx="12" cy="12" r="9" ${О}/><path d="M7.4 12.4L10.6 15.6L16.8 8.8" ${О}/>`,
    колесо: `<circle cx="12" cy="12" r="9" ${О}/><circle cx="12" cy="12" r="3.2" ${О}/><path d="M12 3V8.8M12 15.2V21M3 12H8.8M15.2 12H21" ${О}/>`,
    тележка: `<path d="M2.5 4H5.5L8 15.5H18.5L20.5 7.5H6.4M9.5 19.6A1.4 1.4 0 1 0 9.5 16.8M17 19.6A1.4 1.4 0 1 0 17 16.8" ${О}/>`,
    ящик: `<path d="M3 7.5L12 3L21 7.5V16.5L12 21L3 16.5ZM3 7.5L12 12L21 7.5M12 12V21" ${О}/>`,
    календарь: `<path d="M4 5.5H20V20.5H4ZM4 10H20M8.5 3V7.5M15.5 3V7.5" ${О}/><path d="M8 14H10M12 14H14M8 17H10" ${О}/>`,
    пирог: `<path d="M12 3A9 9 0 1 0 21 12H12Z" ${О}/><path d="M14.5 2.7A9 9 0 0 1 21.3 9.5H14.5Z" ${О}/>`,
    замок: `<rect x="5" y="10.5" width="14" height="10.5" rx="2" ${О}/><path d="M8 10.5V7.5A4 4 0 0 1 16 7.5V10.5M12 14.5V17.5" ${О}/>`,
    бензин: `<path d="M5 21V4.5Q5 3 6.5 3H13Q14.5 3 14.5 4.5V21M3.5 21H16M14.5 8H17Q19 8 19 10V16A1.5 1.5 0 0 0 22 16V8.5L19.5 6" ${О}/><path d="M7.4 7H12" ${О}/>`,
    колокол: `<path d="M6 17V11A6 6 0 0 1 18 11V17L20 19H4ZM10 21.5A2.2 2.2 0 0 0 14 21.5M12 3V5" ${О}/>`,
  };

  const голограмма = (знак) => `<g transform="translate(101 64)"><g class="плав п2">
      <path d="M12 48L7 36H23L18 48Z" fill="var(--cg)" opacity=".16"/>
      <circle cx="15" cy="16" r="21" fill="url(#§a)"/>
      <circle class="кольцо" cx="15" cy="16" r="19" fill="none" stroke="var(--cg)" stroke-width="1" stroke-dasharray="5 4" opacity=".75"/>
      <circle class="кольцо" cx="15" cy="16" r="22.5" fill="none" stroke="var(--cl)" stroke-width=".6" stroke-dasharray="1.5 6" opacity=".5" style="animation-direction:reverse"/>
      <rect x="2" y="3" width="26" height="26" rx="5" fill="var(--cg)" fill-opacity=".2" stroke="var(--cg)" stroke-opacity=".9" stroke-width="1.4"/>
      <rect x="2" y="3" width="26" height="9" rx="5" fill="#fff" fill-opacity=".16"/>
      <path d="M4 15H26M4 20H26M4 25H26" stroke="var(--cg)" stroke-opacity=".13"/>
      <path d="M2 8V5Q2 3 4 3H7M28 8V5Q28 3 26 3H23M2 24V27Q2 29 4 29H7M28 24V27Q28 29 26 29H23" fill="none" stroke="#fff" stroke-opacity=".8" stroke-width="1.2" stroke-linecap="round"/>
      <g transform="translate(6.5 7.5) scale(.73)">${ЗНАЧКИ[знак] || ЗНАЧКИ.документ}</g>
      <path d="M8 33Q15 38 22 33" fill="none" stroke="var(--cg)" stroke-width="1.2" opacity=".6"/>
    </g></g>`;

  // ---- предметы в левой руке (кисть примерно в точке 24,118) ---------------------------------
  const ЗОЛ = "#e8b33a";
  const ПРЕДМЕТЫ = {
    книга: (ц) => `<g transform="rotate(-10 20 112)"><g class="плав"><rect x="6" y="94" width="26" height="34" rx="2.6" fill="${ц || "#1d2238"}" stroke="${ЗОЛ}" stroke-width="1.3"/><rect x="9" y="97" width="3" height="28" fill="#f3e6bf"/><path d="M21 106V112M17 109H25M18 116Q21 120 24 116" stroke="${ЗОЛ}" stroke-width="1.1" fill="none"/></g></g>`,
    папка: () => `<g transform="rotate(-8 20 112)"><g class="плав"><path d="M6 98H16L19 94H32V128H6Z" fill="#e0a64a" stroke="#8a5a14" stroke-width="1.2"/><rect x="9" y="102" width="20" height="22" rx="1.5" fill="#fff"/><path d="M12 108H26M12 113H26M12 118H22" stroke="#9aa3b8" stroke-width="1.2"/></g></g>`,
    планшет: () => `<g transform="rotate(-8 20 112)"><g class="плав"><rect x="6" y="94" width="26" height="34" rx="3.4" fill="#1a2030" stroke="#8d97b3" stroke-width="1.4"/><rect x="9" y="98" width="20" height="26" rx="1.6" fill="var(--cg)" fill-opacity=".22"/><path d="M12 106H26M12 111H26M12 116H21" stroke="var(--cg)" stroke-width="1.3"/></g></g>`,
    блокнот: () => `<g transform="rotate(-8 20 112)"><g class="плав"><rect x="7" y="96" width="24" height="32" rx="2" fill="#fff" stroke="#9aa3b8" stroke-width="1.2"/><path d="M7 102H31" stroke="var(--cg)" stroke-width="3"/><path d="M11 109H27M11 114H27M11 119H21" stroke="#aeb6c8" stroke-width="1.2"/></g></g>`,
    свиток: () => `<g transform="rotate(-14 20 112)"><g class="плав"><rect x="9" y="92" width="22" height="36" rx="3" fill="#f1e2b8" stroke="#a98b3a" stroke-width="1.2"/><path d="M13 100H27M13 105H27M13 110H23" stroke="#a98b3a" stroke-width="1.2"/><ellipse cx="20" cy="92" rx="11" ry="3" fill="#e2cf92" stroke="#a98b3a"/></g></g>`,
    чертёж: () => `<g transform="rotate(-8 20 112)"><g class="плав"><rect x="4" y="96" width="30" height="30" rx="2" fill="#183a6a" stroke="#7fb2ff" stroke-width="1.2"/><path d="M8 118L16 104L24 114L30 100" stroke="#cfe3ff" stroke-width="1.3" fill="none"/><circle cx="16" cy="104" r="2" fill="#cfe3ff"/></g></g>`,
    флаг: () => `<g class="плав"><path d="M12 128V90" stroke="#c9ced8" stroke-width="2.4"/><path d="M12 91H32L28 98L32 105H12Z" fill="var(--cg)" stroke="var(--cd)" stroke-width="1.2"/></g>`,
    телефон: () => `<g transform="rotate(-8 20 112)"><g class="плав"><rect x="9" y="96" width="19" height="32" rx="4" fill="#1a2030" stroke="#8d97b3" stroke-width="1.4"/><rect x="11.5" y="101" width="14" height="22" rx="1.5" fill="var(--cg)" fill-opacity=".25"/><circle cx="18.5" cy="125.5" r="1.1" fill="#8d97b3"/></g></g>`,
    шар: () => `<g class="плав"><circle cx="20" cy="108" r="14" fill="var(--cg)" fill-opacity=".22" stroke="var(--cg)" stroke-width="1.4"/><circle cx="15" cy="103" r="4" fill="#fff" fill-opacity=".5"/><path d="M8 112Q20 120 32 108" stroke="var(--cl)" stroke-width="1" fill="none"/></g>`,
    сердце: () => `<g class="плав"><path d="M20 128Q4 116 4 104A8 8 0 0 1 20 100A8 8 0 0 1 36 104Q36 116 20 128Z" fill="var(--cg)" stroke="var(--cd)" stroke-width="1.2"/><ellipse cx="12" cy="104" rx="3" ry="2" fill="#fff" fill-opacity=".6"/></g>`,
    портфель: () => `<g class="плав"><rect x="4" y="102" width="32" height="24" rx="3.5" fill="#8a5a2a" stroke="#4d2f10" stroke-width="1.3"/><path d="M14 102V97H26V102M4 112H36" stroke="#4d2f10" stroke-width="1.3" fill="none"/><rect x="17" y="109" width="6" height="6" rx="1" fill="${ЗОЛ}"/></g>`,
    ключ: () => `<g transform="rotate(-30 20 112)"><g class="плав"><path d="M10 124L26 96" stroke="#c9ced8" stroke-width="5" stroke-linecap="round"/><path d="M22 100A8 8 0 1 1 32 90L28 96Z" fill="#c9ced8" stroke="#6c7589" stroke-width="1.2"/><circle cx="29" cy="93" r="2.6" fill="#1a2030"/></g></g>`,
    лупа: () => `<g class="плав"><circle cx="16" cy="104" r="11" fill="var(--cg)" fill-opacity=".14" stroke="#c9ced8" stroke-width="3.4"/><path d="M24 112L34 126" stroke="#c9ced8" stroke-width="4" stroke-linecap="round"/><ellipse cx="12" cy="100" rx="3" ry="1.8" fill="#fff" fill-opacity=".6"/></g>`,
    шина: () => `<g class="плав"><circle cx="20" cy="110" r="16" fill="#1a1d28" stroke="#3a4156" stroke-width="2"/><circle cx="20" cy="110" r="8" fill="#6c7589" stroke="#aeb6c8"/><circle cx="20" cy="110" r="2.5" fill="#1a1d28"/></g>`,
    коробка: () => `<g class="плав"><path d="M4 102L20 95L36 102V120L20 128L4 120Z" fill="#c89a5b" stroke="#7a5528" stroke-width="1.3"/><path d="M4 102L20 109L36 102M20 109V128" stroke="#7a5528" stroke-width="1.3" fill="none"/><path d="M12 98.5L28 105.5" stroke="#e8d3a0" stroke-width="2.4"/></g>`,
    щит: () => `<g class="плав"><path d="M20 94L36 99V112Q36 122 20 128Q4 122 4 112V99Z" fill="#0a1220" stroke="var(--cl)" stroke-width="1.7"/><path d="M13 110L18 115L28 104" stroke="var(--cg)" stroke-width="2.2" fill="none" stroke-linecap="round"/></g>`,
    часы: () => `<g class="плав"><circle cx="20" cy="110" r="15" fill="#f4f6fb" stroke="#8d97b3" stroke-width="2"/><path d="M20 110V100M20 110L27 114" stroke="#232733" stroke-width="2" stroke-linecap="round"/><circle cx="20" cy="110" r="1.6" fill="#232733"/></g>`,
    руль: () => `<g class="плав"><circle cx="20" cy="110" r="15" fill="none" stroke="#252a38" stroke-width="5"/><circle cx="20" cy="110" r="15" fill="none" stroke="var(--cl)" stroke-width="1.1"/><circle cx="20" cy="110" r="4.6" fill="#252a38" stroke="var(--cl)"/><path d="M20 114.6V125M16 108L6 104M24 108L34 104" stroke="#252a38" stroke-width="3.4"/></g>`,
    монеты: () => `<g class="плав">${[0, 1, 2, 3].map((и) => `<ellipse cx="20" cy="${124 - и * 6}" rx="13" ry="4.6" fill="#f0c24a" stroke="#a97500" stroke-width="1.1"/>`).join("")}<ellipse cx="20" cy="100" rx="13" ry="4.6" fill="#ffe27a" stroke="#a97500"/><text x="20" y="102.4" text-anchor="middle" font-size="7" font-weight="800" fill="#a97500">₽</text></g>`,
    калькулятор: () => `<g transform="rotate(-8 20 112)"><g class="плав"><rect x="6" y="94" width="28" height="34" rx="3.6" fill="#2a2f3d" stroke="#8d97b3" stroke-width="1.3"/><rect x="9" y="98" width="22" height="8" rx="1.6" fill="var(--cg)" fill-opacity=".35"/>${[0, 1, 2].map((р) => [0, 1, 2].map((с) => `<rect x="${9.6 + с * 7.6}" y="${109 + р * 6.4}" width="5" height="4.2" rx="1" fill="#aeb6c8"/>`).join("")).join("")}</g></g>`,
    ценник: () => `<g class="плав"><path d="M4 106L14 94H36V122H14Z" fill="#fff" stroke="var(--cd)" stroke-width="1.4"/><circle cx="12" cy="106" r="2.4" fill="var(--cd)"/><text x="25" y="113" text-anchor="middle" font-size="13" font-weight="800" fill="var(--cd)">₽</text></g>`,
    машинка: () => `<g class="плав"><path d="M2 116V108L8 98H30L38 108V116Z" fill="var(--c1)" stroke="var(--cd)" stroke-width="1.3"/><path d="M10 100H28L33 108H6Z" fill="#cfe3ff" fill-opacity=".8"/><circle cx="11" cy="117" r="4.6" fill="#1a1d28" stroke="#8d97b3"/><circle cx="29" cy="117" r="4.6" fill="#1a1d28" stroke="#8d97b3"/></g>`,
    грузовик: () => `<g class="плав"><rect x="0" y="100" width="24" height="18" rx="2" fill="#e8edf7" stroke="#8d97b3" stroke-width="1.2"/><path d="M24 106H32L38 112V118H24Z" fill="var(--c1)" stroke="var(--cd)" stroke-width="1.2"/><circle cx="9" cy="119" r="4.4" fill="#1a1d28" stroke="#8d97b3"/><circle cx="30" cy="119" r="4.4" fill="#1a1d28" stroke="#8d97b3"/></g>`,
    касса: () => `<g class="плав"><rect x="2" y="112" width="36" height="16" rx="3" fill="#3a4156" stroke="#8d97b3" stroke-width="1.2"/><path d="M8 112L10 98H30L32 112Z" fill="#cfd6e4" stroke="#8d97b3" stroke-width="1.2"/><rect x="12" y="101" width="16" height="6" rx="1.2" fill="var(--cg)" fill-opacity=".5"/><path d="M8 120H32" stroke="#aeb6c8" stroke-width="1.6"/></g>`,
    канистра: () => `<g class="плав"><path d="M6 100H24L32 108V126H6Z" fill="#d84a3a" stroke="#7d1f12" stroke-width="1.3"/><rect x="8" y="94" width="10" height="7" rx="1.4" fill="#7d1f12"/><path d="M13 108H25M13 114H25" stroke="#ffb3a6" stroke-width="1.4"/></g>`,
    шестерня: () => `<g class="плав"><circle cx="20" cy="110" r="15" fill="#aeb6c8" stroke="#6c7589" stroke-width="1.4" stroke-dasharray="4 2.6"/><circle cx="20" cy="110" r="11" fill="#c9ced8" stroke="#6c7589"/><circle cx="20" cy="110" r="4.6" fill="#232733"/></g>`,
  };

  // ---- одежда --------------------------------------------------------------------------------
  const ТУЛОВИЩЕ = "M31 99Q30 88 42 88H78Q90 88 89 99L87 126Q60 134 33 126Z";
  function одежда(тип, ц) {
    const т = темнее(ц, .72), св = ц === ФОРМА.халат;
    const кант = `<path d="${ТУЛОВИЩЕ}" fill="none" stroke="${ЗОЛ}" stroke-width="1.5" stroke-linejoin="round"/>`;
    const жабо = `<path d="M51 91H69L65 110L60 101L55 110Z" fill="#f6f7fb" stroke="#cfd4e0" stroke-width="1"/><path d="M56 96L60 101L64 96" stroke="#cfd4e0" fill="none"/>`;
    const лацканы = `<path d="M48 90L60 114L52 128M72 90L60 114L68 128" fill="none" stroke="${ЗОЛ}" stroke-width="1.5" stroke-linecap="round"/><circle cx="60" cy="117" r="2" fill="${ЗОЛ}"/>`;
    const основа = `<path d="${ТУЛОВИЩЕ}" fill="url(#§c)" stroke="${т}" stroke-width="1.4" stroke-linejoin="round"/><path d="${ТУЛОВИЩЕ}" fill="url(#§s)" opacity=".55"/>`
      + `<path d="M43 100Q41 112 44 125M77 100Q79 112 76 125M60 121V129M50 118Q54 122 52 128M70 118Q66 122 68 128" stroke="#000" stroke-opacity="${св ? .1 : .24}" stroke-width="1.2" fill="none" stroke-linecap="round"/>`
      + `<path d="M36 95Q44 89.5 56 89.5" stroke="#fff" stroke-opacity="${св ? .8 : .3}" stroke-width="2.6" fill="none" stroke-linecap="round"/>`
      + `<path d="${ТУЛОВИЩЕ}" fill="none" stroke="url(#§r)" stroke-width="2.2" stroke-linejoin="round"/>`;
    switch (тип) {
      case "мантия": return основа + `<path d="M33 126L36 98M87 126L84 98" stroke="${ЗОЛ}" stroke-width="1.2" opacity=".7"/>` + кант + лацканы + жабо;
      case "халат": return основа + `<path d="M48 90L60 112L56 128M72 90L60 112L64 128" fill="none" stroke="var(--c1)" stroke-width="2" stroke-linecap="round"/><rect x="38" y="108" width="12" height="11" rx="2" fill="none" stroke="#c4cbdc" stroke-width="1.2"/><circle cx="60" cy="112" r="1.8" fill="var(--c1)"/>`;
      case "жилет": return основа + `<path d="M38 90H52L61 128H35ZM82 90H68L59 128H85Z" fill="#ff8a2a" stroke="#a84d0a" stroke-width="1.1"/><path d="M37 106H55M37 116H57M83 106H65M83 116H63" stroke="#f4f6fb" stroke-width="2.6" opacity=".9"/>`;
      case "комбез": return основа + `<path d="M46 108H74V127Q60 131 46 127Z" fill="${т}" stroke="${темнее(ц, .55)}" stroke-width="1.2"/><path d="M46 108L42 91M74 108L78 91" stroke="${т}" stroke-width="4"/><rect x="52" y="113" width="16" height="8" rx="1.8" fill="none" stroke="${темнее(ц, .5)}" stroke-width="1.1"/><circle cx="46" cy="108" r="2" fill="${ЗОЛ}"/><circle cx="74" cy="108" r="2" fill="${ЗОЛ}"/>`;
      case "мундир": return основа + кант + `<path d="M60 91V128" stroke="${ЗОЛ}" stroke-width="1"/>` + [100, 108, 116].map((у) => `<circle cx="54" cy="${у}" r="1.7" fill="${ЗОЛ}"/><circle cx="66" cy="${у}" r="1.7" fill="${ЗОЛ}"/>`).join("") + `<rect x="31" y="89" width="12" height="4.6" rx="1.6" fill="${ЗОЛ}"/><rect x="77" y="89" width="12" height="4.6" rx="1.6" fill="${ЗОЛ}"/>` + `<path d="M51 91H69L63 99L60 94L57 99Z" fill="#f6f7fb"/>`;
      case "фартук": return основа + `<path d="M43 98H77L75 128Q60 131 45 128Z" fill="${темнее(ц, 1.45)}" stroke="${т}" stroke-width="1.2"/><path d="M43 98L38 90M77 98L82 90" stroke="${т}" stroke-width="2"/><rect x="52" y="112" width="16" height="9" rx="2" fill="none" stroke="${т}" stroke-width="1.1"/>`;
      case "худи": return основа + `<ellipse cx="60" cy="92" rx="17" ry="7" fill="${темнее(ц, 1.25)}" stroke="${т}" stroke-width="1.2"/><path d="M54 98V108M66 98V108" stroke="#e8ebf3" stroke-width="1.5" stroke-linecap="round"/><path d="M42 114Q60 120 78 114L76 126Q60 130 44 126Z" fill="none" stroke="${т}" stroke-width="1.2"/>`;
      default: return основа + кант + лацканы + жабо; // пиджак
    }
  }

  // ---- волосы и головные уборы ----------------------------------------------------------------
  function волосы(тип, цв, id) {
    const в = цв, т = темнее(в, .72);
    const мас = (путь) => `<path d="${путь}" fill="url(#§v)" stroke="${т}" stroke-width="1.3" stroke-linejoin="round"/><path d="${путь}" fill="url(#§h)"/>`;
    const св1 = светлее(в, .5);
    const блики = `<path d="M38 36Q44 27 56 24" stroke="#fff" stroke-width="3.4" stroke-linecap="round" fill="none" opacity=".5"/><path d="M33 46Q34 42 37 39" stroke="#fff" stroke-width="2.2" stroke-linecap="round" fill="none" opacity=".35"/><path d="M82 34Q87 38 88 46" stroke="#fff" stroke-width="1.8" stroke-linecap="round" fill="none" opacity=".22"/>`;
    // чёлка: нижний край волос с зубцами, под ним видны глаза
    const ЧЁЛКА = "M29 58Q27 26 60 21Q93 26 91 58Q91 67 86 73Q79 66 75 71Q67 63 60 72Q53 63 45 71Q41 66 34 73Q29 67 29 58Z";
    const пряди = `<path d="M60 22Q54 40 47 66M60 22Q66 40 73 66M60 22Q58 38 60 70M38 34Q36 50 38 66M82 34Q84 50 82 66" fill="none" stroke="${т}" stroke-width="1.2" opacity=".55"/><path d="M60 22Q56 38 52 66M60 22Q64 38 68 66M44 30Q41 46 42 66M76 30Q79 46 78 66" fill="none" stroke="${св1}" stroke-width="1" opacity=".5"/>`;
    const схема = `<path d="M49 29Q44 42 51 58M71 29Q76 42 69 58" fill="none" stroke="var(--cg)" stroke-width="4.4" stroke-linecap="round" opacity=".22"/><path d="M49 29Q44 42 51 58M71 29Q76 42 69 58" fill="none" stroke="var(--cg)" stroke-width="1.7" stroke-linecap="round" opacity=".98"/><path d="M60 24V33M52 38L56 42" stroke="var(--cg)" stroke-width="1.2" stroke-linecap="round" opacity=".7"/><circle class="узел" cx="51" cy="58" r="2.4"/><circle class="узел" cx="69" cy="58" r="2.4"/><circle cx="51" cy="58" r="4.6" fill="var(--cg)" opacity=".2"/><circle cx="69" cy="58" r="4.6" fill="var(--cg)" opacity=".2"/>`;
    const кольцо = (х, у) => `<rect x="${х - 10}" y="${у}" width="20" height="5" rx="2.4" fill="${ЗОЛ}" stroke="#a97500" stroke-width=".8"/>`;
    const баз = мас(ЧЁЛКА) + пряди + блики + схема;
    const шапкаКупол = (цвет, ободок) => `<path d="M27 56Q26 22 60 20Q94 22 93 56Q93 61 88 61Q60 55 32 61Q27 61 27 56Z" fill="${цвет}" stroke="${темнее(цвет, .65)}" stroke-width="1.3"/><path d="M27 56Q26 22 60 20Q94 22 93 56Q93 61 88 61Q60 55 32 61Q27 61 27 56Z" fill="url(#§h)"/><path d="M36 38Q42 28 54 24" stroke="#fff" stroke-width="4" stroke-linecap="round" fill="none" opacity=".55"/><path d="M32 48Q33 44 36 41" stroke="#fff" stroke-width="2.2" stroke-linecap="round" fill="none" opacity=".35"/>${ободок || ""}`;
    switch (тип) {
      case "пучок": return { зад: `<circle cx="60" cy="19" r="13" fill="url(#§v)" stroke="${т}" stroke-width="1.3"/><circle cx="60" cy="19" r="13" fill="url(#§h)"/><path d="M52 14Q60 8 68 14M54 22Q60 16 66 22" fill="none" stroke="${т}" opacity=".5"/>`, перед: баз + кольцо(60, 28) };
      case "двойной": return { зад: `<circle cx="33" cy="30" r="11.5" fill="${в}" stroke="${т}" stroke-width="1.3"/><circle cx="87" cy="30" r="11.5" fill="${в}" stroke="${т}" stroke-width="1.3"/><circle cx="33" cy="30" r="11.5" fill="url(#§h)"/><circle cx="87" cy="30" r="11.5" fill="url(#§h)"/>`, перед: баз + `<circle cx="39" cy="38" r="3.4" fill="${ЗОЛ}"/><circle cx="81" cy="38" r="3.4" fill="${ЗОЛ}"/>` };
      case "хвост": return { зад: `<path d="M60 30Q96 -4 106 24Q106 44 90 46Q100 30 88 24Q78 22 66 38Z" fill="${в}" stroke="${т}" stroke-width="1.3"/><path d="M60 30Q96 -4 106 24Q106 44 90 46Q100 30 88 24Q78 22 66 38Z" fill="url(#§h)"/>`, перед: баз + `<circle cx="70" cy="28" r="3.6" fill="${ЗОЛ}" stroke="#a97500" stroke-width=".8"/>` };
      case "каре": return { зад: `<path d="M27 56Q20 96 42 94L48 70L72 70L78 94Q100 96 93 56Z" fill="${в}" stroke="${т}" stroke-width="1.3"/>`, перед: баз };
      case "ёжик": return { зад: "", перед: `<path d="M29 58L27 40L36 44L35 28L45 36L48 20L56 31L62 17L67 31L76 20L77 36L86 28L84 44L93 40L91 58Z" fill="${в}" stroke="${т}" stroke-width="1.2" stroke-linejoin="round"/>` + мас(ЧЁЛКА.replace(/Q27 26 60 21Q93 26 91 58/, "Q28 30 60 27Q92 30 91 58")) + схема };
      case "рога": return { зад: `<path d="M38 36L26 8L52 28ZM82 36L94 8L68 28Z" fill="var(--c1)" stroke="var(--cd)" stroke-width="1.3" stroke-linejoin="round"/><path d="M32 18L38 30M88 18L82 30" stroke="#fff" stroke-opacity=".5" stroke-width="1.4"/>`, перед: баз };
      case "очки-лоб": return { зад: "", перед: баз + `<circle cx="46" cy="40" r="9" fill="#1a2030" stroke="${ЗОЛ}" stroke-width="2"/><circle cx="74" cy="40" r="9" fill="#1a2030" stroke="${ЗОЛ}" stroke-width="2"/><circle cx="46" cy="40" r="5.4" fill="var(--cg)" fill-opacity=".55"/><circle cx="74" cy="40" r="5.4" fill="var(--cg)" fill-opacity=".55"/><path d="M55 40H65M37 40Q30 42 28 48M83 40Q90 42 92 48" stroke="${ЗОЛ}" stroke-width="2" fill="none"/>` };
      case "каска": return { зад: "", перед: `<path d="M30 62Q27 56 29 46L91 46Q93 56 90 62Q60 52 30 62Z" fill="${в}" opacity="0"/>` + шапкаКупол(в, `<rect x="55" y="19" width="10" height="38" rx="3" fill="${темнее(в, .8)}" opacity=".7"/><rect x="52" y="14" width="16" height="9" rx="3.4" fill="${темнее(в, .6)}"/><circle cx="60" cy="18" r="3" fill="#fff9d6"/>`) + `<path d="M24 60Q60 50 96 60Q96 67 60 65Q24 67 24 60Z" fill="${темнее(в, .8)}" stroke="${темнее(в, .55)}" stroke-width="1.2"/>` };
      case "кепка": return { зад: "", перед: шапкаКупол(в, `<path d="M60 20V56" stroke="${темнее(в, .7)}" stroke-width="1.2"/><circle cx="60" cy="21" r="3" fill="${темнее(в, .6)}"/><path d="M32 41Q60 46 88 41" stroke="${темнее(в, .7)}" stroke-width="1.1" fill="none"/>`) + `<path d="M36 62Q60 52 84 62Q82 70 60 68Q38 70 36 62Z" fill="${темнее(в, .8)}" stroke="${темнее(в, .55)}" stroke-width="1.2"/>` };
      case "шапка": return { зад: "", перед: шапкаКупол(в, `<rect x="26" y="47" width="68" height="12" rx="5" fill="${темнее(в, 1.3)}" stroke="${темнее(в, .6)}" stroke-width="1.1"/><path d="M34 47V59M42 47V59M50 47V59M58 47V59M66 47V59M74 47V59M82 47V59M90 47V59" stroke="${темнее(в, .7)}" opacity=".5"/><circle cx="60" cy="17" r="8" fill="${темнее(в, 1.4)}" stroke="${темнее(в, .6)}" stroke-width="1.1"/>`) };
      case "берет": return { зад: "", перед: баз + `<ellipse cx="68" cy="32" rx="31" ry="15" transform="rotate(-12 68 32)" fill="${в}" stroke="${т}" stroke-width="1.3"/><ellipse cx="68" cy="32" rx="31" ry="15" transform="rotate(-12 68 32)" fill="url(#§h)"/><circle cx="64" cy="19" r="3" fill="${т}"/>` };
      default: return { зад: "", перед: баз };
    }
  }

  const КОРОНА = `<path d="M44 26L46 10L54 18L60 7L66 18L74 10L76 26Z" fill="url(#§z)" stroke="#a97500" stroke-width="1.1" stroke-linejoin="round"/><circle cx="60" cy="10" r="2" fill="#ff5b5b"/><circle cx="47" cy="12" r="1.5" fill="#7ee6ff"/><circle cx="73" cy="12" r="1.5" fill="#7ee6ff"/>`;
  const ЗВЕЗДА = `<g class="плав п2"><path d="M108 8l3.2 7 7.6.8-5.7 5.2 1.7 7.5L108 24.4 101.2 28.5l1.7-7.5-5.7-5.2 7.6-.8z" fill="url(#§z)" stroke="#a97500" stroke-width=".9" stroke-linejoin="round"/></g>`;

  // ---- сборка героя ---------------------------------------------------------------------------
  function разметка(ключ, id, номер) {
    const [стиль, цвВолос, формаТип, цвФормы, наушники, акс, предмет, значок] = П[ключ] || ["ёжик", "серебро", "пиджак", "графит", 1, "", "папка", "документ"];
    const ц = ФОРМА[цвФормы] || "#232733", в = ВОЛОСЫ[цвВолос] || "#cfd3de", кожа = КОЖА[номер % КОЖА.length];
    const { зад, перед } = волосы(стиль, в, id);
    const рукав = ц === ФОРМА.халат ? "#dfe4ef" : ц;
    const руки = (р, х, у) => `<g class="рука ${р}"><circle cx="${х}" cy="${у}" r="7" fill="url(#§w)" stroke="#8d97b3" stroke-width="1.1"/><circle cx="${х + (р === "р1" ? 5 : -5)}" cy="${у - 2}" r="3" fill="url(#§w)" stroke="#8d97b3" stroke-width=".9"/><path d="M${х - 4} ${у + 2}Q${х} ${у + 4.6} ${х + 4} ${у + 2}" stroke="#8d97b3" stroke-width=".8" fill="none"/><ellipse cx="${х - 2.2}" cy="${у - 2.8}" rx="2.6" ry="1.6" fill="#fff" opacity=".85"/></g>`;
    const очки = акс === "очки" ? `<g fill="#9fd8ff" fill-opacity=".18" stroke="${ЗОЛ}" stroke-width="1.5"><rect x="38" y="70" width="17" height="11" rx="5"/><rect x="65" y="70" width="17" height="11" rx="5"/><path d="M55 75H65" fill="none"/></g>` : "";
    const визор = акс === "визор" ? `<rect x="35" y="69" width="50" height="13" rx="6" fill="var(--cg)" fill-opacity=".25" stroke="var(--cl)" stroke-width="1.4"/>` : "";
    const гарнитура = акс === "гарнитура" ? `<path d="M93 64Q98 80 84 88" fill="none" stroke="#232733" stroke-width="2"/><rect x="78" y="85" width="9" height="5.4" rx="2.6" fill="var(--cg)"/>` : "";
    const бейдж = акс === "бейдж" ? `<path d="M52 92L58 112M68 92L62 112" stroke="var(--cg)" stroke-width="1.2"/><rect x="53" y="110" width="14" height="10" rx="2" fill="#fff" stroke="#8d97b3" stroke-width="1"/><circle cx="60" cy="114" r="2.2" fill="#a6aec2"/><path d="M56 118H64" stroke="#a6aec2"/>` : "";
    const галстук = акс === "галстук" ? `<path d="M57 92H63L65 100L60 118L55 100Z" fill="#c43c4f" stroke="#7d1f2c" stroke-width="1"/>` : "";
    const шлем = стиль === "каска" || стиль === "кепка" || стиль === "шапка";
    const уши = наушники && !шлем ? `<g><ellipse cx="27" cy="62" rx="6.4" ry="11.4" fill="url(#§z)" stroke="#a97500" stroke-width="1.1"/><ellipse cx="26" cy="62" rx="3.4" ry="7.4" fill="var(--cg)" fill-opacity=".85"/><ellipse cx="93" cy="62" rx="6.4" ry="11.4" fill="url(#§z)" stroke="#a97500" stroke-width="1.1"/><ellipse cx="94" cy="62" rx="3.4" ry="7.4" fill="var(--cg)" fill-opacity=".85"/></g>`
      : наушники ? `<g><ellipse cx="26" cy="66" rx="5" ry="8" fill="#e8b33a" stroke="#a97500" stroke-width="1"/><ellipse cx="94" cy="66" rx="5" ry="8" fill="#e8b33a" stroke="#a97500" stroke-width="1"/></g>` : `<ellipse cx="27" cy="68" rx="4.4" ry="6.6" fill="${кожа}"/><ellipse cx="93" cy="68" rx="4.4" ry="6.6" fill="${кожа}"/>`;
    const корона = ВОЖДИ.has(ключ) ? КОРОНА : "";
    const звезда = !ВОЖДИ.has(ключ) && ЗВЁЗДЫ.has(ключ) ? ЗВЕЗДА : "";
    return `<defs>
      <radialGradient id="${id}a" cx=".5" cy=".5" r=".5"><stop offset="0" style="stop-color:var(--cg)" stop-opacity=".42"/><stop offset=".6" style="stop-color:var(--cg)" stop-opacity=".1"/><stop offset="1" style="stop-color:var(--cg)" stop-opacity="0"/></radialGradient>
      <radialGradient id="${id}h" cx=".38" cy=".25" r=".75"><stop offset="0" stop-color="#fff" stop-opacity=".5"/><stop offset=".55" stop-color="#fff" stop-opacity="0"/><stop offset="1" stop-color="#000" stop-opacity=".22"/></radialGradient>
      <linearGradient id="${id}s" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#fff" stop-opacity=".22"/><stop offset=".55" stop-color="#fff" stop-opacity="0"/><stop offset="1" stop-color="#000" stop-opacity=".25"/></linearGradient>
      <linearGradient id="${id}c" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="${светлее(ц, .22)}"/><stop offset=".5" stop-color="${ц}"/><stop offset="1" stop-color="${темнее(ц, .6)}"/></linearGradient>
      <linearGradient id="${id}r" x1="0" y1="0" x2="1" y2="0"><stop offset="0" style="stop-color:var(--cg)" stop-opacity="0"/><stop offset=".62" style="stop-color:var(--cg)" stop-opacity="0"/><stop offset="1" style="stop-color:var(--cg)" stop-opacity=".9"/></linearGradient>
      <radialGradient id="${id}k" cx=".4" cy=".32" r=".8"><stop offset="0" stop-color="${светлее(кожа, .35)}"/><stop offset=".6" stop-color="${кожа}"/><stop offset="1" stop-color="${темнее(кожа, .82)}"/></radialGradient>
      <linearGradient id="${id}v" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="${светлее(в, .28)}"/><stop offset=".5" stop-color="${в}"/><stop offset="1" stop-color="${темнее(в, .7)}"/></linearGradient>
      <radialGradient id="${id}w" cx=".35" cy=".3" r=".8"><stop offset="0" stop-color="#fff"/><stop offset=".7" stop-color="#d9deea"/><stop offset="1" stop-color="#a6aec2"/></radialGradient>
      <linearGradient id="${id}b" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#4a5270"/><stop offset=".5" stop-color="#1e2231"/><stop offset="1" stop-color="#0d0f17"/></linearGradient>
      <radialGradient id="${id}t" cx=".5" cy=".5" r=".5"><stop offset="0" stop-color="#000" stop-opacity=".62"/><stop offset=".7" stop-color="#000" stop-opacity=".25"/><stop offset="1" stop-color="#000" stop-opacity="0"/></radialGradient>
      <linearGradient id="${id}z" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#ffe9a0"/><stop offset=".55" stop-color="#e8b33a"/><stop offset="1" stop-color="#b57c10"/></linearGradient>
    </defs>
    <circle class="аура" cx="60" cy="86" r="66" fill="url(#${id}a)"/>
    <ellipse class="тень" cx="60" cy="143" rx="42" ry="8" fill="url(#§t)"/>
    <g class="героя">
      <rect x="46" y="124" width="9" height="12" rx="3" fill="#cfd5e3"/><rect x="65" y="124" width="9" height="12" rx="3" fill="#cfd5e3"/>
      <rect x="40" y="132" width="20" height="11" rx="5.2" fill="url(#§b)" stroke="#e8b33a" stroke-width="1.1"/><rect x="60" y="132" width="20" height="11" rx="5.2" fill="url(#§b)" stroke="#e8b33a" stroke-width="1.1"/>
      <path d="M43 136Q48 133.6 54 135M63 136Q68 133.6 74 135" stroke="#fff" stroke-width="1.6" stroke-linecap="round" fill="none" opacity=".5"/><path d="M42 141H58M62 141H78" stroke="#e8b33a" stroke-width=".9" opacity=".8"/>
      ${зад}
      ${одежда(формаТип, ц)}
      ${галстук}${бейдж}
      <path class="рукав" d="M35 97Q22 104 25 117" fill="none" stroke="${рукав}" stroke-width="13" stroke-linecap="round"/><path d="M35 97Q22 104 25 117" fill="none" stroke="${ЗОЛ}" stroke-width=".9" stroke-dasharray="1 40" stroke-linecap="round" opacity="0"/>
      <path class="рукав" d="M85 97Q99 100 102 112" fill="none" stroke="${рукав}" stroke-width="13" stroke-linecap="round"/>
      <path d="M33 95Q23 102 24 112" fill="none" stroke="${светлее(ц, .3)}" stroke-width="3.4" stroke-linecap="round" opacity=".38"/><path d="M87 95Q98 98 100 107" fill="none" stroke="${светлее(ц, .3)}" stroke-width="3.4" stroke-linecap="round" opacity=".38"/>
      <circle cx="25" cy="119" r="7" fill="none" stroke="${ЗОЛ}" stroke-width="1.2" opacity=".9"/><circle cx="102" cy="114" r="7" fill="none" stroke="${ЗОЛ}" stroke-width="1.2" opacity=".9"/>
      ${(ПРЕДМЕТЫ[предмет] || ПРЕДМЕТЫ.папка)(ключ === "юрист" || ключ === "дог_ведущий" || ключ === "прет_ведущий" ? "#1d2238" : undefined)}
      ${руки("р1", 25, 119)}${руки("р2", 102, 114)}
      <g class="голова-героя">
        ${уши}
        <ellipse cx="60" cy="80" rx="19" ry="15" fill="url(#§k)" stroke="${темнее(кожа, .78)}" stroke-width="1.1"/><ellipse cx="46.5" cy="86" rx="5" ry="2.6" fill="#ff7f9a" opacity=".3"/><ellipse cx="73.5" cy="86" rx="5" ry="2.6" fill="#ff7f9a" opacity=".3"/>
        <ellipse cx="60" cy="88" rx="9" ry="4" fill="#000" opacity=".06"/>
        <g class="лицо">
          <g class="г-обычно"><path class="глаз" d="M43 79Q49 73.5 56 80Q49.5 81.5 43 79Z"/><path class="глаз" d="M77 79Q71 73.5 64 80Q70.5 81.5 77 79Z"/></g>
          <g class="блеск"><circle cx="50.6" cy="77.1" r="1.15" fill="#fff"/><circle cx="69.4" cy="77.1" r="1.15" fill="#fff"/><ellipse cx="49.5" cy="82.2" rx="6" ry="1.3" fill="var(--cg)" opacity=".28"/><ellipse cx="70.5" cy="82.2" rx="6" ry="1.3" fill="var(--cg)" opacity=".28"/></g>
          <g class="г-скан"><rect class="скан-полоса" x="42" y="77" width="36" height="3" rx="1.5"/></g>
          <g class="г-ошибка"><path d="M43 74l8 8M51 74l-8 8M69 74l8 8M77 74l-8 8" stroke="#ff5b5b" stroke-width="2.2" stroke-linecap="round"/></g>
          <path class="рот" d="M55 88Q60 91 65 88" stroke="${темнее(кожа, .6)}" stroke-width="1.3" fill="none" stroke-linecap="round"/>
        </g>
        ${очки}${визор}
        ${перед}
        ${гарнитура}
        ${корона}
      </g>
      ${звезда}
      <g class="зз"><text x="92" y="34" font-size="13" font-weight="700">z</text><text class="з2" x="102" y="22" font-size="10" font-weight="700">z</text></g>
    </g>
    ${голограмма(значок)}`.replaceAll("§", id);
  }

  const старый = window.персонаж;
  window.персонажРобот = старый;
  const стили = new Map();
  const номера = new Map();
  window.персонаж = function (ключ) {
    if (!стили.has(ключ)) {
      const о = старый ? старый(ключ) : null;
      стили.set(ключ, о ? о.getAttribute("style") : "");
      номера.set(ключ, номера.size);
    }
    const id = `в${++счётчик}`;
    const с = document.createElementNS(NS, "svg");
    с.setAttribute("viewBox", "-12 -10 144 156");
    с.setAttribute("class", `персонаж п-${ключ}`);
    с.setAttribute("aria-hidden", "true");
    с.setAttribute("style", стили.get(ключ));
    с.innerHTML = разметка(ключ, id, номера.get(ключ));
    return с;
  };
}
