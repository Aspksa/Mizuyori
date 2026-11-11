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

// ---- Подвал: имя и версия ----------------------------------------------

запрос("/api/status")
  .then((с) => { $("подвал").textContent = `${с.имя} · версия ${с.версия}`; })
  .catch(() => { $("подвал").textContent = "Нет связи с сервером"; });

// ---- Окно настроек проекта ----------------------------------------------

const окно = $("окно-настроек");
const кнопкаОткрыть = $("открыть-настройки");
const статус = $("статус-настроек");
let таймерСтатуса;

function показатьСтатус(текст) {
  статус.textContent = текст;
  clearTimeout(таймерСтатуса);
  if (текст) таймерСтатуса = setTimeout(() => (статус.textContent = ""), 2000);
}

function применитьТему(ключ) {
  document.documentElement.dataset.theme = ключ;
  for (const кнопка of $("темы").children) {
    кнопка.setAttribute("aria-checked", String(кнопка.dataset.theme === ключ));
  }
}

function нарисоватьТемы(настройки) {
  const список = $("темы");
  список.replaceChildren();
  for (const тема of настройки.темы) {
    const кнопка = document.createElement("button");
    кнопка.type = "button";
    кнопка.className = "тема";
    кнопка.setAttribute("role", "radio");
    кнопка.dataset.theme = тема.ключ; // карточка окрашена в свою тему

    const образец = document.createElement("span");
    образец.className = "образец";
    const название = document.createElement("span");
    название.textContent = тема.название;
    const галочка = document.createElement("span");
    галочка.className = "галочка";
    галочка.textContent = "✓";
    кнопка.append(образец, название, галочка);

    кнопка.addEventListener("click", () => выбратьТему(тема.ключ));
    список.append(кнопка);
  }
  применитьТему(настройки.тема);
}

async function выбратьТему(ключ) {
  const прежняя = document.documentElement.dataset.theme;
  if (ключ === прежняя) return;
  применитьТему(ключ); // сразу, не дожидаясь сервера
  try {
    await запрос("/api/settings", { method: "PUT", body: JSON.stringify({ тема: ключ }) });
    показатьСтатус("Сохранено");
  } catch (e) {
    применитьТему(прежняя);
    показатьСтатус(`Не сохранилось: ${e.message}`);
  }
}

async function открытьНастройки() {
  окно.hidden = false;
  try {
    нарисоватьТемы(await запрос("/api/settings"));
    $("темы").querySelector('[aria-checked="true"]')?.focus();
  } catch (e) {
    показатьСтатус(`Не удалось загрузить настройки: ${e.message}`);
  }
}

function закрытьНастройки() {
  окно.hidden = true;
  показатьСтатус("");
  кнопкаОткрыть.focus();
}

кнопкаОткрыть.addEventListener("click", открытьНастройки);
$("закрыть-настройки").addEventListener("click", закрытьНастройки);
окно.addEventListener("click", (событие) => {
  if (событие.target === окно) закрытьНастройки(); // клик по затемнению
});
document.addEventListener("keydown", (событие) => {
  if (событие.key === "Escape" && !окно.hidden) закрытьНастройки();
});
