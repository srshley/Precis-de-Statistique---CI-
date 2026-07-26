const datasetInput = document.querySelector("#dataset");
const histogram = document.querySelector("#histogramBars");
const feedback = document.querySelector("#feedback");

const output = {
  count: document.querySelector("#count"),
  mean: document.querySelector("#mean"),
  median: document.querySelector("#median"),
  mode: document.querySelector("#mode"),
  range: document.querySelector("#range"),
};

const samples = {
  notes: "8, 10, 11, 12, 12, 13, 14, 15, 15, 16, 18",
  sales: "24, 31, 28, 45, 45, 52, 39, 41, 56, 47, 45, 60",
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

function getMedian(values) {
  const mid = Math.floor(values.length / 2);
  if (values.length % 2 === 1) return values[mid];
  return (values[mid - 1] + values[mid]) / 2;
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
  const range = values[values.length - 1] - values[0];

  output.count.textContent = values.length;
  output.mean.textContent = formatNumber(mean);
  output.median.textContent = formatNumber(getMedian(values));
  output.mode.textContent = getMode(values);
  output.range.textContent = formatNumber(range);

  const interpretation =
    range > mean
      ? "La serie semble assez dispersee : comparez la moyenne avec la mediane."
      : "La serie est relativement groupee : moyenne et mediane peuvent bien resumer l'ensemble.";

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

document.querySelector("#clearData").addEventListener("click", () => {
  datasetInput.value = "";
  updateStats();
  datasetInput.focus();
});

datasetInput.addEventListener("input", updateStats);

document.querySelector("#quizForm").addEventListener("submit", (event) => {
  event.preventDefault();
  const formData = new FormData(event.currentTarget);
  const score = ["q1", "q2", "q3"].reduce((sum, key) => sum + Number(formData.get(key) || 0), 0);
  const result = document.querySelector("#quizResult");

  if (score === 3) {
    result.textContent = "3/3 : tres bien, les bases sont solides.";
  } else if (score === 2) {
    result.textContent = "2/3 : bon debut, relisez la notion manquee.";
  } else {
    result.textContent = `${score}/3 : reprenez les definitions, puis recommencez.`;
  }
});

updateStats();
