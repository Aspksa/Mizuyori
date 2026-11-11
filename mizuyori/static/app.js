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

function показатьОшибку(текст) {
  const блок = $("ошибка");
  блок.textContent = текст || "";
  блок.hidden = !текст;
}

function дата(строка) {
  const д = new Date(строка.replace(" ", "T"));
  return isNaN(д) ? строка : д.toLocaleString("ru-RU", { dateStyle: "medium", timeStyle: "short" });
}

function нарисоватьЗаписи(записи) {
  const список = $("список");
  список.replaceChildren();
  for (const запись of записи) {
    const li = document.createElement("li");

    const текст = document.createElement("div");
    текст.className = "текст";
    текст.textContent = запись.текст;
    const время = document.createElement("time");
    время.textContent = дата(запись.создано);
    текст.append(время);

    const кнопка = document.createElement("button");
    кнопка.className = "удалить";
    кнопка.title = "Удалить";
    кнопка.textContent = "✕";
    кнопка.onclick = async () => {
      кнопка.disabled = true;
      try {
        await запрос(`/api/notes/${запись.id}`, { method: "DELETE" });
        await загрузитьЗаписи();
      } catch (e) {
        показатьОшибку(e.message);
        кнопка.disabled = false;
      }
    };

    li.append(текст, кнопка);
    список.append(li);
  }
  $("пусто").hidden = записи.length > 0;
}

async function загрузитьЗаписи() {
  нарисоватьЗаписи(await запрос("/api/notes"));
}

async function загрузитьСостояние() {
  const с = await запрос("/api/status");
  document.title = с.имя;
  $("имя").textContent = с.имя;
  $("подпись").textContent = `Версия ${с.версия}`;
  const строки = [
    ["Python", с.python],
    ["Система", с.система],
    ["Порт", с.порт],
    ["База", с.база],
  ];
  $("состояние").replaceChildren(...строки.flatMap(([название, значение]) => {
    const dt = document.createElement("dt");
    dt.textContent = название;
    const dd = document.createElement("dd");
    dd.textContent = значение;
    return [dt, dd];
  }));
}

$("форма").addEventListener("submit", async (событие) => {
  событие.preventDefault();
  const поле = $("поле");
  const текст = поле.value.trim();
  if (!текст) return;
  const кнопка = событие.submitter;
  кнопка.disabled = true;
  try {
    await запрос("/api/notes", { method: "POST", body: JSON.stringify({ текст }) });
    поле.value = "";
    показатьОшибку("");
    await загрузитьЗаписи();
  } catch (e) {
    показатьОшибку(e.message);
  } finally {
    кнопка.disabled = false;
    поле.focus();
  }
});

Promise.all([загрузитьСостояние(), загрузитьЗаписи()]).catch((e) =>
  показатьОшибку(`Не удалось связаться с сервером: ${e.message}`)
);
