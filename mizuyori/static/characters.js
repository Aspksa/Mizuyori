"use strict";

// =============================================================================
// Персонажи агентов: у каждого из 26 свой оригинальный герой, нарисованный вектором (чёткий на любом экране, хоть в 4K).
//
// Герой собран из слоёв: аура → тень → тело (шесть форм) → шея → голова (пять форм) → экран-лицо с глазами → руки → реквизит
// по профессии (каска, весы, штамп, песочные часы…). Цвета — из палитры агента (переменные --c1/--cl/--cd/--cg).
// Состояния читаются из классов плитки `.агент` (работает, спит, ошибка, успех) — вся анимация в CSS.
//
// window.персонаж(ключ) → <svg class="персонаж">; window.ПЕРСОНАЖИ — таблица для витрины.
// =============================================================================
{
  const NS = "http://www.w3.org/2000/svg";
  let счётчик = 0;

  // ключ → [оттенок, тело, голова, глаза, украшение, ядро-на-груди]
  const ГЕРОИ = {
    чат: [186, "капсула", "купол", "овал", "ушки", true],
    память: [152, "бочка", "квадрат", "полоса", "антенна", true],
    смысл: [208, "шар", "сфера", "круг", "ушки", true],
    сводка: [268, "колокол", "купол", "овал", "антенна", false],
    цели: [340, "броня", "гекс", "полоса", "рожки", true],
    мнения: [322, "шар", "сфера", "овал", "ушки", true],
    смотрящий: [166, "трапеция", "визор", "одноглаз", "антенна", true],
    инженер: [214, "броня", "квадрат", "овал", "нет", false],
    механик: [28, "трапеция", "квадрат", "полоса", "ушки", true],
    диспетчер: [196, "капсула", "визор", "полоса", "нет", true],
    трассировщик: [170, "колокол", "купол", "круг", "антенна", true],
    кадровик: [258, "капсула", "сфера", "овал", "ушки", false],
    юрист: [232, "бочка", "гекс", "овал", "нет", true],
    водитель: [48, "трапеция", "купол", "круг", "нет", false],
    экономист: [44, "бочка", "визор", "овал", "антенна", true],
    делопроизводитель: [334, "капсула", "квадрат", "полоса", "нет", true],
    снабженец: [24, "колокол", "сфера", "круг", "антенна", true],
    архивариус: [198, "бочка", "купол", "круг", "нет", true],
    контрагенты: [140, "капсула", "гекс", "овал", "ушки", true],
    проверяющий: [96, "броня", "визор", "одноглаз", "нет", true],
    секретарь: [306, "колокол", "сфера", "овал", "ушки", true],
    сроки: [8, "трапеция", "гекс", "полоса", "рожки", true],
    охрана: [120, "броня", "купол", "овал", "нет", false],
    гсмконтроль: [18, "бочка", "квадрат", "круг", "антенна", true],
    склад: [38, "трапеция", "квадрат", "полоса", "нет", true],
    бухгалтер: [158, "капсула", "визор", "круг", "нет", true],
    главбух: [152, "броня", "гекс", "полоса", "нет", true],
    замглав: [168, "трапеция", "визор", "овал", "антенна", true],
    ос_ведущий: [188, "броня", "квадрат", "круг", "нет", true],
    ос_бух: [196, "капсула", "купол", "овал", "ушки", true],
    мат_ведущий: [136, "бочка", "квадрат", "полоса", "нет", true],
    зап_бух: [124, "трапеция", "сфера", "круг", "антенна", true],
    зп_ведущий: [176, "колокол", "визор", "овал", "нет", true],
    зп_водители: [162, "капсула", "купол", "круг", "нет", false],
    зп_ауп: [146, "шар", "сфера", "овал", "ушки", true],
    кон_ведущий: [180, "броня", "гекс", "полоса", "рожки", true],
    реализация: [132, "бочка", "купол", "овал", "антенна", true],
    подотчёт: [190, "колокол", "сфера", "круг", "ушки", false],
    налоги: [158, "броня", "визор", "одноглаз", "нет", true],
    касса_старший: [142, "бочка", "гекс", "круг", "нет", true],
    кассир: [150, "капсула", "квадрат", "овал", "антенна", true],
    мастер_ремзоны: [22, "броня", "квадрат", "полоса", "нет", true],
    дефектовщик: [34, "трапеция", "визор", "круг", "антенна", true],
    шины_акб: [14, "шар", "купол", "овал", "нет", true],
    аналитик: [218, "колокол", "гекс", "полоса", "антенна", true],
    плановик: [226, "капсула", "визор", "овал", "нет", true],
    себестоимость: [206, "бочка", "сфера", "круг", "ушки", true],
    цены: [236, "трапеция", "купол", "овал", "антенна", true],
    парк_экономист: [212, "броня", "квадрат", "круг", "рожки", true],
    дог_ведущий: [352, "броня", "гекс", "полоса", "нет", true],
    дог_перевозки: [8, "трапеция", "квадрат", "овал", "ушки", true],
    дог_аренда: [330, "капсула", "визор", "полоса", "антенна", true],
    прет_ведущий: [348, "бочка", "визор", "овал", "рожки", true],
    прет_дтп: [14, "колокол", "купол", "круг", "нет", true],
    прет_дебиторка: [340, "трапеция", "сфера", "полоса", "рожки", true],
    закуп_юрист: [356, "шар", "гекс", "овал", "антенна", true],
    регуляция: [4, "броня", "купол", "одноглаз", "нет", true],
    дог_архив: [322, "бочка", "квадрат", "круг", "ушки", true],
  };

  const ТЕЛА = {
    капсула: 'M34 74Q34 66 42 66H78Q86 66 86 74V108Q86 124 60 124Q34 124 34 108Z',
    трапеция: 'M36 68H84L92 114Q92 124 82 124H38Q28 124 28 114Z',
    бочка: 'M32 78Q60 62 88 78L92 108Q60 130 28 108Z',
    шар: 'M60 68A28 28 0 1 1 59.9 68Z',
    броня: 'M30 70H90V104Q90 124 60 130Q30 124 30 104Z',
    колокол: 'M44 66H76Q94 98 94 120Q94 124 90 124H30Q26 124 26 120Q26 98 44 66Z',
  };
  // голова: [контур, экран x,y,w,h,rx]
  const ГОЛОВЫ = {
    купол: ['M36 56A24 24 0 0 1 84 56V62Q84 72 74 72H46Q36 72 36 62Z', 41, 42, 38, 24, 12],
    квадрат: ['M48 22H72Q86 22 86 36V58Q86 72 72 72H48Q34 72 34 58V36Q34 22 48 22Z', 39, 33, 42, 30, 11],
    визор: ['M46 30H74Q92 30 92 50Q92 68 74 68H46Q28 68 28 50Q28 30 46 30Z', 34, 38, 52, 24, 12],
    сфера: ['M60 22A26 26 0 1 1 59.9 22Z', 40, 36, 40, 28, 13],
    гекс: ['M60 18L85 32V58L60 74L35 58V32Z', 41, 34, 38, 28, 10],
  };

  const ГЛАЗА = {
    овал: (x, y, д) => `<ellipse class="глаз" cx="${x}" cy="${y}" rx="3.4" ry="5"/>`,
    круг: (x, y) => `<circle class="глаз" cx="${x}" cy="${y}" r="4.2"/>`,
    полоса: (x, y) => `<rect class="глаз" x="${x - 4.6}" y="${y - 1.9}" width="9.2" height="3.8" rx="1.9"/>`,
  };

  // ---- реквизит: каждый рисуется своими руками, цвета палитры и немного «золота», «бумаги» и «красного» ----
  const ЗОЛОТО = 'fill="url(#§z)" stroke="#8a5d00" stroke-width=".8"';
  const Р = {
    чат: () => `<g class="проп плав"><path d="M76 4H108Q114 4 114 10V26Q114 32 108 32H98L90 40V32H76Q70 32 70 26V10Q70 4 76 4Z" fill="url(#§g)" stroke="var(--cl)" stroke-width="1.2"/>
      <circle class="т т1" cx="82" cy="18" r="2.6"/><circle class="т т2" cx="92" cy="18" r="2.6"/><circle class="т т3" cx="102" cy="18" r="2.6"/></g>
      <g class="проп плав п2"><rect x="-6" y="30" width="26" height="15" rx="7.5" fill="url(#§g)" stroke="var(--cl)" stroke-width="1"/><circle class="т т2" cx="2" cy="37.5" r="1.8"/><circle class="т т1" cx="8" cy="37.5" r="1.8"/><circle class="т т3" cx="14" cy="37.5" r="1.8"/></g>`,
    память: () => `<g class="проп плав"><rect x="-8" y="76" width="34" height="22" rx="4" fill="url(#§m)" stroke="var(--cd)"/>
      <rect x="-4" y="80" width="26" height="14" rx="2.5" fill="#080d1a"/><path class="цепь" d="M0 84h8l3 4h9M0 90h6l3-3h8" stroke="var(--cg)" stroke-width="1.2" fill="none"/>
      ${[0, 1, 2, 3, 4].map((i) => `<rect x="${-6 + i * 7}" y="72" width="3" height="4" fill="#d7dbe4"/><rect x="${-6 + i * 7}" y="98" width="3" height="4" fill="#d7dbe4"/>`).join("")}</g>
      <g class="проп п2"><circle class="искр" cx="104" cy="22" r="2.5"/><circle class="искр и2" cx="112" cy="40" r="2"/><circle class="искр и3" cx="100" cy="52" r="1.6"/></g>`,
    смысл: () => `<g class="проп вращ"><g class="созв"><path d="M98 8L114 26L100 42L116 60M98 8L100 42M114 26L116 60" stroke="var(--cl)" stroke-width="1.1" fill="none" opacity=".8"/>
      ${[[98, 8], [114, 26], [100, 42], [116, 60]].map(([x, y], i) => `<circle class="узел" style="animation-delay:${i * .4}s" cx="${x}" cy="${y}" r="3.4"/>`).join("")}</g></g>
      <g class="проп п2"><circle class="искр" cx="6" cy="40" r="2.2"/><circle class="искр и2" cx="-2" cy="62" r="1.8"/></g>`,
    сводка: () => `<g class="проп плав"><rect x="-8" y="78" width="34" height="38" rx="3" fill="#f6ecd0" stroke="#b79b5b"/><rect x="-11" y="75" width="40" height="7" rx="3.5" fill="#d9bd78" stroke="#a88a42"/><rect x="-11" y="112" width="40" height="7" rx="3.5" fill="#d9bd78" stroke="#a88a42"/>
      <path d="M-2 90H20M-2 96H16M-2 102H20" stroke="#8f7a4a" stroke-width="1.4"/></g>
      <g class="проп перо"><path d="M96 118Q106 90 120 60Q114 86 104 120Z" fill="url(#§m)" stroke="var(--cd)" stroke-width=".8"/><path d="M99 112Q108 88 118 66" stroke="var(--cd)" stroke-width=".8" fill="none"/></g>`,
    цели: () => `<g class="проп плав"><circle cx="104" cy="30" r="15" fill="#fff" stroke="#c33" stroke-width="1"/><circle cx="104" cy="30" r="10.5" fill="#e23c4a"/><circle cx="104" cy="30" r="6.5" fill="#fff"/><circle class="центр" cx="104" cy="30" r="3.2" fill="#e23c4a"/>
      <path d="M104 30L120 12" stroke="#9a6a2d" stroke-width="2"/><path d="M116 8l8 0-3 8zM122 14l0 8-8-3z" fill="var(--cl)"/></g>
      <g class="проп п2"><path d="M2 40v-30" stroke="#ccd" stroke-width="2"/><path d="M2 10h20l-5 6 5 6H2z" fill="var(--c1)" stroke="var(--cd)"/></g>`,
    мнения: () => `<g class="проп сердце"><path d="M60 28C44 12 38 4 46 -1C54 -5 60 2 60 6C60 2 66 -5 74 -1C82 4 76 12 60 28Z" fill="url(#§h)" stroke="#fff" stroke-opacity=".6" stroke-width="1"/></g>
      <g class="проп п2"><circle class="искр" cx="22" cy="22" r="2.4"/><circle class="искр и2" cx="100" cy="16" r="2"/><circle class="искр и3" cx="108" cy="48" r="1.7"/></g>`,
    смотрящий: () => `<g class="проп плав"><path d="M60 24V8" stroke="var(--cd)" stroke-width="3"/><circle cx="60" cy="2" r="10" fill="#f4f6fb" stroke="var(--cd)" stroke-width="1.5"/><circle class="зрачок" cx="60" cy="2" r="5.2" fill="var(--c1)"/><circle class="зрачок" cx="60" cy="2" r="2.4" fill="#06101a"/><circle cx="57.6" cy="-.4" r="1.2" fill="#fff"/></g>
      <g class="проп п2"><path class="луч" d="M96 66L122 52M96 70L124 70M96 74L122 88" stroke="var(--cg)" stroke-width="1.4" opacity=".7"/></g>`,
    инженер: () => `<g class="проп"><path d="M30 36Q30 8 60 8Q90 8 90 36Z" fill="url(#§y)" stroke="#a97500" stroke-width="1.2"/><rect x="25" y="34" width="70" height="7" rx="3.5" fill="#f1b800" stroke="#a97500"/><rect x="55" y="8" width="10" height="26" fill="#ffe69a" opacity=".75"/><path d="M40 16Q48 10 56 10" stroke="#fff" stroke-opacity=".7" stroke-width="2" fill="none"/></g>
      <g class="проп плав"><rect x="-10" y="86" width="40" height="14" rx="7" fill="#2f6fd6" stroke="#173f86"/><path d="M-3 90H22M-3 95H18" stroke="#cfe3ff" stroke-width="1.2"/><circle cx="-10" cy="93" r="6" fill="#dbe9ff" stroke="#173f86"/></g>`,
    механик: () => `<g class="проп шест"><circle cx="-2" cy="88" r="12" fill="none" stroke="url(#§m)" stroke-width="6" stroke-dasharray="4.4 4.2"/><circle cx="-2" cy="88" r="9" fill="url(#§m)" stroke="var(--cd)"/><circle cx="-2" cy="88" r="3.6" fill="#0a0f1a"/></g>
      <g class="проп гайка"><path d="M100 120L120 78" stroke="#c9ced8" stroke-width="6" stroke-linecap="round"/><path d="M100 120L120 78" stroke="#fff" stroke-opacity=".6" stroke-width="1.6" stroke-linecap="round"/><path d="M114 66A10 10 0 1 1 124 82L120 80L118 74L112 72Z" fill="#c9ced8" stroke="#8a91a0"/></g>`,
    диспетчер: () => `<g class="проп"><path d="M32 50Q32 14 60 14Q88 14 88 50" fill="none" stroke="#2a2f3d" stroke-width="5" stroke-linecap="round"/><rect x="25" y="42" width="11" height="17" rx="5" fill="#3a4156" stroke="var(--cl)"/><rect x="84" y="42" width="11" height="17" rx="5" fill="#3a4156" stroke="var(--cl)"/><path d="M30 58Q32 70 48 70" stroke="#2a2f3d" stroke-width="3" fill="none"/><circle cx="50" cy="70" r="3.4" fill="var(--cg)"/></g>
      <g class="проп"><circle cx="104" cy="94" r="15" fill="#04150e" stroke="var(--cl)" stroke-width="1.5"/><circle cx="104" cy="94" r="9" fill="none" stroke="var(--cg)" stroke-opacity=".4"/><path class="радар" d="M104 94L104 80" stroke="var(--cg)" stroke-width="2"/><circle class="точка т1" cx="98" cy="90" r="1.6"/><circle class="точка т2" cx="110" cy="99" r="1.6"/></g>`,
    трассировщик: () => `<g class="проп"><path class="путь" d="M2 118Q20 96 12 84T34 66" stroke="var(--cg)" stroke-width="2.2" stroke-dasharray="4 4" fill="none"/><circle cx="2" cy="118" r="3" fill="var(--cl)"/></g>
      <g class="проп плав"><path d="M104 8Q116 8 116 20Q116 30 104 44Q92 30 92 20Q92 8 104 8Z" fill="#ef4d4d" stroke="#8d1c1c" stroke-width="1.2"/><circle cx="104" cy="20" r="5" fill="#fff"/></g>
      <g class="проп п2 лупа"><circle cx="104" cy="96" r="11" fill="url(#§g)" stroke="#c9ced8" stroke-width="3"/><path d="M112 104L122 116" stroke="#c9ced8" stroke-width="4" stroke-linecap="round"/></g>`,
    кадровик: () => `<g class="проп"><path d="M50 70L60 98L70 70" stroke="var(--cl)" stroke-width="2.4" fill="none"/><g class="бейдж"><rect x="48" y="96" width="24" height="30" rx="3.5" fill="#fff" stroke="var(--cd)" stroke-width="1.4"/><rect x="48" y="96" width="24" height="7" rx="3" fill="var(--c1)"/><circle cx="60" cy="111" r="5.5" fill="#cfd6e4"/><path d="M52 124Q60 114 68 124Z" fill="#cfd6e4"/></g></g>
      <g class="проп"><circle cx="30" cy="48" r="4.5" fill="#f5f6fa"/><circle cx="26" cy="54" r="4.5" fill="#f5f6fa"/><circle cx="90" cy="48" r="4.5" fill="#f5f6fa"/><circle cx="94" cy="54" r="4.5" fill="#f5f6fa"/></g>`,
    юрист: () => `<g class="проп"><path d="M32 40Q22 30 30 24Q34 36 40 34M88 40Q98 30 90 24Q86 36 80 34" fill="#f5f6fa" stroke="#c4c9d6"/><circle cx="30" cy="42" r="5.5" fill="#f5f6fa" stroke="#c4c9d6"/><circle cx="90" cy="42" r="5.5" fill="#f5f6fa" stroke="#c4c9d6"/><circle cx="26" cy="52" r="5" fill="#f5f6fa" stroke="#c4c9d6"/><circle cx="94" cy="52" r="5" fill="#f5f6fa" stroke="#c4c9d6"/></g>
      <g class="проп весы"><path d="M104 40V108M96 108H112" stroke="#d9be6a" stroke-width="3" stroke-linecap="round"/><g class="балка"><path d="M86 52H122" stroke="#d9be6a" stroke-width="3" stroke-linecap="round"/><path d="M86 52L80 70H92ZM122 52L116 70H128Z" fill="none" stroke="#d9be6a"/><path d="M78 70H94Q92 76 86 76Q80 76 78 70ZM114 70H130Q128 76 122 76Q116 76 114 70Z" ${ЗОЛОТО}/></g></g>`,
    водитель: () => `<g class="проп"><path d="M34 30Q40 12 62 12Q82 12 90 28L96 34Q88 30 84 32H38Q32 32 28 36Z" fill="url(#§m)" stroke="var(--cd)" stroke-width="1.2"/><path d="M28 36Q60 44 96 34" stroke="var(--cd)" stroke-width="3" fill="none"/></g>
      <g class="проп руль"><circle cx="60" cy="102" r="20" fill="none" stroke="#252a38" stroke-width="6"/><circle cx="60" cy="102" r="20" fill="none" stroke="var(--cl)" stroke-width="1.3"/><circle cx="60" cy="102" r="6" fill="#252a38" stroke="var(--cl)"/><path d="M60 96V84M54 105L42 111M66 105L78 111" stroke="#252a38" stroke-width="4" stroke-linecap="round"/></g>`,
    экономист: () => `<g class="проп плав"><ellipse cx="6" cy="116" rx="14" ry="5" ${ЗОЛОТО}/><ellipse cx="6" cy="110" rx="14" ry="5" ${ЗОЛОТО}/><ellipse cx="6" cy="104" rx="14" ry="5" ${ЗОЛОТО}/><ellipse cx="6" cy="98" rx="14" ry="5" ${ЗОЛОТО}/><text x="6" y="101" text-anchor="middle" font-size="8" font-weight="700" fill="#8a5d00">₽</text></g>
      <g class="проп п2"><rect x="92" y="78" width="9" height="16" rx="1.5" fill="var(--c1)"/><rect x="104" y="66" width="9" height="28" rx="1.5" fill="var(--cl)"/><rect x="116" y="52" width="9" height="42" rx="1.5" fill="var(--cg)"/><path class="стрела" d="M90 70L104 56L112 62L126 42M118 40H127V49" stroke="#3ee08a" stroke-width="2.2" fill="none" stroke-linecap="round" stroke-linejoin="round"/></g>`,
    делопроизводитель: () => `<g class="проп плав"><rect x="-6" y="92" width="32" height="6" rx="1" fill="#f6f8fc" stroke="#b9c0d0"/><rect x="-4" y="98" width="32" height="6" rx="1" fill="#eef1f8" stroke="#b9c0d0"/><rect x="-6" y="104" width="32" height="6" rx="1" fill="#f6f8fc" stroke="#b9c0d0"/><rect x="-6" y="110" width="32" height="6" rx="1" fill="#e6eaf4" stroke="#b9c0d0"/></g>
      <g class="проп штамп"><rect x="94" y="66" width="18" height="6" rx="3" fill="#252a38"/><rect x="100" y="70" width="6" height="22" fill="#6a4a2a"/><rect x="92" y="90" width="22" height="9" rx="2" fill="#ef4d4d" stroke="#8d1c1c"/></g><g class="проп след"><rect x="92" y="108" width="24" height="10" rx="2" fill="none" stroke="#ef4d4d" stroke-width="1.6"/></g>`,
    снабженец: () => `<g class="проп тележка"><path d="M-10 78H6L14 108H46L52 88H12" stroke="var(--cl)" stroke-width="3" fill="none" stroke-linejoin="round" stroke-linecap="round"/><path d="M14 90H50L46 106H17Z" fill="url(#§g)" stroke="var(--cl)" stroke-width="1.4"/><circle cx="20" cy="116" r="4.6" fill="#252a38" stroke="var(--cl)"/><circle cx="42" cy="116" r="4.6" fill="#252a38" stroke="var(--cl)"/>
      <rect x="22" y="76" width="22" height="16" rx="2" fill="#c89a5b" stroke="#7a5528"/><path d="M22 82H44" stroke="#7a5528"/><rect x="29" y="79" width="8" height="5" fill="#f4ead6"/></g>
      <g class="проп п2"><rect x="96" y="14" width="20" height="14" rx="3" fill="#fff" stroke="var(--cd)"/><text x="106" y="25" text-anchor="middle" font-size="9" font-weight="700" fill="#e23c4a">-%</text></g>`,
    архивариус: () => `<g class="проп"><circle cx="49" cy="52" r="9.5" fill="none" stroke="#d9be6a" stroke-width="2.4"/><circle cx="71" cy="52" r="9.5" fill="none" stroke="#d9be6a" stroke-width="2.4"/><path d="M58.5 52H61.5" stroke="#d9be6a" stroke-width="2.4"/></g>
      <g class="проп плав"><rect x="-10" y="84" width="40" height="32" rx="3" fill="#c9a36a" stroke="#7a5a2a"/><rect x="-10" y="84" width="40" height="9" rx="3" fill="#b78d50" stroke="#7a5a2a"/><rect x="2" y="100" width="16" height="9" rx="1.5" fill="#f4ead6" stroke="#7a5a2a"/><path d="M5 104H15" stroke="#7a5a2a"/></g>`,
    контрагенты: () => `<g class="проп сцеп"><rect x="-8" y="76" width="22" height="13" rx="6.5" fill="none" stroke="var(--cl)" stroke-width="3.4"/><rect x="6" y="76" width="22" height="13" rx="6.5" fill="none" stroke="var(--cg)" stroke-width="3.4"/></g>
      <g class="проп плав п2"><rect x="92" y="62" width="26" height="34" rx="3" fill="#fff" stroke="var(--cd)" stroke-width="1.3"/><path d="M97 71H113M97 77H113M97 83H107" stroke="#9aa3b8" stroke-width="1.6"/><path class="подпись" d="M97 91Q101 85 104 91T112 90" stroke="var(--c1)" stroke-width="1.6" fill="none"/></g>`,
    проверяющий: () => `<g class="проп лупа"><circle cx="102" cy="88" r="16" fill="url(#§g)" stroke="#c9ced8" stroke-width="4"/><path d="M113 100L124 114" stroke="#c9ced8" stroke-width="5" stroke-linecap="round"/><path class="галка" d="M94 88L100 94L111 81" stroke="#3ee08a" stroke-width="3.4" fill="none" stroke-linecap="round" stroke-linejoin="round"/></g>
      <g class="проп п2"><rect x="-8" y="82" width="26" height="32" rx="3" fill="#fff" stroke="var(--cd)"/><path d="M-2 92H12M-2 98H12M-2 104H8" stroke="#9aa3b8" stroke-width="1.6"/><circle cx="14" cy="108" r="4" fill="#3ee08a"/></g>`,
    секретарь: () => `<g class="проп письмо"><rect x="86" y="62" width="32" height="22" rx="3" fill="#fff" stroke="var(--cd)" stroke-width="1.3"/><path class="клапан" d="M86 64L102 76L118 64" stroke="var(--c1)" stroke-width="1.6" fill="none"/><circle class="уведом" cx="118" cy="62" r="5" fill="#ef4d4d"/></g>
      <g class="проп"><path d="M34 44Q34 22 60 22Q86 22 86 44" fill="none" stroke="var(--cd)" stroke-width="3.6" stroke-linecap="round"/><circle cx="33" cy="47" r="6" fill="var(--c1)" stroke="var(--cd)"/><circle cx="87" cy="47" r="6" fill="var(--c1)" stroke="var(--cd)"/></g>
      <g class="проп плав п2"><path d="M-4 114L18 80L22 84L2 116Z" fill="var(--cl)" stroke="var(--cd)"/><path d="M-4 114L-6 120L0 118Z" fill="#252a38"/></g>`,
    сроки: () => `<g class="проп песок"><path d="M92 38H122M92 110H122" stroke="#d9be6a" stroke-width="4" stroke-linecap="round"/><path d="M96 38V50Q96 62 107 74Q96 86 96 98V110M118 38V50Q118 62 107 74Q118 86 118 98V110" fill="none" stroke="#e8f4ff" stroke-width="2" opacity=".85"/><path d="M99 42H115Q113 54 107 66Q101 54 99 42Z" fill="var(--cg)" opacity=".85"/><path class="струйка" d="M107 66V98" stroke="var(--cg)" stroke-width="1.6"/><path d="M98 108Q107 90 116 108Z" fill="var(--cg)" opacity=".85"/></g>
      <g class="проп п2"><circle cx="8" cy="86" r="14" fill="#0a1220" stroke="var(--cl)" stroke-width="2"/><path class="стрелка" d="M8 86V76" stroke="var(--cg)" stroke-width="2" stroke-linecap="round"/><path d="M8 86H15" stroke="#fff" stroke-width="2" stroke-linecap="round"/></g>`,
    охрана: () => `<g class="проп"><path d="M30 38Q30 10 60 10Q90 10 90 38Z" fill="url(#§w)" stroke="#aeb6c6" stroke-width="1.2"/><rect x="25" y="36" width="70" height="7" rx="3.5" fill="#e8ecf4" stroke="#aeb6c6"/><rect x="55" y="10" width="10" height="26" fill="#3ec978" opacity=".9"/></g>
      <g class="проп"><path d="M60 82L74 87V100Q74 111 60 116Q46 111 46 100V87Z" fill="#3ec978" stroke="#17703c" stroke-width="1.2"/><path d="M60 90V108M52 99H68" stroke="#fff" stroke-width="3.6" stroke-linecap="round"/></g>
      <g class="проп п2"><path d="M96 76Q100 90 108 92" stroke="#252a38" stroke-width="2.4" fill="none"/><circle cx="110" cy="94" r="5.4" fill="#f1b800" stroke="#a97500"/></g>`,
    гсмконтроль: () => `<g class="проп плав"><path d="M-8 84H18L26 92V122H-8Z" fill="#e0453f" stroke="#7e1713" stroke-width="1.3"/><rect x="-2" y="78" width="14" height="8" rx="2" fill="#7e1713"/><path d="M-4 96H20M-4 104H20" stroke="#ff9d97" stroke-width="1.2"/><path d="M6 100l6 8h-12z" fill="#fff" opacity=".85"/></g>
      <g class="проп п2"><path d="M86 74A18 18 0 0 1 122 74" fill="none" stroke="#2a2f3d" stroke-width="5" stroke-linecap="round"/><path d="M89 72A15 15 0 0 1 119 72" fill="none" stroke="var(--cg)" stroke-width="2" stroke-dasharray="3 3"/><path class="стрелка" d="M104 74L113 62" stroke="#fff" stroke-width="2.2" stroke-linecap="round"/><circle cx="104" cy="74" r="3" fill="#fff"/></g>`,
    склад: () => `<g class="проп плав"><rect x="-10" y="100" width="26" height="22" rx="2" fill="#c89a5b" stroke="#7a5528"/><path d="M-10 108H16M3 100V122" stroke="#7a5528"/><rect x="18" y="106" width="24" height="16" rx="2" fill="#d6aa6b" stroke="#7a5528"/><path d="M18 112H42" stroke="#7a5528"/><rect x="0" y="80" width="26" height="20" rx="2" fill="#d9b072" stroke="#7a5528"/><path d="M0 87H26M13 80V100" stroke="#7a5528"/></g>
      <g class="проп п2 скан"><rect x="96" y="76" width="18" height="30" rx="3" fill="#252a38" stroke="var(--cl)"/><rect x="99" y="80" width="12" height="10" rx="1" fill="var(--cg)" opacity=".8"/><path class="лучик" d="M105 106V122" stroke="#ff4a4a" stroke-width="1.6"/></g>`,
    бухгалтер: () => `<g class="проп"><path d="M28 30Q60 22 92 30L88 38Q60 32 32 38Z" fill="#2fbf71" stroke="#17703c" stroke-width="1.2" opacity=".9"/></g>
      <g class="проп плав"><rect x="86" y="62" width="34" height="48" rx="5" fill="url(#§m)" stroke="var(--cd)" stroke-width="1.3"/><rect x="90" y="67" width="26" height="12" rx="2" fill="#071410"/><text class="цифры" x="114" y="77" text-anchor="end" font-size="9" font-family="monospace" fill="var(--cg)">0,00</text>
      ${[0, 1, 2].flatMap((r) => [0, 1, 2].map((c) => `<rect x="${91 + c * 9}" y="${83 + r * 8}" width="6.4" height="5.6" rx="1.2" fill="#e8ecf4" opacity=".85"/>`)).join("")}</g>`,
  };

  // ---- кабинеты: общие детали реквизита ----
  const КОРОНА = `<g class="проп плав"><path d="M42 24L45 6L54 16L60 2L66 16L75 6L78 24Z" ${ЗОЛОТО} stroke-linejoin="round"/><circle cx="60" cy="9" r="2" fill="#ff5b5b"/><circle cx="45" cy="7" r="1.6" fill="#7ee6ff"/><circle cx="75" cy="7" r="1.6" fill="#7ee6ff"/></g>`;
  const ЗВЕЗДА = `<g class="проп плав п2"><path d="M106 4l3.2 7 7.6.8-5.7 5.2 1.7 7.5L106 20.4 99.2 24.5l1.7-7.5-5.7-5.2 7.6-.8z" ${ЗОЛОТО} stroke-linejoin="round"/></g>`;
  const ЛИДЕРЫ = new Set(["дог_ведущий", "прет_ведущий", "закуп_юрист", "регуляция", "дог_архив", "ос_ведущий", "мат_ведущий", "зп_ведущий", "кон_ведущий", "замглав", "касса_старший", "мастер_ремзоны", "плановик", "цены"]);
  const КОРОНОВАННЫЕ = new Set(["главбух", "юрист"]);
  const банкнота = (x, y, r = 0) => `<g transform="translate(${x} ${y}) rotate(${r})"><rect x="-15" y="-8.5" width="30" height="17" rx="2.6" fill="#c8efd2" stroke="#2f7a4a" stroke-width="1.2"/><circle cx="0" cy="0" r="4.6" fill="none" stroke="#2f7a4a"/><text x="0" y="3" text-anchor="middle" font-size="7.5" font-weight="700" fill="#2f7a4a">₽</text><circle cx="-10" cy="0" r="1.3" fill="#2f7a4a"/><circle cx="10" cy="0" r="1.3" fill="#2f7a4a"/></g>`;
  const монеты = (x, y, н = 3) => Array.from({ length: н }, (_, i) => `<ellipse cx="${x}" cy="${y - i * 5.5}" rx="13" ry="4.6" ${ЗОЛОТО}/>`).join("") + `<text x="${x}" y="${y - (н - 1) * 5.5 + 2.6}" text-anchor="middle" font-size="7.5" font-weight="700" fill="#8a5d00">₽</text>`;
  const документ = (x, y, строки = 3, шапка = "var(--c1)") => `<rect x="${x}" y="${y}" width="24" height="31" rx="3" fill="#fff" stroke="var(--cd)" stroke-width="1.3"/><rect x="${x}" y="${y}" width="24" height="6" rx="3" fill="${шапка}"/>` +
    Array.from({ length: строки }, (_, i) => `<path d="M${x + 4} ${y + 12 + i * 5.5}H${x + 20 - (i % 2) * 5}" stroke="#9aa3b8" stroke-width="1.5"/>`).join("");
  const книга = (x, y, цвет) => `<rect x="${x}" y="${y}" width="30" height="38" rx="3" fill="${цвет}" stroke="var(--cd)" stroke-width="1.3"/><rect x="${x + 4}" y="${y + 5}" width="22" height="9" rx="1.5" fill="#fff" opacity=".9"/><path d="M${x + 4} ${y + 21}H${x + 26}M${x + 4} ${y + 27}H${x + 20}" stroke="#fff" stroke-opacity=".7" stroke-width="1.6"/><rect x="${x - 3}" y="${y + 2}" width="4" height="34" rx="1.5" fill="var(--cd)"/>`;
  const шестерня = (x, y, р = 11) => `<g transform="translate(${x} ${y})"><circle r="${р}" fill="url(#§m)" stroke="var(--cd)" stroke-width="1.2" stroke-dasharray="5 2.6"/><circle r="${р - 3}" fill="url(#§m)" stroke="var(--cd)"/><circle r="${р / 3}" fill="#0a0f1a"/></g>`;
  const ценник = (x, y, т = "₽") => `<g transform="translate(${x} ${y})"><path d="M-14 -10H8L16 0L8 10H-14Z" fill="#fff" stroke="var(--cd)" stroke-width="1.3"/><circle cx="-8" cy="0" r="2.2" fill="var(--c1)"/><text x="2" y="3.4" text-anchor="middle" font-size="9" font-weight="700" fill="var(--cd)">${т}</text></g>`;
  const кассовый = (x, y) => `<rect x="${x}" y="${y + 12}" width="38" height="20" rx="3" fill="url(#§m)" stroke="var(--cd)" stroke-width="1.3"/><rect x="${x + 4}" y="${y}" width="30" height="14" rx="2.5" fill="#071410" stroke="var(--cl)"/><text class="цифры" x="${x + 31}" y="${y + 10.5}" text-anchor="end" font-size="8" font-family="monospace" fill="var(--cg)">0,00</text>` +
    [0, 1, 2, 3].map((i) => `<rect x="${x + 4 + i * 8}" y="${y + 18}" width="6" height="4.4" rx="1" fill="#e8ecf4" opacity=".85"/>`).join("") + `<rect x="${x + 4}" y="${y + 25}" width="30" height="3.6" rx="1.2" fill="#0a0f1a"/>`;
  const график = (x, y) => `<rect x="${x}" y="${y}" width="40" height="30" rx="3" fill="#0a1220" stroke="var(--cl)" stroke-width="1.2"/><path class="стрела" d="M${x + 4} ${y + 24}L${x + 13} ${y + 15}L${x + 21} ${y + 20}L${x + 35} ${y + 6}" stroke="#3ee08a" stroke-width="2" fill="none" stroke-linecap="round" stroke-linejoin="round"/><path d="M${x + 4} ${y + 27}H${x + 36}" stroke="#4b5878"/>`;
  const машинка = (x, y) => `<g transform="translate(${x} ${y})"><path d="M0 14V9L4 2H20L26 9V14Z" fill="url(#§m)" stroke="var(--cd)" stroke-width="1.2" stroke-linejoin="round"/><path d="M6 3.4H18L22 9H3Z" fill="#cfe3ff" opacity=".85"/><circle cx="7" cy="15" r="3.6" fill="#252a38" stroke="var(--cl)"/><circle cx="20" cy="15" r="3.6" fill="#252a38" stroke="var(--cl)"/></g>`;
  const грузовик = (x, y) => `<g transform="translate(${x} ${y})"><rect x="0" y="0" width="22" height="16" rx="2" fill="url(#§m)" stroke="var(--cd)" stroke-width="1.2"/><path d="M22 5H30L35 10V16H22Z" fill="url(#§m)" stroke="var(--cd)" stroke-width="1.2"/><circle cx="8" cy="18" r="3.8" fill="#252a38" stroke="var(--cl)"/><circle cx="28" cy="18" r="3.8" fill="#252a38" stroke="var(--cl)"/></g>`;
  const портфель = (x, y) => `<rect x="${x}" y="${y + 6}" width="32" height="22" rx="3.5" fill="#8a5a2a" stroke="#4f3216" stroke-width="1.3"/><path d="M${x + 10} ${y + 6}V${y + 2}H${x + 22}V${y + 6}" fill="none" stroke="#4f3216" stroke-width="2"/><path d="M${x} ${y + 15}H${x + 32}" stroke="#4f3216"/><rect x="${x + 13}" y="${y + 13}" width="6" height="5" rx="1" fill="#e8b33a"/>`;
  const шина = (x, y) => `<g transform="translate(${x} ${y})"><circle r="15" fill="#1a1d28" stroke="#3a4156" stroke-width="1.4"/><circle r="9.5" fill="none" stroke="#0a0c12" stroke-width="2.4" stroke-dasharray="3 2.4"/><circle r="6.5" fill="url(#§m)" stroke="var(--cd)"/><circle r="2" fill="#0a0f1a"/></g>`;
  const батарея = (x, y) => `<rect x="${x}" y="${y + 4}" width="30" height="20" rx="2.6" fill="#2a2f3d" stroke="var(--cl)" stroke-width="1.2"/><rect x="${x + 4}" y="${y}" width="6" height="5" rx="1" fill="#c9ced8"/><rect x="${x + 20}" y="${y}" width="6" height="5" rx="1" fill="#c9ced8"/><path class="стрела" d="M${x + 16} ${y + 8}l-5 7h5l-2 7 7-9h-5z" fill="#ffd84a"/>`;
  Object.assign(Р, {
    главбух: () => КОРОНА + `<g class="проп плав"><g>${книга(-14, 82, "#1f8f63")}</g></g><g class="проп плав п2">${банкнота(106, 74, 12)}${монеты(106, 112)}</g>`,
    замглав: () => `<g class="проп плав">${документ(-12, 82, 4, "var(--cg)")}<path d="M16 86L22 80M16 94L22 88" stroke="var(--cl)" stroke-width="1.4"/></g><g class="проп плав п2">${график(86, 74)}</g>`,
    ос_ведущий: () => `<g class="проп плав">${машинка(-14, 92)}<path d="M-14 112H14" stroke="var(--cl)" stroke-width="1.4"/></g><g class="проп плав п2">${документ(92, 82, 3)}<path d="M96 108H108" stroke="#2fbf71" stroke-width="2.2" stroke-linecap="round"/></g>`,
    ос_бух: () => `<g class="проп плав">${машинка(-14, 84)}<path class="стрела" d="M-6 108L6 118L18 110M12 118H20V110" stroke="#ff7a5b" stroke-width="2" fill="none" stroke-linecap="round" stroke-linejoin="round"/></g><g class="проп плав п2"><rect x="92" y="84" width="22" height="22" rx="4" fill="#eef1f8" stroke="var(--cd)" stroke-width="1.3"/><text x="103" y="100" text-anchor="middle" font-size="9" font-weight="700" fill="var(--cd)">Т₽</text><path d="M96 112H110" stroke="var(--cl)" stroke-width="1.4"/></g>`,
    мат_ведущий: () => `<g class="проп плав"><rect x="-12" y="102" width="26" height="20" rx="2" fill="#c89a5b" stroke="#7a5528"/><path d="M-12 108H14M1 102V122" stroke="#7a5528"/><rect x="-6" y="82" width="26" height="20" rx="2" fill="#d9b072" stroke="#7a5528"/><path d="M-6 88H20M7 82V102" stroke="#7a5528"/></g><g class="проп плав п2">${документ(92, 80, 3)}<path d="M96 106l3 3 6-6" stroke="#2fbf71" stroke-width="2" fill="none" stroke-linecap="round"/></g>`,
    зап_бух: () => `<g class="проп плав">${шестерня(4, 96, 12)}${шестерня(24, 112, 8)}</g><g class="проп плав п2">${ценник(104, 84)}<path d="M96 100H116M96 106H112" stroke="#9aa3b8" stroke-width="1.6"/></g>`,
    зп_ведущий: () => `<g class="проп плав">${документ(-12, 80, 4, "#2fbf71")}<text x="0" y="111" text-anchor="middle" font-size="7" font-weight="700" fill="var(--cd)">₽</text></g><g class="проп плав п2">${монеты(104, 116, 4)}</g>`,
    зп_водители: () => `<g class="проп руль"><circle cx="2" cy="100" r="15" fill="none" stroke="#252a38" stroke-width="5"/><circle cx="2" cy="100" r="15" fill="none" stroke="var(--cl)" stroke-width="1.1"/><circle cx="2" cy="100" r="4.6" fill="#252a38"/><path d="M2 96V86M-2 102L-12 107M6 102L16 107" stroke="#252a38" stroke-width="3" stroke-linecap="round"/></g><g class="проп плав п2">${банкнота(106, 96, -10)}${банкнота(108, 106, 6)}</g>`,
    зп_ауп: () => `<g class="проп плав"><rect x="-12" y="84" width="30" height="22" rx="3" fill="#fff" stroke="var(--cd)" stroke-width="1.3"/><circle cx="3" cy="93" r="3.4" fill="#cfd6e4"/><path d="M-6 104Q3 97 12 104Z" fill="#cfd6e4"/><path d="M8 112H28" stroke="var(--cl)" stroke-width="1.4"/></g><g class="проп плав п2">${банкнота(106, 84, 8)}${банкнота(104, 100, -6)}</g>`,
    кон_ведущий: () => `<g class="проп плав"><circle cx="2" cy="98" r="15" fill="#0a1220" stroke="var(--cl)" stroke-width="1.6"/><path class="стрела" d="M-8 94H10M5 89L10 94L5 99M12 104H-6M-1 99L-6 104L-1 109" stroke="var(--cg)" stroke-width="1.8" fill="none" stroke-linecap="round" stroke-linejoin="round"/></g><g class="проп плав п2">${документ(94, 82, 3)}${документ(104, 92, 3, "var(--cg)")}</g>`,
    реализация: () => `<g class="проп плав">${грузовик(-16, 94)}<path d="M-16 118H22" stroke="var(--cl)" stroke-width="1.4"/></g><g class="проп плав п2">${документ(92, 78, 4, "#ff9b3d")}<text x="104" y="113" text-anchor="middle" font-size="7.5" font-weight="700" fill="var(--cd)">УПД</text></g>`,
    подотчёт: () => `<g class="проп плав">${портфель(-16, 86)}</g><g class="проп плав п2"><path d="M94 72h24v38l-4-3-4 3-4-3-4 3-4-3-4 3z" fill="#fff" stroke="var(--cd)" stroke-width="1.3"/><path d="M99 82H113M99 88H113M99 94H108" stroke="#9aa3b8" stroke-width="1.5"/></g>`,
    налоги: () => `<g class="проп плав"><path d="M-6 80L12 74L30 80V100Q30 114 12 120Q-6 114 -6 100Z" fill="#0a1220" stroke="var(--cl)" stroke-width="1.6"/><text x="12" y="104" text-anchor="middle" font-size="19" font-weight="800" fill="var(--cg)">%</text></g><g class="проп плав п2"><rect x="92" y="76" width="28" height="30" rx="3.5" fill="#fff" stroke="var(--cd)" stroke-width="1.3"/><rect x="92" y="76" width="28" height="8" rx="3.5" fill="#ef4d4d"/><text x="106" y="100" text-anchor="middle" font-size="12" font-weight="800" fill="var(--cd)">28</text></g>`,
    касса_старший: () => `<g class="проп плав">${кассовый(-18, 86)}</g><g class="проп плав п2"><circle cx="104" cy="90" r="7" fill="none" stroke="#d9be6a" stroke-width="2.6"/><path d="M104 97V116M104 108H112M104 114H110" stroke="#d9be6a" stroke-width="2.6" stroke-linecap="round"/></g>`,
    кассир: () => `<g class="проп плав">${кассовый(-18, 84)}</g><g class="проп плав п2">${банкнота(106, 90, 8)}${монеты(106, 118, 2)}</g>`,
    мастер_ремзоны: () => `<g class="проп"><path d="M30 38Q30 8 60 8Q90 8 90 38Z" fill="url(#§y)" stroke="#a97500" stroke-width="1.2"/><rect x="25" y="36" width="70" height="7" rx="3.5" fill="#f1b800" stroke="#a97500"/><rect x="55" y="8" width="10" height="26" fill="#ffe69a" opacity=".75"/></g><g class="проп гайка"><path d="M100 120L120 78" stroke="#c9ced8" stroke-width="6" stroke-linecap="round"/><path d="M114 66A10 10 0 1 1 124 82L120 80L118 74L112 72Z" fill="#c9ced8" stroke="#8a91a0"/></g><g class="проп плав п2">${шестерня(2, 104, 13)}</g>`,
    дефектовщик: () => `<g class="проп лупа"><circle cx="102" cy="92" r="14" fill="url(#§g)" stroke="#c9ced8" stroke-width="3.6"/><path d="M112 102L122 114" stroke="#c9ced8" stroke-width="4.6" stroke-linecap="round"/><path d="M96 86l12 12M108 86L96 98" stroke="#ff5b5b" stroke-width="2.4" stroke-linecap="round"/></g><g class="проп плав п2"><rect x="-12" y="80" width="28" height="36" rx="3" fill="#fff" stroke="var(--cd)" stroke-width="1.3"/><rect x="-5" y="76" width="14" height="7" rx="2" fill="#6b7287"/><path d="M-6 94H12M-6 101H12M-6 108H8" stroke="#9aa3b8" stroke-width="1.5"/><path d="M-8 94l2 2M-8 101l2 2" stroke="#ff5b5b" stroke-width="1.6"/></g>`,
    шины_акб: () => `<g class="проп плав">${шина(8, 100)}</g><g class="проп плав п2">${батарея(92, 90)}</g>`,
    аналитик: () => `<g class="проп плав">${график(-20, 80)}</g><g class="проп плав п2"><circle cx="106" cy="90" r="14" fill="#0a1220" stroke="var(--cl)" stroke-width="1.6"/><path class="стрелка" d="M106 90L113 82" stroke="var(--cg)" stroke-width="2.2" stroke-linecap="round"/><path d="M95 95A11 11 0 0 1 117 95" fill="none" stroke="#3ee08a" stroke-width="2" stroke-dasharray="3 3"/><circle cx="106" cy="90" r="2.4" fill="#fff"/></g>`,
    плановик: () => `<g class="проп плав"><rect x="-14" y="78" width="32" height="34" rx="3.5" fill="#fff" stroke="var(--cd)" stroke-width="1.3"/><rect x="-14" y="78" width="32" height="8" rx="3.5" fill="var(--c1)"/>${[0, 1, 2].flatMap((r) => [0, 1, 2, 3].map((c) => `<rect x="${-10 + c * 7}" y="${90 + r * 7}" width="4.4" height="4.4" rx="1" fill="${r === 1 && c === 2 ? "var(--cg)" : "#cfd6e4"}"/>`)).join("")}</g><g class="проп плав п2"><circle cx="106" cy="90" r="13" fill="#fff" stroke="#c33"/><circle cx="106" cy="90" r="8.5" fill="#e23c4a"/><circle cx="106" cy="90" r="4" fill="#fff"/><path d="M106 90L120 74" stroke="#9a6a2d" stroke-width="2"/></g>`,
    себестоимость: () => `<g class="проп плав">${шестерня(4, 98, 13)}</g><g class="проп плав п2">${монеты(104, 116, 3)}<g transform="translate(104 78)"><rect x="-14" y="-8" width="28" height="16" rx="4" fill="#fff" stroke="var(--cd)" stroke-width="1.2"/><text x="0" y="3.4" text-anchor="middle" font-size="8" font-weight="700" fill="var(--cd)">₽/км</text></g></g>`,
    цены: () => `<g class="проп плав">${ценник(6, 98, "₽")}<path class="стрела" d="M-10 112H18" stroke="var(--cl)" stroke-width="1.4"/></g><g class="проп плав п2"><path d="M104 56V108M96 108H112" stroke="#d9be6a" stroke-width="3" stroke-linecap="round"/><path d="M86 66H122" stroke="#d9be6a" stroke-width="3" stroke-linecap="round"/><path d="M86 66L80 82H92ZM122 66L116 82H128Z" fill="none" stroke="#d9be6a"/><path d="M78 82H94Q92 88 86 88Q80 88 78 82ZM114 82H130Q128 88 122 88Q116 88 114 82Z" ${ЗОЛОТО}/></g>`,
    парк_экономист: () => `<g class="проп плав">${машинка(-16, 88)}<path d="M-16 112H10" stroke="var(--cl)" stroke-width="1.4"/></g><g class="проп плав п2"><circle cx="106" cy="92" r="15" fill="var(--cd)" stroke="var(--cl)" stroke-width="1.2"/><path d="M106 92V77A15 15 0 0 1 120 98Z" fill="var(--cg)"/><path d="M106 92L120 98A15 15 0 0 1 98 105Z" fill="#ffd84a"/></g>`,
  });

  const ПО_УМОЛЧАНИЮ = [200, "капсула", "купол", "овал", "ушки", true];

  function разметка(ключ, id) {
    const [, тело, голова, глаза, укр, ядро] = ГЕРОИ[ключ] || ПО_УМОЛЧАНИЮ;
    const [контур, ех, еу, эш, эв, эр] = ГОЛОВЫ[голова];
    const цх = ех + эш / 2, цу = еу + эв / 2;
    const разнос = Math.min(эш * .24, 11);
    const глаз = глаза === "одноглаз"
      ? `<ellipse class="глаз большой" cx="${цх}" cy="${цу}" rx="${эш * .24}" ry="${эв * .34}"/>`
      : (ГЛАЗА[глаза] || ГЛАЗА.овал)(цх - разнос, цу) + (ГЛАЗА[глаза] || ГЛАЗА.овал)(цх + разнос, цу);
    const укрАсы = {
      антенна: `<path d="M60 ${голова === "гекс" ? 18 : 22}V8" stroke="var(--cd)" stroke-width="2.4"/><circle class="маяк" cx="60" cy="6" r="4.4"/>`,
      ушки: `<circle cx="${ех - 3}" cy="${цу}" r="5.6" fill="url(#§m)" stroke="var(--cd)"/><circle cx="${ех + эш + 3}" cy="${цу}" r="5.6" fill="url(#§m)" stroke="var(--cd)"/><circle class="маяк мал" cx="${ех - 3}" cy="${цу}" r="2"/><circle class="маяк мал" cx="${ех + эш + 3}" cy="${цу}" r="2"/>`,
      рожки: `<path d="M42 28L36 10L50 24ZM78 28L84 10L70 24Z" fill="url(#§m)" stroke="var(--cd)" stroke-linejoin="round"/>`,
      нет: "",
    }[укр];
    return `<defs>
      <linearGradient id="${id}m" x1="0" y1="0" x2=".15" y2="1"><stop offset="0" style="stop-color:var(--cl)"/><stop offset=".5" style="stop-color:var(--c1)"/><stop offset="1" style="stop-color:var(--cd)"/></linearGradient>
      <linearGradient id="${id}g" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#fff" stop-opacity=".62"/><stop offset=".5" stop-color="#fff" stop-opacity=".12"/><stop offset="1" stop-color="#fff" stop-opacity=".3"/></linearGradient>
      <radialGradient id="${id}a" cx=".5" cy=".5" r=".5"><stop offset="0" style="stop-color:var(--cg)" stop-opacity=".5"/><stop offset=".6" style="stop-color:var(--cg)" stop-opacity=".12"/><stop offset="1" style="stop-color:var(--cg)" stop-opacity="0"/></radialGradient>
      <linearGradient id="${id}s" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#05080f"/><stop offset="1" stop-color="#16203a"/></linearGradient>
      <linearGradient id="${id}z" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#ffe9a0"/><stop offset=".55" stop-color="#e8b33a"/><stop offset="1" stop-color="#b57c10"/></linearGradient>
      <linearGradient id="${id}y" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#ffe27a"/><stop offset="1" stop-color="#f1b000"/></linearGradient>
      <linearGradient id="${id}w" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#fff"/><stop offset="1" stop-color="#cdd3e0"/></linearGradient>
      <radialGradient id="${id}h" cx=".4" cy=".3" r=".8"><stop offset="0" stop-color="#ffd1e6"/><stop offset=".5" style="stop-color:var(--cg)"/><stop offset="1" style="stop-color:var(--cd)"/></radialGradient>
    </defs>
    <circle class="аура" cx="60" cy="76" r="66" fill="url(#${id}a)"/>
    <ellipse class="тень" cx="60" cy="134" rx="34" ry="5.5" fill="#000" opacity=".45"/>
    <g class="героя">
      <g class="тело-героя">
        <path d="${ТЕЛА[тело]}" fill="url(#${id}m)" stroke="var(--cd)" stroke-width="1.6" stroke-linejoin="round"/>
        <path d="${ТЕЛА[тело]}" fill="url(#${id}g)" opacity=".55" transform="translate(60 98) scale(.86) translate(-60 -98)"/>
        <path d="M44 112Q60 119 76 112" stroke="var(--cd)" stroke-opacity=".55" stroke-width="1.4" fill="none"/>
        ${ядро ? `<circle cx="60" cy="96" r="9.5" fill="#06101a" stroke="var(--cl)" stroke-width="1.4"/><circle class="ядро" cx="60" cy="96" r="5.4"/><circle cx="58" cy="94" r="1.5" fill="#fff" opacity=".9"/>` : ""}
        <rect x="52" y="63" width="16" height="9" rx="3" fill="var(--cd)"/>
      </g>
      <g class="рука р1"><circle cx="25" cy="98" r="8" fill="url(#${id}m)" stroke="var(--cd)" stroke-width="1.4"/><ellipse cx="22.6" cy="95" rx="3" ry="2" fill="#fff" opacity=".55"/></g>
      <g class="рука р2"><circle cx="95" cy="98" r="8" fill="url(#${id}m)" stroke="var(--cd)" stroke-width="1.4"/><ellipse cx="92.6" cy="95" rx="3" ry="2" fill="#fff" opacity=".55"/></g>
      <g class="голова-героя">
        ${укрАсы}
        <path d="${контур}" fill="url(#${id}m)" stroke="var(--cd)" stroke-width="1.6" stroke-linejoin="round"/>
        <rect x="${ех}" y="${еу}" width="${эш}" height="${эв}" rx="${эр}" fill="url(#${id}s)" stroke="var(--cl)" stroke-opacity=".55" stroke-width="1"/>
        <g class="лицо"><g class="г-обычно">${глаз}</g>
          <g class="г-скан"><rect class="скан-полоса" x="${ех + 4}" y="${цу - 1.4}" width="${эш - 8}" height="2.8" rx="1.4"/></g>
          <g class="г-ошибка"><path d="M${цх - разнос - 3} ${цу - 3}l6 6M${цх - разнос + 3} ${цу - 3}l-6 6M${цх + разнос - 3} ${цу - 3}l6 6M${цх + разнос + 3} ${цу - 3}l-6 6" stroke="#ff5b5b" stroke-width="2.2" stroke-linecap="round"/></g>
          <path class="рот" d="M${цх - 4} ${цу + эв * .3}Q${цх} ${цу + эв * .3 + 3} ${цх + 4} ${цу + эв * .3}" stroke="var(--cg)" stroke-width="1.4" fill="none" stroke-linecap="round"/>
        </g>
        <path d="${контур}" fill="url(#${id}g)" opacity=".45" transform="translate(${60} ${46}) scale(.9 .55) translate(${-60} ${-46})"/>
      </g>
      ${(Р[ключ] || (() => ""))()}
      ${КОРОНОВАННЫЕ.has(ключ) ? "" : ЛИДЕРЫ.has(ключ) ? ЗВЕЗДА : ""}
      <g class="зз"><text x="92" y="30" font-size="13" font-weight="700">z</text><text class="з2" x="102" y="18" font-size="10" font-weight="700">z</text></g>
    </g>`.replaceAll("§", id);
  }

  function цвета(ключ) {
    const [h] = ГЕРОИ[ключ] || ПО_УМОЛЧАНИЮ;
    return `--c1:hsl(${h} 72% 52%);--cl:hsl(${h} 90% 76%);--cd:hsl(${h} 62% 22%);--cg:hsl(${h} 100% 64%);`;
  }

  window.ПЕРСОНАЖИ = ГЕРОИ;

  // ---- Юридическое управление ----
  const весы = () => `<g class="проп плав"><path d="M2 78V116M-10 116H14M-12 84H16" stroke="var(--cl)" stroke-width="2" fill="none" stroke-linecap="round"/><path d="M-12 84L-18 100H-6ZM16 84L10 100H22Z" fill="var(--cd)" stroke="var(--cl)" stroke-width="1.2"/></g>`;
  const печать = (x, y) => `<g transform="translate(${x} ${y})"><circle r="10" fill="#c43c4f" stroke="#7d1f2c" stroke-width="1.4"/><circle r="5.4" fill="none" stroke="#ffb3be" stroke-width="1"/></g>`;
  const щит = (x, y) => `<path d="M${x} ${y}L${x + 18} ${y - 6}L${x + 36} ${y}V${y + 20}Q${x + 36} ${y + 34} ${x + 18} ${y + 40}Q${x} ${y + 34} ${x} ${y + 20}Z" fill="#0a1220" stroke="var(--cl)" stroke-width="1.6"/>`;
  Object.assign(Р, {
    юрист: () => КОРОНА + `<g class="проп плав">${весы()}</g><g class="проп плав п2">${книга(92, 80, "#8a1f3c")}</g>`,
    дог_ведущий: () => `<g class="проп плав">${документ(-14, 78, 4, "var(--cg)")}${печать(10, 112)}</g><g class="проп плав п2">${книга(92, 84, "#8a1f3c")}</g>`,
    дог_перевозки: () => `<g class="проп плав">${грузовик(-18, 92)}</g><g class="проп плав п2">${документ(92, 78, 3, "#ff9b3d")}${печать(112, 112)}</g>`,
    дог_аренда: () => `<g class="проп плав">${машинка(-16, 88)}<path d="M-16 112H10" stroke="var(--cl)" stroke-width="1.4"/></g><g class="проп плав п2">${документ(92, 80, 3, "var(--cg)")}<path d="M100 108H112" stroke="var(--cd)" stroke-width="1.6"/></g>`,
    прет_ведущий: () => `<g class="проп плав">${весы()}</g><g class="проп плав п2">${документ(92, 78, 4, "#ef4d4d")}</g>`,
    прет_дтп: () => `<g class="проп плав">${машинка(-18, 90)}<path d="M-4 84L2 76L8 84" stroke="#ff7a5b" stroke-width="2" fill="none"/></g><g class="проп плав п2">${щит(94, 80)}</g>`,
    прет_дебиторка: () => `<g class="проп плав">${монеты(-6, 114, 3)}</g><g class="проп плав п2">${документ(92, 78, 3, "#ef4d4d")}<text x="104" y="112" text-anchor="middle" font-size="10" font-weight="800" fill="#ef4d4d">!</text></g>`,
    закуп_юрист: () => `<g class="проп плав">${документ(-14, 80, 4, "var(--cg)")}${ценник(10, 116)}</g><g class="проп плав п2">${печать(104, 94)}</g>`,
    регуляция: () => `<g class="проп плав">${щит(-18, 80)}</g><g class="проп плав п2">${документ(92, 80, 4, "var(--cg)")}${печать(112, 112)}</g>`,
    дог_архив: () => `<g class="проп плав">${книга(-16, 82, "#6a2740")}</g><g class="проп плав п2">${документ(92, 76, 5, "var(--cg)")}${документ(100, 86, 2, "var(--cd)")}</g>`,
  });

  window.персонаж = function (ключ) {
    const id = `п${++счётчик}`;
    const с = document.createElementNS(NS, "svg");
    с.setAttribute("viewBox", "-12 -10 144 156");
    с.setAttribute("class", `персонаж п-${ключ}`);
    с.setAttribute("aria-hidden", "true");
    с.setAttribute("style", цвета(ключ));
    с.innerHTML = разметка(ключ, id);
    return с;
  };
  window.ЦВЕТ_ПЕРСОНАЖА = (ключ) => `hsl(${(ГЕРОИ[ключ] || ПО_УМОЛЧАНИЮ)[0]} 90% 62%)`;
}
