"use strict";

// Имя и версия из настроек сервера
fetch("/api/status")
  .then((ответ) => ответ.json())
  .then((с) => {
    document.title = с.имя;
    document.getElementById("имя").textContent = с.имя;
    document.getElementById("подвал").textContent = `${с.имя} · версия ${с.версия}`;
  })
  .catch(() => {
    document.getElementById("подвал").textContent = "Нет связи с сервером";
  });
