const datasetInput = document.querySelector("#dataset");
const histogram = document.querySelector("#histogramBars");
const feedback = document.querySelector("#feedback");
const progress = document.querySelector("#readingProgress");
const searchInput = document.querySelector("#courseSearch");
const searchStatus = document.querySelector("#searchStatus");
const backToTop = document.querySelector(".back-to-top");

const output = {
  count: document.querySelector("#count"),
  mean: document.querySelector("#mean"),
  median: document.querySelector("#median"),
  mode: document.querySelector("#mode"),
  range: document.querySelector("#range"),
  q1: document.querySelector("#q1"),
  q3: document.querySelector("#q3"),
  stddev: document.querySelector("#stddev"),
};

const samples = {
  notes: "8, 10, 11, 12, 12, 13, 14, 15, 15, 16, 18",
  sales: "24, 31, 28, 45, 45, 52, 39, 41, 56, 47, 45, 60",
  income: "1200, 1300, 1350, 1500, 1600, 1700, 1850, 2200, 2800, 4500",
};

function parseValues(text) {
  return text
    .split(/[\s,;]+/)
    .map((value) => Number(value.replace(",", ".")))
    .filter((value) => Number.isFinite(value));
}

function formatNumber(value) {
  if (!Number.isFinite(value)) return "-";
  return Number.isInteger(value) ? String(value) : value.toFixed(2).replace(".", ",");
}

function quantile(sorted, probability) {
  if (sorted.length === 0) return NaN;
  const position = (sorted.length - 1) * probability;
  const base = Math.floor(position);
  const rest = position - base;
  if (sorted[base + 1] === undefined) return sorted[base];
  return sorted[base] + rest * (sorted[base + 1] - sorted[base]);
}

function getMode(values) {
  const frequencies = new Map();
  values.forEach((value) => frequencies.set(value, (frequencies.get(value) || 0) + 1));
  const maxFrequency = Math.max(...frequencies.values());
  if (maxFrequency === 1) return "Aucun";
  return [...frequencies.entries()]
    .filter(([, frequency]) => frequency === maxFrequency)
    .map(([value]) => formatNumber(value))
    .join(", ");
}

function renderHistogram(values) {
  histogram.innerHTML = "";
  if (values.length === 0) {
    histogram.style.gridTemplateColumns = "1fr";
    histogram.innerHTML = '<div class="empty-state">Ajoutez des donnees pour voir le graphique.</div>';
    return;
  }

  const frequencies = new Map();
  values.forEach((value) => frequencies.set(value, (frequencies.get(value) || 0) + 1));
  const entries = [...frequencies.entries()].sort((a, b) => a[0] - b[0]);
  const maxFrequency = Math.max(...entries.map(([, frequency]) => frequency));

  histogram.style.gridTemplateColumns = `repeat(${entries.length}, minmax(0, 1fr))`;
  entries.forEach(([value, frequency]) => {
    const bar = document.createElement("div");
    bar.className = "histogram-bar";
    bar.style.setProperty("--height", `${Math.max(18, (frequency / maxFrequency) * 190)}px`);
    bar.title = `${formatNumber(value)} : ${frequency}`;
    bar.textContent = formatNumber(value);
    histogram.appendChild(bar);
  });
}

function updateStats() {
  const values = parseValues(datasetInput.value).sort((a, b) => a - b);
  if (values.length === 0) {
    Object.values(output).forEach((element) => {
      element.textContent = "-";
    });
    feedback.textContent = "Entrez au moins une valeur numerique.";
    renderHistogram([]);
    return;
  }

  const total = values.reduce((sum, value) => sum + value, 0);
  const mean = total / values.length;
  const variance = values.reduce((sum, value) => sum + (value - mean) ** 2, 0) / values.length;
  const stddev = Math.sqrt(variance);
  const range = values[values.length - 1] - values[0];

  output.count.textContent = values.length;
  output.mean.textContent = formatNumber(mean);
  output.median.textContent = formatNumber(quantile(values, 0.5));
  output.mode.textContent = getMode(values);
  output.range.textContent = formatNumber(range);
  output.q1.textContent = formatNumber(quantile(values, 0.25));
  output.q3.textContent = formatNumber(quantile(values, 0.75));
  output.stddev.textContent = formatNumber(stddev);

  const median = quantile(values, 0.5);
  const interpretation =
    Math.abs(mean - median) > stddev / 2
      ? "La moyenne et la mediane sont eloignees : verifiez la presence de valeurs extremes."
      : "La moyenne et la mediane sont proches : la serie semble assez equilibree.";

  feedback.textContent = interpretation;
  renderHistogram(values);
}

