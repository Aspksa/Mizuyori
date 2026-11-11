"use strict";

const $ = (id) => document.getElementById(id);

async function запрос(адрес, параметры = {}) {
  const ответ = await fetch(адрес, {
    headers: { "Content-Type": "application/json" },
    ...параметры,
  });
  const данные = await ответ.json().catch(() => ({}));
  if (!ответ.ok) throw new Error(данные.ошибка || `Ошибка ${ответ.status}`);
  return данные;
}

// Создать элемент: создать("div", { класс: "…", текст: "…", onclick: … }, ...дети)
function создать(тег, свойства = {}, ...дети) {
  const элемент = document.createElement(тег);
  for (const [к, з] of Object.entries(свойства)) {
    if (к === "класс") элемент.className = з;
    else if (к === "текст") элемент.textContent = з;
    else if (к === "данные") Object.assign(элемент.dataset, з);
    else if (к.startsWith("on")) элемент.addEventListener(к.slice(2), з);
    else элемент.setAttribute(к, з);
  }
  элемент.append(...дети);
  return элемент;
}

// «2026-11-12 08:10:00» → «сегодня, 08:10» / «вчера, 08:10» / «12 нояб., 08:10»
function дата(строка) {
  const д = new Date(String(строка).replace(" ", "T"));
  if (isNaN(д)) return строка;
  const время = д.toLocaleTimeString("ru-RU", { hour: "2-digit", minute: "2-digit" });
  const сегодня = new Date(); сегодня.setHours(0, 0, 0, 0);
  const день = new Date(д); день.setHours(0, 0, 0, 0);
  const разница = Math.round((сегодня - день) / 86400000);
  if (разница === 0) return `сегодня, ${время}`;
  if (разница === 1) return `вчера, ${время}`;
  const опции = { day: "numeric", month: "short" };
  if (д.getFullYear() !== сегодня.getFullYear()) опции.year = "numeric";
  return `${д.toLocaleDateString("ru-RU", опции)}, ${время}`;
}

// Иконка-значок из SVG-пути
function значок(путь) {
  const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  svg.setAttribute("viewBox", "0 0 24 24");
  svg.setAttribute("aria-hidden", "true");
  svg.setAttribute("fill", "none");
  svg.setAttribute("stroke", "currentColor");
  svg.setAttribute("stroke-width", "2");
  svg.setAttribute("stroke-linecap", "round");
  svg.setAttribute("stroke-linejoin", "round");
  const p = document.createElementNS("http://www.w3.org/2000/svg", "path");
  p.setAttribute("d", путь);
  svg.append(p);
  return svg;
}

// Версия — в окне настроек
запрос("/api/status")
  .then((с) => { $("версия").textContent = `${с.имя} · версия ${с.версия}`; })
  .catch(() => {});

// ---- Окно «Настройки проекта» -------------------------------------------
//
// Изменения сразу видны на сайте (предпросмотр), но в config.json попадают
// только по кнопке «Сохранить». «Отменить» возвращает сохранённый вид.

const окно = $("окно-настроек");
const кнопкаОткрыть = $("открыть-настройки");
const статус = $("статус-настроек");

let описание = {};       // какие настройки есть (приходит с сервера)
let поУмолчанию = {};    // начальные значения
let сохранённый = {};    // что лежит в config.json
let текущий = {};        // что сейчас на экране

const одинаковые = (а, б) => Object.keys(описание).every((к) => а[к] === б[к]);
const естьИзменения = () => !одинаковые(текущий, сохранённый);

function применить(вид) {
  const html = document.documentElement;
  for (const [ключ, о] of Object.entries(описание)) {
    const значение = вид[ключ];
    html.dataset[о.атрибут] = typeof значение === "boolean" ? (значение ? "да" : "нет") : значение;
  }
}

function показатьСтатус(текст, несохранено = false) {
  статус.textContent = текст;
  статус.classList.toggle("несохранено", несохранено);
}

