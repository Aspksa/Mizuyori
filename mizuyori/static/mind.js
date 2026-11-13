"use strict";

// =============================================================================
// «ВТОРОЙ МОЗГ»: душа в центре, вокруг — кластеры знаний (разделы памяти и контрагенты с Диска),
// каждая точка — запись или файл. На внешнем кольце стоят агенты и по одной «читают» точки:
// луч идёт от агента к точке, точка загорается, душа растёт (кольцо уровня вокруг ядра).
// Раскладки: «Кольца» и «Соты»; колесо — масштаб, перетаскивание — сдвиг, клик по кластеру — приблизить.
// «Изучено» — отметка просмотра записи агентом (хранится в базе), а не разбор текста ИИ.
// =============================================================================
(() => {
  const экран = $("экран-мозг2");
  if (!экран) return;
  const холст = $("мозг2-холст"), к = холст.getContext("2d"), подсказка = $("мозг2-подсказка"), инфо = $("мозг2-инфо");
  const безАнимаций = () => matchMedia("(prefers-reduced-motion: reduce)").matches;

  let данные = null, агенты = [], клас = [], узлыАгентов = [];
  let ш = 0, в = 0, dpr = 1, камера = { x: 0, y: 0, z: 1 }, цель = { x: 0, y: 0, z: 1 };
  let раскладка = "кольца", активен = false, кадр = 0, прошлый = 0, время = 0, читают = true;
  let наведён = null, перетаскивание = null, таймерДанных = 0, таймерОтправки = 0, следующееЧтение = 0, росло = 0;
  const лучи = [], вспышки = [], очередь = [], читалиСейчас = new Set();
  const ДИСК = new Set(["архивариус", "юрист", "контрагенты", "делопроизводитель", "бухгалтер", "снабженец", "секретарь", "проверяющий"]);

  const мягкий = (h) => (typeof h === "string" && /^#[0-9a-f]{6}$/i.test(h) ? h : "#6aa9ff");
  const а_ = (hex, а) => { const h = мягкий(hex).slice(1); return `rgba(${parseInt(h.slice(0, 2), 16)},${parseInt(h.slice(2, 4), 16)},${parseInt(h.slice(4, 6), 16)},${а})`; };

  // ---- раскладка -----------------------------------------------------------------------------
  function расставить() {
    if (!данные) return;
    клас = данные.кластеры.map((c) => ({ ...c, x: 0, y: 0, r: 40, точки: c.точки.map(([ключ, изучено]) => ({ ключ, изучено: Boolean(изучено), x: 0, y: 0 })) }));
    const n = клас.length;
    if (раскладка === "соты") {
      const S = 118, соты = [[0, 0]];
      for (let кольцо = 1; соты.length <= n + 1; кольцо++) {      // спираль шестиугольных ячеек вокруг центральной (души)
        let q = -кольцо, r = кольцо; const шаги = [[1, 0], [1, -1], [0, -1], [-1, 0], [-1, 1], [0, 1]];
        for (const [dq, dr] of шаги) for (let i = 0; i < кольцо; i++) { соты.push([q, r]); q += dq; r += dr; }
      }
      клас.forEach((c, i) => {
        const [q, r] = соты[i + 1];
        c.x = S * Math.sqrt(3) * (q + r / 2); c.y = S * 1.5 * r; c.r = S * .86; c.сота = S;
        c.точки.forEach((т, j) => { const ρ = Math.sqrt((j + .5) / c.точки.length) * S * .72, θ = j * 2.39996; т.x = c.x + Math.cos(θ) * ρ; т.y = c.y + Math.sin(θ) * ρ; });
      });
    } else {
      const внутр = Math.min(n, 7), R1 = n <= 5 ? 150 : 185, R2 = 330;
      клас.forEach((c, i) => {
        const внеш = i >= внутр, idx = внеш ? i - внутр : i, всего = внеш ? n - внутр : внутр, R = внеш ? R2 : R1;
        const θ = -Math.PI / 2 + (idx + (внеш ? .5 : 0)) * Math.PI * 2 / всего;
        c.x = Math.cos(θ) * R; c.y = Math.sin(θ) * R; c.θ = θ;
        const m = c.точки.length, колонок = Math.max(3, Math.ceil(Math.sqrt(m * 1.5))), шаг = 7.5;
        c.r = Math.max(34, Math.min(70, колонок * шаг * .62));
        c.точки.forEach((т, j) => {                    // сетка точек, повёрнутая вдоль кольца
          const col = j % колонок, row = Math.floor(j / колонок), lx = (col - (колонок - 1) / 2) * шаг, ly = (row - (Math.ceil(m / колонок) - 1) / 2) * шаг;
          const co = Math.cos(θ + Math.PI / 2), si = Math.sin(θ + Math.PI / 2);
          т.x = c.x + lx * co - ly * si; т.y = c.y + lx * si + ly * co;
        });
      });
    }
    // агенты: внешнее кольцо
    const РА = раскладка === "соты" ? Math.max(330, ...клас.map((c) => Math.hypot(c.x, c.y) + 160)) : (n > 7 ? 450 : n <= 5 ? 280 : 320);
    узлыАгентов = агенты.map((а, i) => {
      const θ = -Math.PI / 2 + i * Math.PI * 2 / Math.max(1, агенты.length);
      return { а, x: Math.cos(θ) * РА, y: Math.sin(θ) * РА, θ, r: 5.5 };
    });
    запас = РА + 110;                 // с запасом на подписи агентов
    сброс(true);
  }
  let запас = 400;
  function сброс(сразу = false) {
    const z = Math.max(.25, Math.min(1.6, Math.min(ш, в) / 2 / (запас + 30)));
    цель = { x: 0, y: 0, z };
    if (сразу) камера = { ...цель };
    запустить();
  }

  // ---- данные --------------------------------------------------------------------------------
  async function загрузить() {
    try {
      const [д, а] = await Promise.all([запрос("/api/mind"), запрос("/api/agents").catch(() => ({ агенты: агенты }))]);
      const было = данные?.кластеры.map((c) => c.ключ + c.точки.length).join(",");
      данные = д; агенты = (а.агенты || []).filter((х) => х.ключ);
      const стало = д.кластеры.map((c) => c.ключ + c.точки.length).join(",");
      if (было !== стало || !клас.length || узлыАгентов.length !== агенты.length) расставить();
      else { for (const c of д.кластеры) { const мой = клас.find((х) => х.ключ === c.ключ); if (мой) { мой.число = c.число; c.точки.forEach(([ключ, ч], i) => { if (ч && мой.точки[i]?.ключ === ключ) мой.точки[i].изучено = true; }); } } }
      обновитьИнфо(); запустить();
    } catch {}
  }
  function обновитьИнфо() {
    if (!данные) return;
    const р = данные.рост, всего = клас.reduce((с, c) => с + c.точки.length, 0), прочитано = клас.reduce((с, c) => с + c.точки.filter((т) => т.изучено).length, 0);
    инфо.textContent = `${данные.настроение?.имя || "душа"} · ур. ${р.уровень} · прочитано ${р.изучено}${р.до ? ` из ${р.до} до следующего уровня` : ""} · на карте ${прочитано}/${всего}`;
  }
  async function отправить() {
    clearTimeout(таймерОтправки); таймерОтправки = 0;
    while (очередь.length) {
      const пачка = очередь.splice(0, 20), агент = пачка[0].агент;
      try { const р = await запрос("/api/mind/study", { method: "POST", body: JSON.stringify({ агент, ключи: пачка.map((х) => х.ключ) }) }); if (данные) данные.рост = р; обновитьИнфо(); } catch {}
    }
  }

  // ---- чтение: агент → точка, по одной --------------------------------------------------------
  function разделыЧтения(а) {
    const своё = window.разделыАгентаПамяти?.(а) || [];
    const ключи = клас.filter((c) => своё.includes(c.ключ) || (c.вид === "диск" && ДИСК.has(а.ключ))).map((c) => c.ключ);
    return ключи.length ? ключи : клас.map((c) => c.ключ);
  }
  function прочитатьОдно() {
    const живые = узлыАгентов.filter((у) => !читалиСейчас.has(у.а.ключ));
    if (!живые.length || !клас.length) return false;
    // работающие агенты читают охотнее
    const раб = живые.filter((у) => у.а.работает), из = раб.length && Math.random() < .6 ? раб : живые;
    for (let попытка = 0; попытка < 8; попытка++) {
      const у = из[Math.floor(Math.random() * из.length)], мои = разделыЧтения(у.а);
      const кл = клас.filter((c) => мои.includes(c.ключ) && c.точки.some((т) => !т.изучено));
      if (!кл.length) continue;
      const c = кл[Math.floor(Math.random() * кл.length)], т = c.точки.find((x) => !x.изучено);
      т.изучено = true;
      читалиСейчас.add(у.а.ключ);
      const цвет = у.а.цвет_кабинета || c.цвет;
      if (безАнимаций()) { читалиСейчас.delete(у.а.ключ); готовоЧтение(у, c, т); return true; }
      лучи.push({ у, c, т, t: 0, цвет });
      return true;
    }
    return false;
  }
  function готовоЧтение(у, c, т) {
    вспышки.push({ x: т.x, y: т.y, t: 0, цвет: c.цвет });
    росло = время;
    очередь.push({ ключ: т.ключ, агент: у.а.ключ });
    if (данные) { данные.рост = { ...данные.рост, изучено: данные.рост.изучено + 1 }; const р = данные.рост; if (р.до && р.изучено >= р.до) { загрузить(); } }
    обновитьИнфо();
    if (!таймерОтправки) таймерОтправки = setTimeout(отправить, 2500);
  }

  // ---- рисование -----------------------------------------------------------------------------
  function рисоватьДушу() {
    const н = данные?.настроение || {}, цвет = мягкий(н.цвет || "#58c4ff"), р = данные?.рост || { изучено: 0, уровень: 1, от: 0, до: 8 };
    const доля = р.до ? Math.min(1, Math.max(0, (р.изучено - р.от) / Math.max(1, р.до - р.от))) : 1;
    const вспл = Math.max(0, 1 - (время - росло) * 1.6), п = .5 + .5 * Math.sin(время * (1 + (н.энергия ?? .5) * 1.2));
    const g = к.createRadialGradient(0, 0, 10, 0, 0, 120 + п * 10 + вспл * 30);
    g.addColorStop(0, а_(цвет, .3 + вспл * .3)); g.addColorStop(1, а_(цвет, 0));
    к.fillStyle = g; к.beginPath(); к.arc(0, 0, 140, 0, Math.PI * 2); к.fill();
    к.lineCap = "round"; к.lineWidth = 4; к.strokeStyle = а_(цвет, .18);
    к.beginPath(); к.arc(0, 0, 46, 0, Math.PI * 2); к.stroke();
    к.strokeStyle = а_(цвет, .95); к.beginPath(); к.arc(0, 0, 46, -Math.PI / 2, -Math.PI / 2 + доля * Math.PI * 2); к.stroke();
    к.lineCap = "butt";
    к.beginPath(); к.arc(0, 0, 36, 0, Math.PI * 2); к.fillStyle = "#070b14"; к.fill(); к.lineWidth = 2; к.strokeStyle = а_(цвет, .95); к.stroke();
    к.beginPath(); к.moveTo(0, -15); к.bezierCurveTo(11, -2, 12, 5, 0, 14); к.bezierCurveTo(-12, 5, -11, -2, 0, -15);
    к.lineWidth = 2.4; к.strokeStyle = "#e8f2ff"; к.stroke();
    к.beginPath(); к.arc(32, -32, 10, 0, Math.PI * 2); к.fillStyle = цвет; к.fill();
    к.fillStyle = "#08150f"; к.font = "700 11px system-ui, sans-serif"; к.textAlign = "center"; к.textBaseline = "middle"; к.fillText(String(р.уровень), 32, -31.5);
    к.fillStyle = "rgba(210,225,250,.9)"; к.font = "700 10px ui-monospace, Consolas, monospace";
    к.fillText(`${н.значок || ""} ${н.имя || "душа"}`.trim().toUpperCase(), 0, 68);
    к.fillStyle = "rgba(170,195,235,.7)"; к.font = "10px ui-monospace, Consolas, monospace";
    к.fillText(`прочитано ${р.изучено}`, 0, 82);
  }
  function рисоватьКластеры() {
    for (const c of клас) {
      const гор = наведён === c, всего = c.точки.length, прочит = c.точки.filter((т) => т.изучено).length;
      if (раскладка === "соты") {
        к.beginPath();
        for (let i = 0; i < 6; i++) { const θ = Math.PI / 6 + i * Math.PI / 3; к.lineTo(c.x + Math.cos(θ) * c.сота * .98, c.y + Math.sin(θ) * c.сота * .98); }
        к.closePath(); к.fillStyle = а_(c.цвет, гор ? .1 : .045); к.fill(); к.lineWidth = гор ? 1.6 : 1; к.strokeStyle = а_(c.цвет, гор ? .8 : .28); к.stroke();
      } else {
        к.beginPath(); к.arc(c.x, c.y, c.r + 6, 0, Math.PI * 2); к.fillStyle = а_(c.цвет, гор ? .1 : .04); к.fill();
        к.lineWidth = 1; к.strokeStyle = а_(c.цвет, гор ? .7 : .18); к.stroke();
      }
      const размер = камера.z > 1.6 ? 4 : 3;
      к.fillStyle = а_(c.цвет, .2);
      for (const т of c.точки) if (!т.изучено) к.fillRect(т.x - размер / 2, т.y - размер / 2, размер, размер);
      к.fillStyle = а_(c.цвет, .98);
      for (const т of c.точки) if (т.изучено) к.fillRect(т.x - размер / 2, т.y - размер / 2, размер, размер);
      к.textAlign = "center"; к.textBaseline = "middle";
      const вынос = раскладка === "соты" ? c.сота * .86 : c.r + 18, dx = раскладка === "соты" ? 0 : Math.cos(c.θ) * 0, ly = раскладка === "соты" ? c.y + вынос : c.y + Math.sin(c.θ) * вынос;
      const lx = раскладка === "соты" ? c.x : c.x + Math.cos(c.θ) * вынос + dx;
      к.font = "700 10px system-ui, sans-serif"; к.fillStyle = а_(c.цвет, гор ? 1 : .9); к.fillText(`${c.значок} ${c.имя}`.toUpperCase(), lx, ly);
      к.font = "9px ui-monospace, Consolas, monospace"; к.fillStyle = "rgba(180,200,235,.6)"; к.fillText(`${прочит}/${всего}${c.число > всего ? ` · всего ${c.число}` : ""}`, lx, ly + 12);
    }
  }
  function рисоватьАгентов() {
    const скаляр = Math.max(1, 1 / Math.max(.3, камера.z));
    for (const у of узлыАгентов) {
      const а = у.а, цвет = а.цвет_кабинета || "#6aa9ff", читает_ = читалиСейчас.has(а.ключ), раб = Boolean(а.работает), r = у.r * (скаляр > 1.6 ? 1.3 : 1);
      if (читает_ || раб) {
        const g = к.createRadialGradient(у.x, у.y, r, у.x, у.y, r + 16);
        g.addColorStop(0, а_(цвет, .55)); g.addColorStop(1, а_(цвет, 0)); к.fillStyle = g; к.beginPath(); к.arc(у.x, у.y, r + 16, 0, Math.PI * 2); к.fill();
      }
      к.beginPath(); к.arc(у.x, у.y, r, 0, Math.PI * 2); к.fillStyle = "#111a2e"; к.fill();
      к.lineWidth = 1.6; к.strokeStyle = а_(цвет, наведён === у ? 1 : .85); к.stroke();
      const доля = а.до ? Math.min(1, Math.max(0, (а.опыт - а.от) / Math.max(1, а.до - а.от))) : 1;
      к.lineWidth = 1.5; к.strokeStyle = а_(цвет, .9); к.beginPath(); к.arc(у.x, у.y, r + 2.8, -Math.PI / 2, -Math.PI / 2 + доля * Math.PI * 2); к.stroke();
      if (камера.z > .55 || наведён === у) {
        к.save(); к.translate(у.x, у.y); к.rotate(у.θ + (Math.cos(у.θ) < 0 ? Math.PI : 0));
        к.textBaseline = "middle"; к.font = "600 8px system-ui, sans-serif"; к.fillStyle = "rgba(205,220,248,.82)";
        к.textAlign = Math.cos(у.θ) < 0 ? "right" : "left"; к.fillText((а.имя || а.ключ).slice(0, 22), Math.cos(у.θ) < 0 ? -(r + 8) : r + 8, 0); к.restore();
      }
    }
  }
  function рисоватьЛучи(dt) {
    for (let i = лучи.length - 1; i >= 0; i--) {
      const л = лучи[i]; л.t += dt;
      const П = Math.min(1, л.t / .55), ослаб = л.t > .55 ? Math.max(0, 1 - (л.t - .55) / .25) : 1;
      const x = л.у.x + (л.т.x - л.у.x) * П, y = л.у.y + (л.т.y - л.у.y) * П;
      к.beginPath(); к.moveTo(л.у.x, л.у.y); к.lineTo(x, y); к.lineWidth = 1.4; к.strokeStyle = а_(л.цвет, .55 * ослаб); к.stroke();
      к.beginPath(); к.arc(x, y, 3, 0, Math.PI * 2); к.fillStyle = `rgba(255,255,255,${.95 * ослаб})`; к.fill();
      if (л.t >= .55 && !л.готово) { л.готово = true; готовоЧтение(л.у, л.c, л.т); }
      if (л.t > .8) { лучи.splice(i, 1); читалиСейчас.delete(л.у.а.ключ); }
    }
    for (let i = вспышки.length - 1; i >= 0; i--) {
      const f = вспышки[i]; f.t += dt; const П = f.t / .7;
      if (П >= 1) { вспышки.splice(i, 1); continue; }
      к.beginPath(); к.arc(f.x, f.y, 3 + П * 14, 0, Math.PI * 2); к.lineWidth = 1.5 * (1 - П); к.strokeStyle = а_(f.цвет, (1 - П) * .9); к.stroke();
    }
  }
  function кадрРисовать(t) {
    кадр = 0;
    if (!активен) return;
    const идёт = читают && клас.some((c) => c.точки.some((т) => !т.изучено));
    if (t - прошлый < 33) { кадр = requestAnimationFrame(кадрРисовать); return; }
    const dt = Math.min(.1, (t - прошлый) / 1000 || .016); прошлый = t; время += dt;
    if (читают && время > следующееЧтение) { if (прочитатьОдно()) следующееЧтение = время + (.55 + Math.random() * .5); else следующееЧтение = время + 2; }
    const k_ = Math.min(1, dt * 6);
    камера.x += (цель.x - камера.x) * k_; камера.y += (цель.y - камера.y) * k_; камера.z += (цель.z - камера.z) * k_;
    к.setTransform(dpr, 0, 0, dpr, 0, 0); к.clearRect(0, 0, ш, в);
    к.save(); к.translate(ш / 2 + камера.x * камера.z, в / 2 + камера.y * камера.z); к.scale(камера.z, камера.z);
    к.strokeStyle = "rgba(160,200,255,.07)"; к.lineWidth = 1;
    for (const R of раскладка === "кольца" ? [клас.length <= 5 ? 150 : 185, 330, запас - 110] : [запас - 110]) { к.beginPath(); к.arc(0, 0, R, 0, Math.PI * 2); к.stroke(); }
    рисоватьКластеры(); рисоватьАгентов(); рисоватьЛучи(dt); рисоватьДушу();
    к.restore();
    const движется = Math.abs(цель.x - камера.x) > .3 || Math.abs(цель.y - камера.y) > .3 || Math.abs(цель.z - камера.z) > .002;
    if (идёт || лучи.length || вспышки.length || движется || время - росло < .7) кадр = requestAnimationFrame(кадрРисовать);
  }
  function запустить() { if (активен && !кадр) { прошлый = performance.now(); кадр = requestAnimationFrame(кадрРисовать); } }

  // ---- размер, мышь ------------------------------------------------------------------------
  function размер() {
    const р = экран.getBoundingClientRect(); if (!р.width || !р.height) return;
    dpr = Math.min(window.devicePixelRatio || 1, 1.5); ш = р.width; в = р.height;
    холст.width = Math.round(ш * dpr); холст.height = Math.round(в * dpr);
    if (данные) сброс(true);
    запустить();
  }
  const вМир = (ев) => { const р = холст.getBoundingClientRect(); return { x: (ев.clientX - р.left - ш / 2) / камера.z - камера.x, y: (ев.clientY - р.top - в / 2) / камера.z - камера.y, px: ев.clientX - р.left, py: ев.clientY - р.top }; };
  function найти(м) {
    if (Math.hypot(м.x, м.y) < 50) return { тип: "душа" };
    for (const у of узлыАгентов) if (Math.hypot(у.x - м.x, у.y - м.y) < Math.max(10, 14 / камера.z)) return у;
    for (const c of клас) if (Math.hypot(c.x - м.x, c.y - м.y) < c.r + 8) return c;
    return null;
  }
  const показать = (текст, м) => {
    подсказка.replaceChildren(...текст.map(([т, жирный]) => создать(жирный ? "b" : "small", { текст: т })));
    подсказка.hidden = false;
    подсказка.style.transform = `translate(${Math.max(8, Math.min(ш - 250, м.px + 14))}px, ${Math.max(8, Math.min(в - 90, м.py + 14))}px)`;
  };
  холст.addEventListener("pointermove", (ев) => {
    if (перетаскивание) {
      камера.x = цель.x = перетаскивание.x0 + (ев.clientX - перетаскивание.cx) / камера.z; камера.y = цель.y = перетаскивание.y0 + (ев.clientY - перетаскивание.cy) / камера.z;
      перетаскивание.двигали = true; запустить(); return;
    }
    const м = вМир(ев), н = найти(м);
    if (н !== наведён) { наведён = н; холст.style.cursor = н ? "pointer" : "grab"; запустить(); }
    if (!н) { подсказка.hidden = true; return; }
    if (н.тип === "душа") { const р = данные?.рост; показать([[`${данные?.настроение?.значок || ""} ${данные?.настроение?.имя || "Душа"}`.trim(), 1], [`уровень ${р?.уровень} · прочитано ${р?.изучено}`], ["клик — характер и рост"]], м); }
    else if (н.а) показать([[н.а.имя || н.а.ключ, 1], [`${н.а.кабинет_название || ""}${н.а.уровень ? ` · уровень ${н.а.уровень}` : ""}`], [читалиСейчас.has(н.а.ключ) ? "читает…" : н.а.работает ? "работает" : "ждёт"]], м);
    else показать([[`${н.значок} ${н.имя}`, 1], [`прочитано ${н.точки.filter((т) => т.изучено).length} из ${н.точки.length}${н.число > н.точки.length ? ` (всего ${н.число})` : ""}`], ["клик — приблизить"]], м);
  });
  холст.addEventListener("pointerleave", () => { наведён = null; подсказка.hidden = true; запустить(); });
  холст.addEventListener("pointerdown", (ев) => { холст.setPointerCapture(ев.pointerId); перетаскивание = { cx: ев.clientX, cy: ев.clientY, x0: цель.x, y0: цель.y, двигали: false }; холст.style.cursor = "grabbing"; });
  холст.addEventListener("pointerup", (ев) => {
    const был = перетаскивание; перетаскивание = null; холст.style.cursor = "grab";
    if (!был || был.двигали) return;
    const н = найти(вМир(ев));
    if (н?.тип === "душа") document.dispatchEvent(new CustomEvent("mizuyori:центр", { detail: { вкладка: "душа" } }));
    else if (н?.а) window.открытьАгента?.(н.а.ключ);
    else if (н) { цель = { x: -н.x, y: -н.y, z: Math.min(4, Math.max(2.2, (Math.min(ш, в) * .42) / (н.r + 10))) }; запустить(); }
    else сброс();
  });
  холст.addEventListener("wheel", (ев) => {
    ев.preventDefault();
    const м = вМир(ев), f = Math.exp(-ев.deltaY * .0015), z = Math.max(.2, Math.min(6, цель.z * f));
    цель.x = -(м.x - (м.px - ш / 2) / z); цель.y = -(м.y - (м.py - в / 2) / z); цель.z = z; запустить();
  }, { passive: false });

  // ---- управление ---------------------------------------------------------------------------
  for (const б of экран.querySelectorAll("[data-раскладка]")) б.addEventListener("click", () => {
    раскладка = б.dataset.раскладка; for (const x of экран.querySelectorAll("[data-раскладка]")) x.setAttribute("aria-pressed", String(x === б));
    расставить();
  });
  $("мозг2-сброс").addEventListener("click", () => сброс());
  const кнопкаЧтения = $("мозг2-читают");
  кнопкаЧтения.addEventListener("click", () => { читают = !читают; кнопкаЧтения.setAttribute("aria-pressed", String(читают)); кнопкаЧтения.textContent = читают ? "⏸ Агенты читают" : "▶ Читать"; запустить(); });

  function включить(вкл) {
    активен = вкл;
    clearInterval(таймерДанных); таймерДанных = 0;
    if (вкл) { размер(); загрузить(); таймерДанных = setInterval(() => { if (!document.hidden) загрузить(); }, 20000); запустить(); }
    else { if (очередь.length) отправить(); }
  }
  document.addEventListener("mizuyori:мозг2", (с) => включить(Boolean(с.detail)));
  new ResizeObserver(() => { if (активен) размер(); }).observe(экран);
  document.addEventListener("visibilitychange", () => { if (!document.hidden) запустить(); else if (очередь.length) отправить(); });
  addEventListener("pagehide", () => { if (очередь.length) отправить(); });
})();
