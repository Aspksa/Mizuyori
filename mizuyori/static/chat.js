"use strict";

// ---- Чат ------------------------------------------------------------------
// ИИ — cloud.ru (настройки проекта → вкладка «ИИ»). Ответ приходит потоком
// и печатается по мере генерации. Без ИИ вместо ответа — подсказка, как подключить.
{
  const список = $("чат-сообщения");
  const форма = $("чат-форма");
  const поле = $("чат-поле");
  const кнопка = форма.querySelector("button[type=submit]");
  let отправляется = false;

  function пузырь(сообщение) {
    const чьё = сообщение.роль === "пользователь" ? "моё" : "ии";
    const элемент = создать("div", { класс: `сообщение ${чьё}` },
      создать("div", { класс: "текст-сообщения", текст: сообщение.текст }),
      создать("time", { класс: "когда", текст: сообщение.создано ? дата(сообщение.создано) : "" }),
    );
    if (сообщение.мысль) показатьМысль(элемент, сообщение.мысль, false);
    return элемент;
  }

  // 💭 — внутренняя мысль ИИ перед ответом: свёрнута, открывается по клику
  function показатьМысль(элемент, мысль, думает) {
    let кнопка = элемент.querySelector(".мысль-кнопка");
    let блок = элемент.querySelector(".мысль-сообщения");
    if (!кнопка) {
      блок = создать("div", { класс: "мысль-сообщения", hidden: "" });
      кнопка = создать("button", { type: "button", класс: "мысль-кнопка", "aria-expanded": "false",
        onclick: () => {
          const открыта = блок.hidden;
          блок.hidden = !открыта;
          кнопка.setAttribute("aria-expanded", String(открыта));
        } });
      элемент.prepend(кнопка, блок);
    }
    кнопка.classList.toggle("думает", думает);
    кнопка.textContent = думает ? "💭 думает…" : "💭 мысль";
    блок.textContent = мысль;
  }

  // Поток ответа: <think>…</think> моделей-«мыслителей» не показываем, <мысль>…</мысль> — в 💭
  function разобрать(текст) {
    текст = текст.replace(/<think>[\s\S]*?(<\/think>\s*|$)/g, "");
    const м = текст.match(/^\s*<мысль>([\s\S]*?)(<\/мысль>|$)/i);
    if (!м) {
      const начало = текст.trimStart();
      if (начало && "<мысль>".startsWith(начало)) return { мысль: "", ответ: "", думает: true };
      return { мысль: "", ответ: текст, думает: false };
    }
    if (!м[2]) return { мысль: м[1].trim(), ответ: "", думает: true };
    return { мысль: м[1].trim(), ответ: текст.slice(м[0].length).trimStart(), думает: false };
  }

  function пустойЧат() {
    return создать("div", { класс: "чат-пусто" },
      создать("div", { класс: "чат-пусто-заголовок", текст: "Здесь пока пусто" }),
      создать("div", { текст: "Напишите первое сообщение" }),
    );
  }

  // Метка рядом с заголовком: какая модель отвечает. Клик — настройки ИИ.
  function показатьМетку(подключён, модель) {
    const метка = $("чат-ии");
    метка.textContent = подключён ? `ИИ · ${модель.split("/").pop()}` : "ИИ не подключён";
    метка.title = подключён ? `${модель} — настроить` : "Подключить ИИ cloud.ru";
    метка.classList.toggle("включено", подключён);
  }
  $("чат-ии").addEventListener("click", () => document.dispatchEvent(new CustomEvent("mizuyori:открыть-настройки-ии")));
  document.addEventListener("mizuyori:ии-изменён", (с) => показатьМетку(с.detail.подключён, с.detail.модель));

  // Внизу ли сейчас список (чтобы не дёргать, если человек листает историю)
  const уНиза = () => список.scrollHeight - список.scrollTop - список.clientHeight < 80;

  function вниз() {
    список.scrollTop = список.scrollHeight;
  }

  function добавить(элемент) {
    список.querySelector(".чат-пусто")?.remove();
    список.append(элемент);
    вниз();
  }

  async function загрузить() {
    try {
      const ответ = await запрос("/api/chat");
      показатьМетку(ответ.ии_подключён, ответ.модель);
      список.replaceChildren(...(ответ.сообщения.length ? ответ.сообщения.map(пузырь) : [пустойЧат()]));
      вниз();
    } catch (e) {
      список.replaceChildren(создать("div", { класс: "чат-пусто", текст: `Не удалось загрузить чат: ${e.message}` }));
    }
  }

  // Поле растёт вместе с текстом (до 8 строк)
  function подогнатьВысоту() {
    поле.style.height = "auto";
    поле.style.height = `${Math.min(поле.scrollHeight, 200)}px`;
  }

  async function отправить() {
    const текст = поле.value.trim();
    if (!текст || отправляется) return;
    отправляется = true;
    кнопка.disabled = true;
    document.dispatchEvent(new CustomEvent("mizuyori:чат-отправлено"));

    // Сообщение показываем сразу, не дожидаясь сервера
    const моё = пузырь({ роль: "пользователь", текст });
    добавить(моё);
    поле.value = "";
    подогнатьВысоту();
    const печатает = создать("div", { класс: "сообщение ии печатает", "aria-label": "ИИ печатает" },
      создать("span"), создать("span"), создать("span"));
    добавить(печатает);

    let пузырьИИ = null;
    let текстИИ = "";
    try {
      const ответ = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ текст }),
      });
      if (!ответ.ok) {
        const данные = await ответ.json().catch(() => ({}));
        throw new Error(данные.ошибка || `Ошибка ${ответ.status}`);
      }
      // Читаем поток: по одной JSON-строке на событие
      const читатель = ответ.body.getReader();
      const декодер = new TextDecoder();
      let хвост = "";
      for (;;) {
        const { value, done } = await читатель.read();
        if (done) break;
        хвост += декодер.decode(value, { stream: true });
        const строки = хвост.split("\n");
        хвост = строки.pop();
        for (const строка of строки) {
          if (!строка.trim()) continue;
          const событие = JSON.parse(строка);
          if (событие.вопрос) {
            моё.replaceWith(пузырь(событие.вопрос));
          } else if (событие.кусок) {
            const внизу = уНиза();
            if (!пузырьИИ) {
              пузырьИИ = пузырь({ роль: "ии", текст: "" });
              пузырьИИ.classList.add("пишет");
              печатает.replaceWith(пузырьИИ);
            }
            текстИИ += событие.кусок;
            const р = разобрать(текстИИ);
            if (р.думает || р.мысль) показатьМысль(пузырьИИ, р.мысль, р.думает);
            пузырьИИ.querySelector(".текст-сообщения").textContent = р.ответ || "…";
            if (внизу) вниз();
          } else if (событие.ответ) {
            const готовый = пузырь(событие.ответ);
            if (пузырьИИ?.querySelector(".мысль-кнопка[aria-expanded=true]")) готовый.querySelector(".мысль-кнопка")?.click();
            (пузырьИИ || печатает).replaceWith(готовый);
            пузырьИИ = null;
          } else if (событие.ошибка) {
            const ошибка = создать("div", { класс: "сообщение ошибка" },
              создать("div", { текст: `ИИ не ответил: ${событие.ошибка}` }),
              создать("button", { type: "button", класс: "ссылка", текст: "Настройки ИИ",
                onclick: () => document.dispatchEvent(new CustomEvent("mizuyori:открыть-настройки-ии")) }));
            (пузырьИИ || печатает).replaceWith(ошибка);
            пузырьИИ = null;
          }
        }
      }
      if (печатает.isConnected) печатает.remove();
    } catch (e) {
      const ошибка = создать("div", { класс: "сообщение ошибка", текст: `Не отправлено: ${e.message}` });
      if (печатает.isConnected) печатает.replaceWith(ошибка); else добавить(ошибка);
      if (!текстИИ) { поле.value = текст; подогнатьВысоту(); }
    } finally {
      отправляется = false;
      кнопка.disabled = false;
      вниз();
      поле.focus();
    }
  }

  форма.addEventListener("submit", (событие) => { событие.preventDefault(); отправить(); });
  поле.addEventListener("input", подогнатьВысоту);
  // Enter — отправить, Shift+Enter — новая строка
  поле.addEventListener("keydown", (событие) => {
    if (событие.key === "Enter" && !событие.shiftKey && !событие.isComposing) {
      событие.preventDefault();
      отправить();
    }
  });

  $("чат-очистить").addEventListener("click", async () => {
    if (!confirm("Удалить все сообщения чата?")) return;
    try {
      await запрос("/api/chat", { method: "DELETE" });
      список.replaceChildren(пустойЧат());
    } catch (e) {
      alert(`Не удалось очистить чат: ${e.message}`);
    }
  });

  загрузить();
}