function обновитьКнопки() {
  const изменено = естьИзменения();
  $("сохранить").disabled = !изменено;
  $("отменить").disabled = !изменено;
  $("сбросить").disabled = одинаковые(текущий, поУмолчанию);
  показатьСтатус(изменено ? "Есть несохранённые изменения" : "", изменено);
}

function изменить(ключ, значение) {
  текущий = { ...текущий, [ключ]: значение };
  применить(текущий);
  нарисоватьПоля();
  обновитьКнопки();
}

// ---- Отрисовка полей по описанию с сервера ---------------------------------

function полеТемы(ключ, о) {
  const карточки = Object.entries(о.варианты).map(([значение, надпись]) =>
    создать("button", {
      type: "button",
      класс: "тема",
      role: "radio",
      "aria-checked": String(текущий[ключ] === значение),
      // Карточка окрашена в свою тему с учётом светлого/тёмного варианта
      данные: { theme: значение, variant: текущий.вариант },
      onclick: () => изменить(ключ, значение),
    },
      создать("span", { класс: "образец" }),
      создать("span", { класс: "подпись", текст: надпись }),
      создать("span", { класс: "галочка", текст: "✓", "aria-hidden": "true" }),
    ));
  return создать("div", { класс: "поле" },
    создать("span", { класс: "поле-название", id: `поле-${ключ}`, текст: о.название }),
    создать("div", { класс: "темы", role: "radiogroup", "aria-labelledby": `поле-${ключ}` }, ...карточки),
  );
}

function полеВыбора(ключ, о) {
  const кнопки = Object.entries(о.варианты).map(([значение, надпись]) =>
    создать("button", {
      type: "button",
      role: "radio",
      "aria-checked": String(текущий[ключ] === значение),
      текст: надпись,
      onclick: () => изменить(ключ, значение),
    }));
  return создать("div", { класс: "поле" },
    создать("span", { класс: "поле-название", id: `поле-${ключ}`, текст: о.название }),
    создать("div", { класс: "выбор", role: "radiogroup", "aria-labelledby": `поле-${ключ}` }, ...кнопки),
  );
}

function полеФлажка(ключ, о) {
  return создать("div", { класс: "поле флажок" },
    создать("span", { класс: "текст-поля" },
      создать("span", { класс: "поле-название", id: `поле-${ключ}`, текст: о.название }),
      создать("span", { класс: "пояснение", текст: о.описание || "" }),
    ),
    создать("button", {
      type: "button",
      класс: "тумблер",
      role: "switch",
      "aria-checked": String(текущий[ключ]),
      "aria-labelledby": `поле-${ключ}`,
      onclick: () => изменить(ключ, !текущий[ключ]),
    }),
  );
}

function нарисоватьПоля() {
  // Запоминаем фокус, чтобы после перерисовки он остался на той же кнопке
  const активный = document.activeElement;
  const путь = активный && $("поля").contains(активный)
    ? [...$("поля").querySelectorAll("button")].indexOf(активный) : -1;

  const поля = Object.entries(описание).map(([ключ, о]) => {
    if (ключ === "тема") return полеТемы(ключ, о);
    if (typeof о.по_умолчанию === "boolean") return полеФлажка(ключ, о);
    return полеВыбора(ключ, о);
  });
  $("поля").replaceChildren(...поля);

  if (путь >= 0) $("поля").querySelectorAll("button")[путь]?.focus();
}

// ---- Кнопки окна ----------------------------------------------------------

async function сохранить() {
  const кнопка = $("сохранить");
  кнопка.disabled = true;
  try {
    const ответ = await запрос("/api/settings", {
      method: "PUT",
      body: JSON.stringify({ внешний_вид: текущий }),
    });
    сохранённый = { ...ответ.внешний_вид };
    текущий = { ...сохранённый };
    обновитьКнопки();
    показатьСтатус("Сохранено");
  } catch (e) {
    кнопка.disabled = false;
    показатьСтатус(`Не сохранилось: ${e.message}`, true);
  }
}

