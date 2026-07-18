// Dark/light mode toggle. Note: per artifact rules we avoid localStorage in
// artifacts, but this is a real Flask app served from your own server, so
// localStorage is perfectly fine here and persists the choice across visits.
(function () {
  const root = document.documentElement;
  const toggleBtn = document.getElementById("themeToggle");
  const stored = window.localStorage ? localStorage.getItem("theme") : null;
  if (stored) root.setAttribute("data-bs-theme", stored);

  function icon() {
    if (!window.feather) return;
    const isDark = root.getAttribute("data-bs-theme") === "dark";
    toggleBtn.innerHTML = `<i data-feather="${isDark ? "sun" : "moon"}"></i>`;
    feather.replace();
  }

  if (toggleBtn) {
    icon();
    toggleBtn.addEventListener("click", () => {
      const next = root.getAttribute("data-bs-theme") === "dark" ? "light" : "dark";
      root.setAttribute("data-bs-theme", next);
      if (window.localStorage) localStorage.setItem("theme", next);
      icon();
    });
  }

  if (window.feather) feather.replace();
})();