document.querySelector("#sampleA").addEventListener("click", () => {
  datasetInput.value = samples.notes;
  updateStats();
});
document.querySelector("#sampleB").addEventListener("click", () => {
  datasetInput.value = samples.sales;
  updateStats();
});
document.querySelector("#sampleC").addEventListener("click", () => {
  datasetInput.value = samples.income;
  updateStats();
});
document.querySelector("#clearData").addEventListener("click", () => {
  datasetInput.value = "";
  updateStats();
  datasetInput.focus();
});
datasetInput.addEventListener("input", updateStats);

document.addEventListener("click", (event) => {
  const button = event.target.closest("[data-toggle]");
  if (!button) return;
  const answer = document.getElementById(button.getAttribute("data-toggle"));
  if (!answer) return;
  const isVisible = answer.classList.toggle("show");
  button.textContent = isVisible ? "Cacher la correction" : "Voir la correction";
  button.setAttribute("aria-expanded", String(isVisible));
});

function normalize(value) {
  return value
    .toLowerCase()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "");
}

function filterCourse() {
  const query = normalize(searchInput.value.trim());
  const panels = [...document.querySelectorAll("[data-chapter-panel]")];
  if (!query) {
    panels.forEach((panel) => {
      panel.hidden = false;
      panel.querySelectorAll(".content-section").forEach((section) => {
        section.hidden = false;
      });
    });
    searchStatus.textContent = "";
    return;
  }

  let visibleChapters = 0;
  let visibleSections = 0;
  panels.forEach((panel) => {
    let chapterHasMatch = false;
    panel.querySelectorAll(".content-section").forEach((section) => {
      const match = normalize(section.textContent).includes(query);
      section.hidden = !match;
      if (match) {
        chapterHasMatch = true;
        visibleSections += 1;
      }
    });
    panel.hidden = !chapterHasMatch;
    if (chapterHasMatch) visibleChapters += 1;
  });
  searchStatus.textContent =
    visibleSections === 0
      ? "Aucun resultat trouve."
      : `${visibleSections} section(s) trouvee(s) dans ${visibleChapters} chapitre(s).`;
}

searchInput.addEventListener("input", filterCourse);

function updateProgress() {
  const scrollTop = document.documentElement.scrollTop || document.body.scrollTop;
  const maxScroll = document.documentElement.scrollHeight - document.documentElement.clientHeight;
  const percent = maxScroll > 0 ? (scrollTop / maxScroll) * 100 : 0;
  progress.style.width = `${percent}%`;
  backToTop.classList.toggle("show", scrollTop > 600);
}

window.addEventListener("scroll", updateProgress, { passive: true });
backToTop.addEventListener("click", () => window.scrollTo({ top: 0, behavior: "smooth" }));

const tocLinks = [...document.querySelectorAll(".toc a")];
const observer = new IntersectionObserver(
  (entries) => {
    const visible = entries
      .filter((entry) => entry.isIntersecting)
      .sort((a, b) => b.intersectionRatio - a.intersectionRatio)[0];
    if (!visible) return;
    tocLinks.forEach((link) => {
      link.classList.toggle("active", link.getAttribute("href") === `#${visible.target.id}`);
    });
  },
  { rootMargin: "-20% 0px -70% 0px", threshold: [0.05, 0.2, 0.5] }
);

document.querySelectorAll(".content-section[id]").forEach((section) => observer.observe(section));

/* ---- Bivariate calculator ---- */
const bivX = document.querySelector("#bivX");
const bivY = document.querySelector("#bivY");
const bivOut = {
  cov: document.querySelector("#bivCov"),
  r: document.querySelector("#bivR"),
  r2: document.querySelector("#bivR2"),
  a: document.querySelector("#bivA"),
  b: document.querySelector("#bivB"),
  n: document.querySelector("#bivN"),
};
const bivEq = document.querySelector("#bivEquation");
const bivFb = document.querySelector("#bivFeedback");