function отменить() {
  текущий = { ...сохранённый };
  применить(текущий);
  нарисоватьПоля();
  обновитьКнопки();
}

function сбросить() {
  текущий = { ...поУмолчанию };
  применить(текущий);
  нарисоватьПоля();
  обновитьКнопки();
}

async function открытьНастройки() {
  окно.hidden = false;
  показатьСтатус("Загрузка…");
  try {
    const ответ = await запрос("/api/settings");
    описание = ответ.описание;
    поУмолчанию = ответ.по_умолчанию;
    сохранённый = { ...ответ.внешний_вид };
    текущий = { ...сохранённый };
    нарисоватьПоля();
    обновитьКнопки();
    $("поля").querySelector('[aria-checked="true"]')?.focus();
  } catch (e) {
    показатьСтатус(`Не удалось загрузить настройки: ${e.message}`, true);
  }
}

// Закрыть окно. Несохранённые изменения отменяются.
function закрытьНастройки() {
  if (естьИзменения()) отменить();
  окно.hidden = true;
  показатьСтатус("");
  кнопкаОткрыть.focus();
}

// Вкладки окна настроек: «Внешний вид» и «ИИ»
function вкладкаНастроек(имя) {
  const вид = имя === "вид";
  $("вкладка-вид").setAttribute("aria-selected", String(вид));
  $("вкладка-ии").setAttribute("aria-selected", String(!вид));
  $("раздел-вид").hidden = !вид;
  $("раздел-ии").hidden = вид;
  if (!вид) document.dispatchEvent(new CustomEvent("mizuyori:настройки-ии"));
}
$("вкладка-вид").addEventListener("click", () => вкладкаНастроек("вид"));
$("вкладка-ии").addEventListener("click", () => вкладкаНастроек("ии"));

кнопкаОткрыть.addEventListener("click", открытьНастройки);
$("закрыть-настройки").addEventListener("click", закрытьНастройки);
$("сохранить").addEventListener("click", сохранить);
$("отменить").addEventListener("click", отменить);
$("сбросить").addEventListener("click", сбросить);

// Клик по затемнению закрывает окно, только если нечего терять
окно.addEventListener("click", (событие) => {
  if (событие.target === окно && !естьИзменения()) закрытьНастройки();
});
document.addEventListener("keydown", (событие) => {
  if (событие.key === "Escape" && !окно.hidden) закрытьНастройки();
});

// ---- Меню: «Главная» и «Мозги» --------------------------------------------
// Экран выбирается по адресу: #главная или #мозги (работают «назад» и «вперёд»).

const ЭКРАНЫ = {
  главная: () => document.querySelector("main.главная"),
  мозги: () => $("экран-мозги"),
};

function текущийЭкран() {
  const имя = decodeURIComponent(location.hash.slice(1));
  return имя in ЭКРАНЫ ? имя : "главная";
}

function показатьЭкран() {
  const имя = текущийЭкран();
  for (const [к, найти] of Object.entries(ЭКРАНЫ)) найти().hidden = к !== имя;
  for (const ссылка of document.querySelectorAll("#меню a")) {
    if (ссылка.dataset.экран === имя) ссылка.setAttribute("aria-current", "page");
    else ссылка.removeAttribute("aria-current");
  }
  document.body.dataset.экран = имя;
  document.dispatchEvent(new CustomEvent("mizuyori:экран", { detail: имя }));
}

window.addEventListener("hashchange", показатьЭкран);
// Запуск после того, как подключатся все скрипты (мозги слушают это событие)
window.addEventListener("DOMContentLoaded", показатьЭкран);

// Открыть настройки сразу на вкладке «ИИ» (например, из чата)
document.addEventListener("mizuyori:открыть-настройки-ии", async () => {
  await открытьНастройки();
  вкладкаНастроек("ии");
});
