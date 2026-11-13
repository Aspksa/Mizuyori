"use strict";

// =============================================================================
// АГЕНТЫ КАК МОЗГ: граф в стиле раздела «Мозги».
//
// В центре — ядро Mizuyori. Агенты стоят на широком эллипсе, кабинеты занимают свои дуги, отделы идут
// подряд, руководитель отдела — первым. Агенты НЕ двигаются: у каждого своё постоянное место.
// Внизу слева — узел «Чат»: сообщение уходит импульсом в ядро и к «Собеседнику», ответ возвращается обратно.
// Работа агента видна как поток по нитям (ядро → начальник кабинета → агент), искры по орбите,
// радар в ядре, «матрица» на фоне; передачи работы, знаний и опыта оставляют светящийся след.
// Данные приходят событием mizuyori:агенты из agents.js (тот же опрос /api/agents).
// =============================================================================
{
  const лента = document.querySelector(".конвейер-лента");
  const холст = $("агенты-граф");
  if (лента && холст) {
    const к = холст.getContext("2d");
    const подсказка = $("агенты-граф-подсказка");
    const кнопкаВида = $("агенты-вид");
    const безАнимаций = () => matchMedia("(prefers-reduced-motion: reduce)").matches;
    const ИКОНКИ = () => window.ЗНАЧКИ_АГЕНТОВ || {};
    const ЦВЕТ_ЗНАНИЯ = "#6aa9ff", ЦВЕТ_ОПЫТА = "#f5c451", ЦВЕТ_ЧАТА = "#58c4ff";
    const ШРИФТ = '"Bahnschrift", "DIN Alternate", "Roboto Condensed", "Arial Narrow", "Segoe UI", system-ui, sans-serif';
    const СДВИГ = 21;
    const ГЛИФЫ = "01アイウエオカキクケコサシスセソ水依";

    let агенты = [];
    let узлы = [];
    let по = new Map();
    let кабинеты = [];
    let ш = 0, в = 0, dpr = 1, A = 480, B = 270, фит = 1, подписиВсе = true;
    let камера = { x: 0, y: 0, z: 1 }, цель = { x: 0, y: 0, z: 1 };
    let активен = false, кадр = 0, время = 0, прошлый = 0;
    let выбранКабинет = "";
    try { выбранКабинет = localStorage.getItem("mizuyori.агенты.кабинет") || ""; } catch {}
    let наведён = null, перетаскивание = null;
    let чатЖдёт = 0, поворот = 0;
    const прошлое = new Map();
    const эффекты = [];
    const следы = [];
    const капли = [];
    let последнееПисьмо = null, последнийОпыт = null;

    // ---- расклад: эллипс, шаг по длине дуги ---------------------------------------------------------
    function таблицаЭллипса(a, b) {
      const N = 720, т = [0]; let пред = { x: 0, y: -b };
      for (let i = 1; i <= N; i++) {
        const θ = -Math.PI / 2 + i / N * Math.PI * 2, p = { x: a * Math.cos(θ), y: b * Math.sin(θ) };
        т.push(т[i - 1] + Math.hypot(p.x - пред.x, p.y - пред.y)); пред = p;
      }
      return т;
    }
    function параметр(т, доля) {      // доля 0..1 по длине дуги → угол θ
      const N = т.length - 1, д = Math.max(0, Math.min(1, доля)) * т[N];
      let lo = 1, hi = N;
      while (lo < hi) { const m = (lo + hi) >> 1; if (т[m] < д) lo = m + 1; else hi = m; }
      const f = (д - т[lo - 1]) / ((т[lo] - т[lo - 1]) || 1);
      return -Math.PI / 2 + ((lo - 1 + f) / N) * Math.PI * 2;
    }
    const точкаЭ = (θ, a = A, b = B) => ({ x: a * Math.cos(θ), y: b * Math.sin(θ) });

    function расставить() {
      if (!агенты.length || !ш) return;
      A = B = Math.max(230, Math.min(ш / 2 - 175, в / 2 - 160));
      const сПодписями = Math.min(1, (ш / 2 - 20) / (A + 175), (в / 2 - 12) / (B + 200));
      подписиВсе = сПодписями >= .8;
      фит = подписиВсе ? сПодписями : Math.min(1, (ш / 2 - 20) / (A + 70), (в / 2 - 12) / (B + 90));
      const таб = таблицаЭллипса(A, B);
      const упор = [...агенты].sort((а, б) => (а.порядок_кабинета ?? 99) - (б.порядок_кабинета ?? 99)
        || (а.порядок_отдела ?? 99) - (б.порядок_отдела ?? 99) || Number(Boolean(б.руководитель)) - Number(Boolean(а.руководитель)));
      const группы = [];
      for (const а of упор) {
        const ключК = а.кабинет || "прочее", ключО = `${ключК}/${а.отдел || а.группа || ""}`;
        let кб = группы.find((г) => г.кабинет === ключК);
        if (!кб) группы.push(кб = { кабинет: ключК, отделы: [] });
        let отд = кб.отделы.find((о) => о.ключ === ключО);
        if (!отд) кб.отделы.push(отд = { ключ: ключО, название: а.отдел || а.группа || "", агенты: [] });
        отд.агенты.push(а);
      }
      const ЗК = 2.6, ЗО = .8;
      let мест = 0;
      for (const г of группы) мест += г.отделы.reduce((с, о) => с + о.агенты.length + ЗО, 0) - ЗО + ЗК;
      let слот = ЗК / 2;
      узлы = []; кабинеты = [];
      const вθ = (с) => параметр(таб, (((с % мест) + мест) % мест) / мест);
      for (const г of группы) {
        const нач = слот;
        for (const о of г.отделы) {
          const начО = слот;
          let номер = 0;
          for (const а of о.агенты) {
            const ст = номер++ % 2 ? СДВИГ : 0, θ = вθ(слот + .5), p = точкаЭ(θ, A - ст, B - ст), лидер = Boolean(а.руководитель);
            узлы.push({ а, ключ: а.ключ, θ, ст, x: p.x, y: p.y, нормаль: Math.atan2(p.y / (B * B), p.x / (A * A)), r: лидер ? 12.5 : 9.5, лидер,
              цвет: а.цвет_кабинета || "#6aa9ff", кабинет: г.кабинет, отдел: о.ключ, отделНазвание: о.название });
            слот += 1;
          }
          о.θ0 = вθ(начО); о.θ1 = вθ(слот);
          слот += ЗО;
        }
        слот -= ЗО;
        const члены = узлы.filter((у) => у.кабинет === г.кабинет);
        кабинеты.push({ ключ: г.кабинет, название: члены[0]?.а.кабинет_название || г.кабинет, цвет: члены[0]?.цвет || "#6aa9ff",
          θ0: вθ(нач - .2), θ1: вθ(слот + .2), θм: вθ((нач + слот) / 2), лидер: члены[0],
          отделы: г.отделы.map((о) => ({ название: о.название, θ0: о.θ0, θ1: о.θ1, ключ: о.ключ })) });
        слот += ЗК;
      }
      по = new Map(узлы.map((у) => [у.ключ, у]));
      обновитьПоложения();
    }
    function обновитьПоложения() {
      for (const у of узлы) { const θ = у.θ + поворот, p = точкаЭ(θ, A - у.ст, B - у.ст); у.x = p.x; у.y = p.y; у.нормаль = θ; }
    }

    function размер() {
      const р = лента.getBoundingClientRect();
      dpr = Math.min(2, window.devicePixelRatio || 1);
      ш = Math.max(320, Math.round(р.width)); в = Math.max(320, Math.round(р.height));
      холст.width = Math.round(ш * dpr); холст.height = Math.round(в * dpr);
      капли.length = 0;
      расставить(); сбросКамеры(true);
    }
    function сбросКамеры(сразу = false) {
      цель = { x: 0, y: 0, z: фит };
      if (сразу) камера = { ...цель };
      запустить();
    }

    // ---- пути и эффекты -----------------------------------------------------------------------------
    const ЯДРО = { x: 0, y: 0 };
    const чатТочка = () => ({ x: 0, y: -96 });
    function путь(из, в_) {
      const mx = (из.x + в_.x) / 2 * .38, my = (из.y + в_.y) / 2 * .38;
      return (t) => { const u = 1 - t; return { x: u * u * из.x + 2 * u * t * mx + t * t * в_.x, y: u * u * из.y + 2 * u * t * my + t * t * в_.y }; };
    }
    const прямая = (из, в_) => (t) => ({ x: из.x + (в_.x - из.x) * t, y: из.y + (в_.y - из.y) * t });
    const кабинетУзла = (у) => кабинеты.find((c) => c.ключ === у.кабинет);
    const мягкий = (hex) => (typeof hex === "string" && hex[0] === "#" && hex.length === 7 ? hex : "#6aa9ff");
    const прозрачный = (hex, а) => {
      const h = мягкий(hex).replace("#", "");
      return `rgba(${parseInt(h.slice(0, 2), 16)},${parseInt(h.slice(2, 4), 16)},${parseInt(h.slice(4, 6), 16)},${а})`;
    };
    const тока = (имя) => имя === "ядро" ? () => ЯДРО : имя === "чат-узел" ? чатТочка : () => по.get(имя);

    function комета(откуда, кому, цвет, длит = 1.5, подпись = "", след = true, после = null) {
      const служебный = (н) => н === "ядро" || н === "чат-узел";
      const получатель = служебный(кому) ? null : кому;
      if (безАнимаций()) {
        if (получатель) эффекты.push({ тип: "вспышка", ключ: получатель, t: 0, цвет, подпись });
        if (после) после();
        return;
      }
      const А = тока(откуда), Б = тока(кому);
      if (!А() || !Б()) { if (после) после(); return; }
      эффекты.push({ тип: "комета", откуда: А, куда: Б, прямо: служебный(откуда) || служебный(кому), t: 0, длит, цвет, кому: получатель, подпись, после });
      if (след && !служебный(откуда) && !служебный(кому)) следы.push({ от: откуда, кому, цвет, t: 0 });
      запустить();
    }
    function волна(ключ, цвет, сила = 1) { эффекты.push({ тип: "волна", ключ, t: 0, цвет, сила }); запустить(); }
    function всплеск(ключ, цвет) {
      const у = по.get(ключ); if (!у || безАнимаций()) return;
      for (let i = 0; i < 14; i++) {
        const а = Math.PI * 2 * i / 14 + Math.random() * .3, v = 30 + Math.random() * 40;
        эффекты.push({ тип: "искра", x: у.x, y: у.y, vx: Math.cos(а) * v, vy: Math.sin(а) * v, t: 0, цвет });
      }
      запустить();
    }

    function новыеДанные(д) {
      агенты = д.агенты || [];
      const ключи = агенты.map((а) => `${а.ключ}|${а.кабинет}|${а.отдел}`).join(",");
      if (ключи !== новыеДанные.ключи) { новыеДанные.ключи = ключи; расставить(); сбросКамеры(true); }
      for (const а of агенты) {
        const у = по.get(а.ключ); if (у) у.а = а;
        const было = прошлое.get(а.ключ), цв = а.цвет_кабинета || "#6aa9ff";
        if (было && !было.работает && а.работает && у) {
          const лид = кабинетУзла(у)?.лидер;
          if (лид && лид !== у) комета("ядро", лид.ключ, цв, 1.0, "", false, () => комета(лид.ключ, а.ключ, цв, .9, "", false));
          else комета("ядро", а.ключ, цв, 1.3, "", false);
          волна(а.ключ, цв, 1.2);
        }
        if (было && было.всего < а.всего && !а.работает) {
          const ок = !а.ошибка;
          эффекты.push({ тип: "вспышка", ключ: а.ключ, t: 0, цвет: ок ? "#4ade80" : "#ff5b5b",
            подпись: `${ок ? "✓" : "⚠"} ${String(а.последний_результат || а.последнее_действие || "готово").slice(0, 44)}` });
          всплеск(а.ключ, ок ? "#4ade80" : "#ff5b5b");
        }
        прошлое.set(а.ключ, { работает: а.работает, всего: а.всего });
      }
      разобрать(д.письма, "письмо"); разобрать(д.опыт, "опыт");
      запустить();
    }
    function разобрать(список, вид) {
      if (!список) return;
      const был = вид === "письмо" ? последнееПисьмо : последнийОпыт;
      const новыйId = список.length ? Math.max(...список.map((п) => п.id)) : (был ?? 0);
      const новые = был == null ? [] : список.filter((п) => п.id > был).reverse();
      if (вид === "письмо") последнееПисьмо = новыйId; else последнийОпыт = новыйId;
      for (const п of новые) {
        if (!по.has(п.от)) continue;
        const кому = по.has(п.кому) ? [п.кому] : п.кому === "все" ? агенты.filter((а) => а.ключ !== п.от).slice(0, 4).map((а) => а.ключ) : [];
        const тип = вид === "опыт" ? "опыт" : (п.тип || "работа");
        const цв = тип === "опыт" ? ЦВЕТ_ОПЫТА : тип === "знание" ? ЦВЕТ_ЗНАНИЯ : по.get(п.от).цвет;
        const значок = тип === "опыт" ? "🎓" : тип === "знание" ? "💡" : "📤";
        for (const куда of кому) комета(п.от, куда, цв, 1.7, `${значок} от ${по.get(п.от).а.имя}`);
      }
    }
    document.addEventListener("mizuyori:агенты", (с) => новыеДанные(с.detail));
    document.addEventListener("mizuyori:кабинет", (с) => { выбранКабинет = с.detail || ""; запустить(); });
    // связь с чатом: вопрос уходит в ядро и к «Собеседнику», ответ возвращается в чат
    document.addEventListener("mizuyori:чат-отправлено", () => {
      чатЖдёт = 1;
      комета("чат-узел", "ядро", ЦВЕТ_ЧАТА, .9, "", false, () => комета("ядро", "чат", ЦВЕТ_ЧАТА, .9, "✉ вопрос", false));
    });
    document.addEventListener("mizuyori:чат-готов", () => {
      if (!чатЖдёт) return;
      чатЖдёт = 0;
      комета("чат", "чат-узел", ЦВЕТ_ЧАТА, 1.1, "", false);
      всплеск("чат", ЦВЕТ_ЧАТА);
    });

    // ---- рисование ----------------------------------------------------------------------------------
    const приглушён = (у) => Boolean(выбранКабинет) && у.кабинет !== выбранКабинет;

    function матрица(dt, работают) {
      const шаг = 20;
      if (!капли.length) for (let i = 0; i < Math.ceil(ш / шаг); i++) капли.push({ x: i * шаг + 6, y: Math.random() * в, v: 18 + Math.random() * 40, дл: 6 + Math.random() * 9 });
      к.font = "11px ui-monospace, Consolas, monospace"; к.textAlign = "center"; к.textBaseline = "middle";
      for (const л of капли) {
        л.y += л.v * dt * (работают ? 2.2 : 1);
        if (л.y - л.дл * 13 > в) { л.y = -20; л.v = 18 + Math.random() * 40; }
        for (let i = 0; i < л.дл; i++) {
          const y = л.y - i * 13; if (y < -6 || y > в + 6) continue;
          к.fillStyle = i === 0 ? `rgba(190,235,255,${работают ? .3 : .15})` : `rgba(80,170,230,${(1 - i / л.дл) * (работают ? .13 : .06)})`;
          к.fillText(ГЛИФЫ[Math.floor(время * 3 + л.x * 7 + i * 5) % ГЛИФЫ.length], л.x, y);
        }
      }
    }
    function рисоватьФон(dt, работают) {
      const g = к.createRadialGradient(ш / 2, в / 2, 20, ш / 2, в / 2, Math.max(ш, в) * .65);
      g.addColorStop(0, "#0d1524"); g.addColorStop(1, "#05070c");
      к.fillStyle = g; к.fillRect(0, 0, ш, в);
      if (!безАнимаций()) матрица(dt, работают);
    }
    function эллипс(a, b, θ0, θ1, ширина, стиль) {
      к.beginPath(); к.ellipse(0, 0, a, b, 0, θ0, θ1); к.lineWidth = ширина; к.strokeStyle = стиль; к.lineCap = "round"; к.stroke();
    }
    function рисоватьКольцаФона() {
      к.setLineDash([2, 8]);
      for (const м of [.3, .62]) { к.beginPath(); к.ellipse(0, 0, A * м, B * м, 0, 0, Math.PI * 2); к.lineWidth = 1; к.strokeStyle = "rgba(120,150,200,.1)"; к.stroke(); }
      к.setLineDash([]);
    }

    function рисоватьКабинеты() {
      for (const каб of кабинеты) {
        const тих = Boolean(выбранКабинет) && каб.ключ !== выбранКабинет, а = тих ? .35 : 1;
        к.save(); к.rotate(поворот);
        эллипс(A - 10, B - 10, каб.θ0, каб.θ1, 60, прозрачный(каб.цвет, .09 * а + .02));
        эллипс(A - 44, B - 44, каб.θ0, каб.θ1, 2, прозрачный(каб.цвет, .55 * а));
        for (const о of каб.отделы) эллипс(A - 38, B - 38, о.θ0, о.θ1, 1.2, прозрачный(каб.цвет, .3 * а));
        к.restore();
        const p = точкаЭ(каб.θм + поворот, Math.max(A * .56, 150), Math.max(B * .56, 150));
        const члены = узлы.filter((n) => n.кабинет === каб.ключ), работают = члены.filter((n) => n.а.работает).length;
        к.save(); к.translate(p.x, p.y); к.textAlign = "center"; к.textBaseline = "middle"; к.globalAlpha = тих ? .4 : 1;
        к.font = "700 14px " + ШРИФТ; к.fillStyle = прозрачный(каб.цвет, .98);
        к.fillText(каб.название.toUpperCase().slice(0, 26), 0, -8);
        к.font = "11px ui-monospace, Consolas, monospace"; к.fillStyle = работают ? "#fff" : "rgba(200,210,230,.55)";
        к.fillText(работают ? `${работают} из ${члены.length} работают` : `${члены.length} агентов`, 0, 9);
        к.restore();
      }
    }

    function цепочкаРаботы(у) {
      const лид = кабинетУзла(у)?.лидер;
      return лид && лид !== у ? [прямая(ЯДРО, лид), путь(лид, у)] : [прямая(ЯДРО, у)];
    }
    function тропа(f, цвет, ширина, смещение, альфа) {
      к.beginPath();
      for (let i = 0; i <= 24; i++) { const p = f(i / 24); i ? к.lineTo(p.x, p.y) : к.moveTo(p.x, p.y); }
      к.lineWidth = ширина; к.strokeStyle = прозрачный(цвет, альфа); к.setLineDash([6, 8]); к.lineDashOffset = -смещение; к.stroke();
      к.setLineDash([]); к.lineDashOffset = 0;
    }

    function рисоватьНити() {
      к.lineCap = "round";
      for (const каб of кабинеты) {
        const а = Boolean(выбранКабинет) && каб.ключ !== выбранКабинет ? .25 : 1;
        const члены = узлы.filter((n) => n.кабинет === каб.ключ);
        for (const о of каб.отделы) {
          const ч = члены.filter((n) => n.отдел === о.ключ);
          for (let i = 1; i < ч.length; i++) {
            const раб = ч[i].а.работает || ч[i - 1].а.работает;
            к.beginPath(); к.moveTo(ч[i - 1].x, ч[i - 1].y); к.lineTo(ч[i].x, ч[i].y);
            к.lineWidth = раб ? 3 : 2; к.strokeStyle = прозрачный(каб.цвет, (раб ? .9 : .36) * а); к.stroke();
          }
        }
        if (каб.лидер) for (const у of члены) {
          if (!у.лидер || у === каб.лидер) continue;
          const f = путь(каб.лидер, у);
          к.beginPath();
          for (let i = 0; i <= 16; i++) { const p = f(i / 16); i ? к.lineTo(p.x, p.y) : к.moveTo(p.x, p.y); }
          к.lineWidth = 1; к.strokeStyle = прозрачный(каб.цвет, .22 * а); к.stroke();
        }
        if (каб.лидер) {
          const g = к.createLinearGradient(0, 0, каб.лидер.x, каб.лидер.y);
          g.addColorStop(0, прозрачный(каб.цвет, 0)); g.addColorStop(1, прозрачный(каб.цвет, .42 * а));
          к.beginPath(); к.moveTo(0, 0); к.lineTo(каб.лидер.x * .96, каб.лидер.y * .96); к.lineWidth = 1.4; к.strokeStyle = g; к.stroke();
        }
      }
      // поток работы: бегущие пунктиры и частицы по цепочке ядро → кабинет → агент
      for (const у of узлы) {
        if (!у.а.работает || приглушён(у)) continue;
        const ц = у.а.ошибка ? "#ff5b5b" : у.цвет;
        for (const f of цепочкаРаботы(у)) {
          тропа(f, ц, 2.2, время * 38, .75);
          for (let j = 0; j < 3; j++) {
            const p = f((время * .55 + j / 3) % 1);
            к.beginPath(); к.arc(p.x, p.y, 2.6, 0, Math.PI * 2); к.fillStyle = "rgba(255,255,255,.9)"; к.fill();
          }
        }
      }
      // следы передач гаснут за ~30 секунд
      for (let i = следы.length - 1; i >= 0; i--) {
        const с = следы[i]; с.t += 1 / 60;
        const А = по.get(с.от), Б = по.get(с.кому);
        if (!А || !Б || с.t > 30) { следы.splice(i, 1); continue; }
        const f = путь(А, Б), ал = Math.max(0, 1 - с.t / 30);
        к.beginPath();
        for (let j = 0; j <= 24; j++) { const p = f(j / 24); j ? к.lineTo(p.x, p.y) : к.moveTo(p.x, p.y); }
        к.lineWidth = 1.2 + 2.4 * ал; к.strokeStyle = прозрачный(с.цвет, .15 + .55 * ал); к.stroke();
      }
    }

    function значокУзла(у, x, y, цвет, размер) {
      const п = ИКОНКИ()[у.а.значок];
      if (!п) { к.fillStyle = цвет; к.beginPath(); к.arc(x, y, 2.4, 0, Math.PI * 2); к.fill(); return; }
      if (!у.путь) у.путь = new Path2D(п);
      к.save(); к.translate(x - размер / 2, y - размер / 2); к.scale(размер / 24, размер / 24);
      к.lineWidth = 2.1; к.lineCap = "round"; к.lineJoin = "round"; к.strokeStyle = цвет; к.stroke(у.путь); к.restore();
    }

    function рисоватьУзлы() {
      const максимум = Math.max(1, ...узлы.map((у) => у.а.сегодня || 0));
      for (const у of узлы) {
        const а = у.а, тих = приглушён(у), раб = Boolean(а.работает), ошибка = Boolean(а.ошибка);
        const цв = ошибка ? "#ff5b5b" : у.цвет, фокус = наведён === у, спит = !раб && !(а.сегодня > 0);
        к.save(); к.globalAlpha = тих ? .3 : спит && !фокус ? .66 : 1;
        if (раб) {
          const п = .5 + .5 * Math.sin(время * 5 + у.θ * 3);
          const g = к.createRadialGradient(у.x, у.y, у.r, у.x, у.y, у.r + 22 + п * 8);
          g.addColorStop(0, прозрачный(цв, .6)); g.addColorStop(1, прозрачный(цв, 0));
          к.fillStyle = g; к.beginPath(); к.arc(у.x, у.y, у.r + 30, 0, Math.PI * 2); к.fill();
        }
        к.beginPath(); к.arc(у.x, у.y, у.r, 0, Math.PI * 2);
        const gд = к.createRadialGradient(у.x - у.r * .3, у.y - у.r * .35, 1, у.x, у.y, у.r);
        gд.addColorStop(0, "#1c2740"); gд.addColorStop(1, "#0a0f1b"); к.fillStyle = gд; к.fill();
        к.lineWidth = у.лидер ? 2.6 : 2; к.strokeStyle = прозрачный(цв, фокус || раб ? 1 : .85); к.stroke();
        if (а.сегодня > 0) {
          к.beginPath(); к.arc(у.x, у.y, у.r + 3.4, -Math.PI / 2, -Math.PI / 2 + Math.PI * 2 * Math.min(1, а.сегодня / максимум));
          к.lineWidth = 2; к.strokeStyle = прозрачный(цв, .75); к.stroke();
        }
        if (раб) {
          к.save(); к.translate(у.x, у.y); к.rotate(время * 2.4);
          к.beginPath(); к.arc(0, 0, у.r + 7, 0, Math.PI * 1.35); к.lineWidth = 1.6; к.strokeStyle = цв; к.setLineDash([3, 4]); к.stroke(); к.setLineDash([]);
          к.rotate(-время * 4.4);
          for (let i = 0; i < 3; i++) {
            const θ = i * 2.094; к.beginPath(); к.arc(Math.cos(θ) * (у.r + 12), Math.sin(θ) * (у.r + 12), 1.9, 0, Math.PI * 2);
            к.fillStyle = "rgba(255,255,255,.85)"; к.fill();
          }
          к.restore();
        }
        значокУзла(у, у.x, у.y, ошибка ? "#ffb4b4" : раб ? "#ffffff" : прозрачный(цв, 1), у.r * 1.15);
        if (кабинетУзла(у)?.лидер === у) {
          к.fillStyle = "#f5c451"; к.beginPath();
          к.moveTo(у.x - 5, у.y - у.r - 2); к.lineTo(у.x - 5, у.y - у.r - 7); к.lineTo(у.x - 2.5, у.y - у.r - 4.5); к.lineTo(у.x, у.y - у.r - 8);
          к.lineTo(у.x + 2.5, у.y - у.r - 4.5); к.lineTo(у.x + 5, у.y - у.r - 7); к.lineTo(у.x + 5, у.y - у.r - 2); к.closePath(); к.fill();
        }
        к.restore();
      }
    }

    function рисоватьПодписи() {
      к.textBaseline = "middle";
      for (const у of узлы) {
        const фокус = наведён === у, раб = Boolean(у.а.работает);
        if (!подписиВсе && камера.z < 1.15 && !у.лидер && !фокус && !раб) continue;
        const имя = у.а.имя || у.ключ, макс = подписиВсе ? 22 : 17;
        const текст = имя.length > макс ? `${имя.slice(0, макс - 1)}…` : имя;
        к.save(); к.translate(у.x, у.y);
        const слева = Math.cos(у.нормаль) < 0;
        к.rotate(слева ? у.нормаль + Math.PI : у.нормаль);
        к.textAlign = слева ? "right" : "left";
        к.font = `${у.лидер ? "700 13px" : "12px"} ${ШРИФТ}`;
        к.fillStyle = раб || фокус ? "#ffffff" : у.лидер ? "rgba(235,240,252,.94)" : "rgba(190,202,226,.74)";
        к.globalAlpha = приглушён(у) ? .22 : 1;
        const сдв = (у.r + 10 + у.ст) * (слева ? -1 : 1);
        if (у.ст) { к.beginPath(); к.moveTo((у.r + 2) * (слева ? -1 : 1), 0); к.lineTo(сдв - 3 * (слева ? -1 : 1), 0); к.lineWidth = 1; к.strokeStyle = прозрачный(у.цвет, .3); к.stroke(); }
        к.fillText(текст, сдв, 0);
        к.restore();
      }
    }

    function рисоватьЯдро(работают) {
      const п = .5 + .5 * Math.sin(время * (работают ? 4 : 1.4));
      const g = к.createRadialGradient(0, 0, 8, 0, 0, 80 + п * 8);
      g.addColorStop(0, `rgba(88,196,255,${.28 + (работают ? .22 : 0)})`); g.addColorStop(1, "rgba(88,196,255,0)");
      к.fillStyle = g; к.beginPath(); к.arc(0, 0, 92, 0, Math.PI * 2); к.fill();
      if (работают && !безАнимаций()) {   // радар и расходящиеся кольца, пока кто-то работает
        if (к.createConicGradient) {
          к.save(); к.rotate(время * 1.1);
          const gg = к.createConicGradient(0, 0, 0);
          gg.addColorStop(0, "rgba(88,196,255,0)"); gg.addColorStop(.9, "rgba(88,196,255,0)"); gg.addColorStop(.985, "rgba(88,196,255,.14)"); gg.addColorStop(1, "rgba(160,225,255,.3)");
          к.fillStyle = gg; к.beginPath(); к.arc(0, 0, Math.min(A, B) * .92, 0, Math.PI * 2); к.fill(); к.restore();
        }
        for (let i = 0; i < 2; i++) {
          const т = (время * .6 + i * .5) % 1;
          к.beginPath(); к.arc(0, 0, 36 + т * 70, 0, Math.PI * 2); к.lineWidth = 1.6 * (1 - т); к.strokeStyle = `rgba(120,210,255,${(1 - т) * .55})`; к.stroke();
        }
      }
      к.save(); к.rotate(время * .25); к.setLineDash([2, 6]); к.lineWidth = 1; к.strokeStyle = "rgba(160,200,255,.35)";
      к.beginPath(); к.arc(0, 0, 56, 0, Math.PI * 2); к.stroke(); к.setLineDash([]);
      for (let i = 0; i < кабинеты.length; i++) {
        const θ = i * Math.PI * 2 / кабинеты.length;
        к.beginPath(); к.arc(Math.cos(θ) * 56, Math.sin(θ) * 56, 2.8, 0, Math.PI * 2); к.fillStyle = кабинеты[i].цвет; к.fill();
      }
      к.restore();
      к.beginPath(); к.arc(0, 0, 33, 0, Math.PI * 2); к.fillStyle = "#070b14"; к.fill(); к.lineWidth = 2; к.strokeStyle = "rgba(210,230,255,.88)"; к.stroke();
      к.beginPath(); к.moveTo(0, -14); к.bezierCurveTo(10, -2, 11, 4, 0, 13); к.bezierCurveTo(-11, 4, -10, -2, 0, -14);
      к.lineWidth = 2.4; к.strokeStyle = "#e8f2ff"; к.stroke();
      к.textAlign = "center"; к.textBaseline = "middle"; к.font = "700 9px ui-monospace, Consolas, monospace"; к.fillStyle = "rgba(190,210,240,.78)"; к.fillText("MIZUYORI", 0, 46);
      if (работают) { к.font = "10px ui-monospace, Consolas, monospace"; к.fillStyle = "#fff"; к.fillText(`${работают} в работе`, 0, 59); }
    }

    // узел чата внутри круга, над ядром: сообщение идёт отсюда в ядро и к «Собеседнику»
    function рисоватьЧат() {
      const { x, y } = чатТочка();
      к.save();
      к.beginPath(); к.moveTo(x, y + 15); к.lineTo(0, -34);
      к.lineWidth = 1.4; к.strokeStyle = прозрачный(ЦВЕТ_ЧАТА, чатЖдёт ? .8 : .3); к.setLineDash([3, 5]); к.lineDashOffset = -время * (чатЖдёт ? 50 : 6); к.stroke(); к.setLineDash([]);
      if (чатЖдёт) {
        const g = к.createRadialGradient(x, y, 6, x, y, 36); g.addColorStop(0, прозрачный(ЦВЕТ_ЧАТА, .45)); g.addColorStop(1, прозрачный(ЦВЕТ_ЧАТА, 0));
        к.fillStyle = g; к.beginPath(); к.arc(x, y, 36, 0, Math.PI * 2); к.fill();
      }
      к.beginPath(); к.arc(x, y, 14, 0, Math.PI * 2); к.fillStyle = "#08101c"; к.fill(); к.lineWidth = 2; к.strokeStyle = ЦВЕТ_ЧАТА; к.stroke();
      к.lineWidth = 1.6; к.strokeStyle = "#e8f6ff"; к.lineJoin = "round"; к.beginPath();
      к.moveTo(x - 6, y - 5); к.lineTo(x + 6, y - 5); к.lineTo(x + 6, y + 2.5); к.lineTo(x + 1, y + 2.5); к.lineTo(x - 3.5, y + 7); к.lineTo(x - 3.5, y + 2.5); к.lineTo(x - 6, y + 2.5); к.closePath(); к.stroke();
      к.font = "700 11px " + ШРИФТ; к.textAlign = "left"; к.textBaseline = "middle"; к.fillStyle = "rgba(200,225,250,.92)"; к.fillText("ЧАТ", x + 20, y - 4);
      к.font = "10px " + ШРИФТ; к.fillStyle = чатЖдёт ? "#fff" : "rgba(160,185,215,.6)"; к.fillText(чатЖдёт ? "думают агенты…" : "на связи", x + 20, y + 8);
      к.restore();
    }

    function рисоватьЭффекты(dt) {
      for (let i = эффекты.length - 1; i >= 0; i--) {
        const э = эффекты[i]; э.t += dt;
        if (э.тип === "комета") {
          const А = э.откуда(), Б = э.куда(); if (!А || !Б) { эффекты.splice(i, 1); continue; }
          const f = э.прямо ? прямая(А, Б) : путь(А, Б), т = Math.min(1, э.t / э.длит), ц = мягкий(э.цвет);
          for (let j = 0; j < 16; j++) {
            const p = f(Math.max(0, т - j * .017));
            к.beginPath(); к.arc(p.x, p.y, Math.max(.8, 4.6 - j * .3), 0, Math.PI * 2); к.fillStyle = прозрачный(ц, (1 - j / 16) * .88); к.fill();
          }
          const p = f(т), g = к.createRadialGradient(p.x, p.y, 0, p.x, p.y, 17);
          g.addColorStop(0, "rgba(255,255,255,.95)"); g.addColorStop(1, "rgba(255,255,255,0)"); к.fillStyle = g; к.beginPath(); к.arc(p.x, p.y, 17, 0, Math.PI * 2); к.fill();
          if (т >= 1) {
            эффекты.splice(i, 1);
            if (э.кому) { эффекты.push({ тип: "вспышка", ключ: э.кому, t: 0, цвет: э.цвет, подпись: э.подпись }); всплеск(э.кому, э.цвет); }
            if (э.после) э.после();
          }
        } else if (э.тип === "волна") {
          const у = по.get(э.ключ), т = э.t / (1.3 * э.сила);
          if (!у || т >= 1) { эффекты.splice(i, 1); continue; }
          к.beginPath(); к.arc(у.x, у.y, у.r + т * 50, 0, Math.PI * 2); к.lineWidth = 2.4 * (1 - т); к.strokeStyle = прозрачный(э.цвет, (1 - т) * .85); к.stroke();
        } else if (э.тип === "искра") {
          if (э.t > .9) { эффекты.splice(i, 1); continue; }
          const x = э.x + э.vx * э.t, y = э.y + э.vy * э.t + 30 * э.t * э.t, ал = 1 - э.t / .9;
          к.beginPath(); к.arc(x, y, 2.2 * ал + .4, 0, Math.PI * 2); к.fillStyle = прозрачный(э.цвет, ал); к.fill();
        } else if (э.тип === "вспышка") {
          const у = по.get(э.ключ), т = э.t / 2.6;
          if (!у || т >= 1) { эффекты.splice(i, 1); continue; }
          const ц = мягкий(э.цвет);
          к.beginPath(); к.arc(у.x, у.y, у.r + 4 + т * 26, 0, Math.PI * 2); к.lineWidth = 3 * (1 - т); к.strokeStyle = прозрачный(ц, (1 - т) * .9); к.stroke();
          if (э.подпись) {
            к.save(); к.globalAlpha = Math.min(1, (1 - т) * 2.2); к.font = "600 12px " + ШРИФТ; к.textAlign = "center"; к.textBaseline = "middle";
            const w = к.measureText(э.подпись).width + 16, yy = у.y - у.r - 24 - т * 8;
            к.fillStyle = "rgba(8,12,22,.94)"; к.strokeStyle = ц; к.lineWidth = 1; к.beginPath(); к.roundRect(у.x - w / 2, yy - 10, w, 20, 9); к.fill(); к.stroke();
            к.fillStyle = "#f2f6ff"; к.fillText(э.подпись, у.x, yy); к.restore();
          }
        }
      }
    }

    function кадрРисовать(t) {
      кадр = 0;
      if (!активен) return;
      const dt = Math.min(.05, (t - прошлый) / 1000 || .016); прошлый = t; время += dt;
      if (чатЖдёт) { чатЖдёт += dt; if (чатЖдёт > 120) чатЖдёт = 0; }
      if (!безАнимаций()) { поворот += dt * .03; обновитьПоложения(); }
      const k_ = Math.min(1, dt * 5);
      камера.x += (цель.x - камера.x) * k_; камера.y += (цель.y - камера.y) * k_; камера.z += (цель.z - камера.z) * k_;
      const работают = агенты.filter((а) => а.работает).length;
      к.setTransform(dpr, 0, 0, dpr, 0, 0);
      рисоватьФон(dt, работают > 0 || чатЖдёт > 0);
      к.save(); к.translate(ш / 2 + камера.x, в / 2 + камера.y); к.scale(камера.z, камера.z);
      рисоватьКольцаФона(); рисоватьКабинеты(); рисоватьНити(); рисоватьУзлы(); рисоватьЯдро(работают); рисоватьЧат(); рисоватьПодписи(); рисоватьЭффекты(dt);
      к.restore();
      if (безАнимаций() && !эффекты.length) return;
      кадр = requestAnimationFrame(кадрРисовать);
    }
    function запустить() { if (активен && !кадр) { прошлый = performance.now(); кадр = requestAnimationFrame(кадрРисовать); } }

    // ---- мышь ---------------------------------------------------------------------------------------
    const вМир = (ев) => {
      const р = холст.getBoundingClientRect();
      return { x: (ев.clientX - р.left - ш / 2 - камера.x) / камера.z, y: (ев.clientY - р.top - в / 2 - камера.y) / камера.z, px: ев.clientX - р.left, py: ев.clientY - р.top };
    };
    function найти(м) {
      let лучший = null, d = 1e9;
      for (const у of узлы) { const r = Math.hypot(у.x - м.x, у.y - м.y); if (r < Math.max(у.r + 6, 16 / камера.z) && r < d) { d = r; лучший = у; } }
      return лучший;
    }
    function показатьПодсказку(у, м) {
      if (!у) { подсказка.hidden = true; return; }
      const а = у.а;
      подсказка.replaceChildren(
        создать("b", { текст: а.имя || у.ключ }),
        создать("small", { текст: `${а.кабинет_название || ""} · ${у.отделНазвание || ""}` }),
        создать("span", { текст: а.работает ? "работает…" : а.ошибка ? `ошибка: ${а.ошибка}` : а.сегодня ? `сегодня дел: ${а.сегодня}` : "ждёт задачу" }),
        ...(а.последнее_действие ? [создать("em", { текст: `${а.последнее_действие}${а.последний_результат ? ` → ${String(а.последний_результат).slice(0, 70)}` : ""}` })] : []),
        создать("small", { текст: "клик — история, память, записки" }));
      подсказка.hidden = false;
      подсказка.style.transform = `translate(${Math.max(8, Math.min(ш - 260, м.px + 16))}px, ${Math.max(8, Math.min(в - 130, м.py + 14))}px)`;
    }
    холст.addEventListener("pointermove", (ев) => {
      const м = вМир(ев);
      const у = найти(м);
      if (у !== наведён) { наведён = у; холст.style.cursor = у ? "pointer" : "default"; запустить(); }
      показатьПодсказку(у, м);
    });
    холст.addEventListener("pointerleave", () => { наведён = null; подсказка.hidden = true; запустить(); });
    холст.addEventListener("click", (ев) => { const у = найти(вМир(ев)); if (у) window.открытьАгента?.(у.ключ); });

    // ---- переключатель вида -------------------------------------------------------------------------
    const УЗКО = matchMedia("(max-width: 62rem)");
    let вид = "граф";
    try { вид = localStorage.getItem("mizuyori.агенты.вид") || (УЗКО.matches ? "список" : "граф"); } catch {}
    function применитьВид() {
      лента.classList.toggle("режим-граф", вид === "граф");
      кнопкаВида.textContent = вид === "граф" ? "Кабинеты" : "Граф";
      кнопкаВида.title = вид === "граф" ? "Показать агентов по кабинетам (список)" : "Показать агентов графом, как в «Мозгах»";
      активен = вид === "граф" && !лента.closest("main")?.hidden;
      if (активен) { размер(); запустить(); } else window.dispatchEvent(new Event("resize"));
    }
    кнопкаВида.addEventListener("click", () => {
      вид = вид === "граф" ? "список" : "граф";
      try { localStorage.setItem("mizuyori.агенты.вид", вид); } catch {}
      применитьВид();
    });
    new ResizeObserver(() => { if (вид === "граф") размер(); }).observe(лента);
    document.addEventListener("mizuyori:экран", (с) => { активен = вид === "граф" && с.detail === "главная"; if (активен) { размер(); запустить(); } });
    document.addEventListener("visibilitychange", () => { if (!document.hidden) запустить(); });
    применитьВид();
  }
}
