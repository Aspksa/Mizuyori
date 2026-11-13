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

  const ЗАГЛУШКА_НАЧАЛО = "ИИ пока не подключён";

  function пузырь(сообщение, новое = false) {
    const чьё = сообщение.роль === "пользователь" ? "моё" : "ии";
    const текст = создать("div", { класс: `текст-сообщения${чьё === "ии" ? " разметка" : ""}` });
    // ответы ИИ — с разметкой (**жирный**, списки, код), без звёздочек на экране
    if (чьё === "ии") текст.innerHTML = разметка(сообщение.текст); else текст.textContent = сообщение.текст;
    const элемент = создать("div", { класс: `сообщение ${чьё}${новое ? " новое" : ""}` },
      текст,
      создать("time", { класс: "когда", текст: сообщение.создано ? дата(сообщение.создано) : "" }),
    );
    if (сообщение.мысль) показатьМысль(элемент, сообщение.мысль, false);
    if (чьё === "ии" && сообщение.id && !String(сообщение.текст).startsWith(ЗАГЛУШКА_НАЧАЛО)) {
      элемент.append(действия(элемент, сообщение));
    }
    return элемент;
  }

  // ---- Из ответа — в дела: ➕ в задачи, 🎯 в цель, ✎ в заметку, ⧉ копировать ----------

  function тост(текст) {
    const т = создать("div", { класс: "тост", текст, role: "status" });
    document.body.append(т);
    requestAnimationFrame(() => т.classList.add("виден"));
    setTimeout(() => { т.classList.remove("виден"); setTimeout(() => т.remove(), 300); }, 2600);
  }
  const деньISO = (д) => `${д.getFullYear()}-${String(д.getMonth() + 1).padStart(2, "0")}-${String(д.getDate()).padStart(2, "0")}`;
  const черезДней = (н) => { const д = new Date(); д.setDate(д.getDate() + н); return деньISO(д); };

  // Что можно превратить в задачи: пункты списков из ответа, иначе выделение, иначе первая фраза
  function кандидаты(элемент, текст) {
    const выделение = String(window.getSelection?.() || "").trim();
    if (выделение && элемент.contains(window.getSelection().anchorNode)) {
      return выделение.split(/\n+/).map((с) => простойТекст(с).replace(/^[-*•\d.)\s]+/, "").trim()).filter(Boolean).slice(0, 12);
    }
    const пункты = [];
    for (const строка of String(текст).split("\n")) {
      const м = строка.match(/^\s*(?:[-*•+]|\d+[.)])\s+(?:\[[ xX]\]\s+)?(.+)$/);
      if (м) пункты.push(простойТекст(м[1]).replace(/[:：]$/, "").slice(0, 200));
    }
    if (пункты.length) return пункты.slice(0, 12);
    const первая = простойТекст(текст).split(/(?<=[.!?])\s|\n/)[0] || "";
    return первая ? [первая.slice(0, 200)] : [];
  }

  let списки = null;
  async function загрузитьСписки() {
    if (!списки) { try { const д = await запрос("/api/lists"); списки = Array.isArray(д) ? д : д.списки || []; } catch { списки = []; } }
    return списки;
  }

  function закрытьПанели(кроме) {
    for (const п of список.querySelectorAll(".панель-действия")) if (п !== кроме) п.remove();
  }

  function действия(элемент, сообщение) {
    const кнопка = (значок, подпись, действие) => создать("button", { type: "button", класс: "кнопка-действия",
      title: подпись, onclick: (с) => { с.stopPropagation(); действие(); } }, создать("span", { текст: значок }), создать("span", { текст: подпись }));
    return создать("div", { класс: "действия-сообщения" },
      кнопка("➕", "В задачи", () => панельЗадач(элемент, сообщение)),
      кнопка("🎯", "В цель", () => панельЦели(элемент, сообщение)),
      кнопка("✎", "В заметку", () => вЗаметку(сообщение)),
      кнопка("⧉", "Копировать", async () => {
        try { await navigator.clipboard.writeText(простойТекст(сообщение.текст)); тост("Скопировано"); }
        catch { тост("Не удалось скопировать"); }
      }));
  }

  async function панельЗадач(элемент, сообщение) {
    const пункты = кандидаты(элемент, сообщение.текст);
    закрытьПанели();
    const строки = пункты.map((т) => {
      const флажок = создать("input", { type: "checkbox", "aria-label": "Добавить" });
      флажок.checked = true;
      const поле = создать("input", { type: "text", maxlength: "2000", value: т, "aria-label": "Текст задачи" });
      return { флажок, поле, строка: создать("label", { класс: "кандидат" }, флажок, поле) };
    });
    const срок = создать("select", { "aria-label": "Срок" },
      создать("option", { value: "", текст: "Без срока" }), создать("option", { value: черезДней(0), текст: "Сегодня" }),
      создать("option", { value: черезДней(1), текст: "Завтра" }), создать("option", { value: черезДней(7), текст: "Через неделю" }));
    const выборСписка = создать("select", { "aria-label": "Список" }, создать("option", { value: "", текст: "Без списка" }),
      ...(await загрузитьСписки()).map((с) => создать("option", { value: String(с.id), текст: `${с.значок} ${с.название}` })));
    const добавить = создать("button", { type: "submit", класс: "кнопка главная малая", текст: "Добавить" });
    const обновитьКнопку = () => {
      const н = строки.filter((с) => с.флажок.checked && с.поле.value.trim()).length;
      добавить.textContent = н ? `Добавить ${н}` : "Добавить";
      добавить.disabled = !н;
    };
    строки.forEach((с) => { с.флажок.addEventListener("change", обновитьКнопку); с.поле.addEventListener("input", обновитьКнопку); });
    const панель = создать("form", { класс: "панель-действия" },
      создать("div", { класс: "панель-действия-заголовок", текст: строки.length > 1 ? "➕ Задачи из ответа" : "➕ Задача из ответа" }),
      ...(строки.length ? строки.map((с) => с.строка) : [создать("p", { класс: "пусто", текст: "Выделите текст в ответе и нажмите ещё раз." })]),
      создать("div", { класс: "панель-действия-низ" }, срок, выборСписка,
        создать("button", { type: "button", класс: "кнопка второстепенная малая", текст: "Отмена", onclick: () => панель.remove() }),
        добавить));
    панель.addEventListener("submit", async (с) => {
      с.preventDefault();
      const тексты = строки.filter((х) => х.флажок.checked && х.поле.value.trim()).map((х) => х.поле.value.trim());
      if (!тексты.length) return;
      добавить.disabled = true;
      try {
        for (const т of тексты) {
          await запрос("/api/tasks", { method: "POST", body: JSON.stringify({ текст: т, срок: срок.value || null,
            список_id: выборСписка.value ? Number(выборСписка.value) : null }) });
        }
        панель.remove();
        тост(тексты.length === 1 ? "Задача добавлена" : `Добавлено задач: ${тексты.length}`);
        document.dispatchEvent(new CustomEvent("mizuyori:обновить-задачи"));
      } catch (e) { тост(`Не получилось: ${e.message}`); добавить.disabled = false; }
    });
    обновитьКнопку();
    элемент.append(панель);
    панель.querySelector("input[type=text]")?.focus();
  }

  function панельЦели(элемент, сообщение) {
    закрытьПанели();
    const выделение = String(window.getSelection?.() || "").trim();
    const заголовок = (String(сообщение.текст).match(/^#{1,4}\s+(.+)$/m) || [])[1];
    const имя = простойТекст(выделение && элемент.contains(window.getSelection().anchorNode) ? выделение
      : заголовок || простойТекст(сообщение.текст).split(/(?<=[.!?])\s|\n/)[0] || "").slice(0, 80);
    const шаги = кандидаты(элемент, сообщение.текст).filter((т) => т !== имя);
    const поле = создать("input", { type: "text", maxlength: "80", value: имя, placeholder: "Чего хотите достичь?", "aria-label": "Цель" });
    const почему = создать("input", { type: "text", maxlength: "300", placeholder: "Зачем это вам? (необязательно)", "aria-label": "Зачем" });
    const сШагами = создать("input", { type: "checkbox" });
    сШагами.checked = шаги.length > 1;
    const панель = создать("form", { класс: "панель-действия" },
      создать("div", { класс: "панель-действия-заголовок", текст: "🎯 Новая цель из ответа" }),
      поле, почему,
      ...(шаги.length > 1 ? [создать("label", { класс: "флажок-строка" }, сШагами, ` и шаги из ответа — ${шаги.length} задач`)] : []),
      создать("div", { класс: "панель-действия-низ" },
        создать("button", { type: "button", класс: "кнопка второстепенная малая", текст: "Отмена", onclick: () => панель.remove() }),
        создать("button", { type: "submit", класс: "кнопка главная малая", текст: "Создать цель" })));
    панель.addEventListener("submit", async (с) => {
      с.preventDefault();
      if (!поле.value.trim()) return поле.focus();
      try {
        const цель = await запрос("/api/goals", { method: "POST", body: JSON.stringify({ имя: поле.value.trim(), почему: почему.value.trim() }) });
        if (сШагами.checked) {
          for (const т of шаги) await запрос("/api/tasks", { method: "POST", body: JSON.stringify({ текст: т, цель_id: цель.id }) });
        }
        панель.remove();
        тост(сШагами.checked && шаги.length > 1 ? `Цель «${цель.имя}» и ${шаги.length} шагов` : `Цель «${цель.имя}» создана`);
        document.dispatchEvent(new CustomEvent("mizuyori:обновить-задачи"));
      } catch (e) { тост(`Не получилось: ${e.message}`); }
    });
    элемент.append(панель);
    поле.focus();
  }

  async function вЗаметку(сообщение) {
    try {
      await запрос("/api/notes", { method: "POST", body: JSON.stringify({ текст: простойТекст(сообщение.текст) }) });
      тост("Сохранено в заметки");
      document.dispatchEvent(new CustomEvent("mizuyori:обновить-задачи"));
    } catch (e) { тост(`Не получилось: ${e.message}`); }
  }

  // Копировать блок кода
  список.addEventListener("click", async (с) => {
    const к = с.target.closest(".копировать-код");
    if (!к) return;
    try { await navigator.clipboard.writeText(к.closest(".код-блок").querySelector("code").textContent); к.textContent = "Скопировано ✓"; }
    catch { к.textContent = "Не вышло"; }
    setTimeout(() => (к.textContent = "Копировать"), 1500);
  });

  // ---- Печать по словам: текст догоняет поток плавно, без рывков -----------------

  function печатник(элемент) {
    const поле = элемент.querySelector(".текст-сообщения");
    let цель = "", показано = 0, кадр = 0, прошлый = 0, готово = null;
    function шаг(t) {
      const dt = Math.min(0.1, Math.max(0, (t - прошлый) / 1000 || 0.016));
      прошлый = t;
      const отстаёт = цель.length - показано;
      if (отстаёт > 0) {
        // чем больше отстали — тем быстрее, но всегда целыми словами
        let н = Math.min(цель.length, показано + Math.max(1, Math.ceil((35 + отстаёт * 3.5) * dt)));
        const пробел = цель.slice(н).search(/\s/);
        н = пробел < 0 ? (готово ? цель.length : н) : Math.min(цель.length, н + пробел);
        if (н > показано) {
          показано = н;
          const внизу = уНиза();
          поле.innerHTML = разметка(цель.slice(0, показано)) || "…";
          if (внизу) вниз();
        }
      }
      if (показано >= цель.length && готово) { кадр = 0; const г = готово; готово = null; г(); return; }
      кадр = requestAnimationFrame(шаг);
    }
    return {
      задать(текст) { цель = текст; if (!кадр) { прошлый = performance.now(); кадр = requestAnimationFrame(шаг); } },
      дописать() {
        return new Promise((г) => {
          if (matchMedia("(prefers-reduced-motion: reduce)").matches) показано = цель.length;
          готово = г;
          if (!кадр) { прошлый = performance.now(); кадр = requestAnimationFrame(шаг); }
        });
      },
    };
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

  // Итоги поручений приходят в чат сами: раз в несколько секунд сверяем номер последнего сообщения
  let известныйНомер = null;
  async function сверитьНомер(обновить) {
    try {
      const { id } = await запрос("/api/chat/last");
      if (известныйНомер === null || !обновить) { известныйНомер = id; return; }
      if (id !== известныйНомер && !отправляется) {
        const низ = уНиза();
        известныйНомер = id;
        await загрузить();
        if (!низ) список.scrollTop = Math.max(0, список.scrollHeight - список.clientHeight - 80);
      }
    } catch { /* сервер занят: попробуем в следующий раз */ }
  }
  setInterval(() => { if (!document.hidden && !отправляется) сверитьНомер(true); }, 6000);

  async function загрузить() {
    try {
      const ответ = await запрос("/api/chat");
      известныйНомер = ответ.сообщения.length ? ответ.сообщения[ответ.сообщения.length - 1].id : 0;
      показатьМетку(ответ.ии_подключён, ответ.модель);
      список.replaceChildren(...(ответ.сообщения.length ? ответ.сообщения.map((с) => пузырь(с)) : [пустойЧат()]));
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
    const моё = пузырь({ роль: "пользователь", текст }, true);
    добавить(моё);
    поле.value = "";
    подогнатьВысоту();
    const печатает = создать("div", { класс: "сообщение ии печатает", "aria-label": "ИИ печатает" },
      создать("span"), создать("span"), создать("span"));
    добавить(печатает);

    let пузырьИИ = null, печать = null;
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
            const настоящий = пузырь(событие.вопрос);
            настоящий.classList.add("без-анимации");
            моё.replaceWith(настоящий);
          } else if (событие.кусок) {
            const внизу = уНиза();
            if (!пузырьИИ) {
              пузырьИИ = пузырь({ роль: "ии", текст: "" });
              пузырьИИ.classList.add("пишет");
              печатает.replaceWith(пузырьИИ);
              печать = печатник(пузырьИИ);
            }
            текстИИ += событие.кусок;
            const р = разобрать(текстИИ);
            if (р.думает || р.мысль) показатьМысль(пузырьИИ, р.мысль, р.думает);
            if (р.ответ) печать.задать(р.ответ);
            else пузырьИИ.querySelector(".текст-сообщения").textContent = "…";
            if (внизу) вниз();
          } else if (событие.ответ) {
            if (печать) { печать.задать(событие.ответ.текст); await печать.дописать(); }
            const готовый = пузырь(событие.ответ);
            готовый.classList.add("без-анимации");
            if (пузырьИИ?.querySelector(".мысль-кнопка[aria-expanded=true]")) готовый.querySelector(".мысль-кнопка")?.click();
            (пузырьИИ?.isConnected ? пузырьИИ : печатает).replaceWith(готовый);
            if (уНиза()) вниз();
            пузырьИИ = null; печать = null;
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
      console.error("чат: отправка не удалась", e);
      const ошибка = создать("div", { класс: "сообщение ошибка", текст: `Не отправлено: ${e.message}` });
      if (печатает.isConnected) печатает.replaceWith(ошибка); else добавить(ошибка);
      if (!текстИИ) { поле.value = текст; подогнатьВысоту(); }
    } finally {
      отправляется = false;
      сверитьНомер(false);
      кнопка.disabled = false;
      вниз();
      поле.focus();
    }
  }

  форма.addEventListener("submit", (событие) => { событие.preventDefault(); отправить(); });

  // Скрепка: файл (смета на ремонт) уходит на сервер, агент отвечает разбором прямо в чат
  const скрепка = $("чат-скрепка"), файлВвод = $("чат-файл");
  async function отправитьФайл(файл) {
    if (!файл || отправляется) return;
    отправляется = true;
    кнопка.disabled = скрепка.disabled = true;
    document.dispatchEvent(new CustomEvent("mizuyori:чат-отправлено"));
    добавить(пузырь({ роль: "пользователь", текст: `📎 ${файл.name}` }, true));
    const печатает = создать("div", { класс: "сообщение ии печатает", "aria-label": "Агент разбирает смету" },
      создать("span"), создать("span"), создать("span"));
    добавить(печатает);
    try {
      const ответ = await fetch(`/api/chat/attach?name=${encodeURIComponent(файл.name)}`, {
        method: "POST", headers: { "Content-Type": "application/octet-stream" }, body: файл });
      const данные = await ответ.json().catch(() => ({}));
      if (!ответ.ok) throw new Error(данные.ошибка || `Ошибка ${ответ.status}`);
      печатает.remove();
      добавить(пузырь(данные.ответ, true));
    } catch (e) {
      печатает.remove();
      добавить(пузырь({ роль: "ии", текст: `📎 Не получилось отправить файл: ${e.message}` }, true));
    } finally {
      отправляется = false;
      сверитьНомер(false);
      кнопка.disabled = скрепка.disabled = false;
      файлВвод.value = "";
    }
  }
  скрепка.addEventListener("click", () => файлВвод.click());
  файлВвод.addEventListener("change", () => отправитьФайл(файлВвод.files[0]));
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