function updateBivariate() {
  const x = parseValues(bivX.value);
  const y = parseValues(bivY.value);

  if (x.length < 2 || y.length < 2 || x.length !== y.length) {
    Object.values(bivOut).forEach((el) => { el.textContent = "-"; });
    bivEq.innerHTML = "<span style='color:var(--muted)'>Entrez deux series de meme longueur (au moins 2 valeurs).</span>";
    bivFb.textContent = "";
    return;
  }

  const n = x.length;
  const mx = x.reduce((s, v) => s + v, 0) / n;
  const my = y.reduce((s, v) => s + v, 0) / n;
  const varX = x.reduce((s, v) => s + (v - mx) ** 2, 0) / n;
  const varY = y.reduce((s, v) => s + (v - my) ** 2, 0) / n;
  const cov = x.reduce((s, v, i) => s + (v - mx) * (y[i] - my), 0) / n;
  const sdX = Math.sqrt(varX);
  const sdY = Math.sqrt(varY);
  const r = sdX > 0 && sdY > 0 ? cov / (sdX * sdY) : 0;
  const r2 = r * r;
  const a = varX > 0 ? cov / varX : 0;
  const b = my - a * mx;

  bivOut.n.textContent = n;
  bivOut.cov.textContent = formatNumber(cov);
  bivOut.r.textContent = formatNumber(r);
  bivOut.r2.textContent = formatNumber(r2);
  bivOut.a.textContent = formatNumber(a);
  bivOut.b.textContent = formatNumber(b);

  const rAbs = Math.abs(r);
  let force = rAbs > 0.8 ? "très forte" : rAbs > 0.5 ? "modérée" : rAbs > 0.3 ? "faible" : "très faible";
  let sens = r > 0 ? "positive" : "négative";

  bivEq.innerHTML = `
    <div style="margin-bottom:10px;"><strong>Y = ${formatNumber(a)} · X + ${formatNumber(b)}</strong></div>
    <div>Corrélation ${sens} ${force} (r = ${formatNumber(r)})</div>
    <div>R² = ${formatNumber(r2)} → ${(r2 * 100).toFixed(0)} % de la variance de Y expliquée par X</div>
    ${rAbs > 0.7 ? "<div style='color:var(--green);margin-top:6px;'>✓ La liaison linéaire est suffisamment forte pour une prévision.</div>" : "<div style='color:var(--coral);margin-top:6px;'>⚠ La liaison linéaire est faible : la prédiction sera peu fiable.</div>"}
  `;

  bivFb.textContent =
    n < 5
      ? "Attention : avec moins de 5 points, la regression est peu fiable."
      : rAbs > 0.9
        ? "Relation quasi parfaite : les points sont presque alignés."
        : rAbs > 0.7
          ? "Bonne relation linéaire : le modèle est utile pour la prediction."
          : rAbs > 0.5
            ? "Relation modérée : d'autres facteurs influencent Y."
            : "Relation linéaire faible : cherchez d'autres variables explicatives.";
}

bivX.addEventListener("input", updateBivariate);
bivY.addEventListener("input", updateBivariate);

document.querySelector("#bivSampleA").addEventListener("click", () => {
  bivX.value = "20, 25, 30, 35, 40, 45, 50, 55, 60, 65";
  bivY.value = "115, 118, 120, 125, 130, 135, 140, 145, 150, 155";
  updateBivariate();
});
document.querySelector("#bivSampleB").addEventListener("click", () => {
  bivX.value = "10, 15, 20, 25, 30, 35, 40, 45, 50, 55, 60, 65";
  bivY.value = "78, 92, 108, 124, 140, 158, 172, 190, 205, 222, 238, 252";
  updateBivariate();
});
document.querySelector("#bivClear").addEventListener("click", () => {
  bivX.value = "";
  bivY.value = "";
  updateBivariate();
  bivX.focus();
});

updateBivariate();

updateStats();
updateProgress();
