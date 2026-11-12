// Мелкие эффекты панели «Граф»: заливка дорожки ползунков и волна на кнопках.
(function () {
  "use strict";
  function залить(вход) {
    const мин = parseFloat(вход.min) || 0, макс = parseFloat(вход.max) || 1;
    const доля = Math.max(0, Math.min(1, (parseFloat(вход.value) - мин) / (макс - мин)));
    вход.style.setProperty("--зап", (доля * 100).toFixed(1) + "%");
  }
  function подключить() {
    const панель = document.getElementById("мозги-панель");
    if (!панель) return;
    const все = () => панель.querySelectorAll(".ползунок input[type=range]");
    for (const вход of все()) {
      залить(вход);
      вход.addEventListener("input", () => залить(вход));
      // значение меняет brain.js без события — следим за подписью рядом
      const вывод = вход.parentElement.querySelector("output");
      if (вывод) new MutationObserver(() => залить(вход)).observe(вывод, { childList: true, characterData: true, subtree: true });
    }
    панель.addEventListener("pointerdown", (с) => {
      const к = с.target.closest(".кнопка, .кнопки-выбора button");
      if (!к || matchMedia("(prefers-reduced-motion: reduce)").matches) return;
      const р = к.getBoundingClientRect();
      к.style.setProperty("--вх", (с.clientX - р.left) + "px");
      к.style.setProperty("--вy", (с.clientY - р.top) + "px");
      к.classList.remove("волна"); void к.offsetWidth; к.classList.add("волна");
    });
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", подключить);
  else подключить();
})();
