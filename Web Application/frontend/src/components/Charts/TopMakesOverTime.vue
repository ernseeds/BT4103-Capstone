<template>
  <a-card
    title="Top Car Makes Over Time"
    :bordered="false"
    class="h-full shadow-md rounded-lg"
  >
    <!-- 🟣 Top-right Filters + Download -->
    <template #extra>
      <div class="filter-top-right">
        <div class="filter-group">
          <span class="label">Show last:</span>
          <select v-model.number="numYears" @change="fetchData" class="filter-select">
            <option v-for="n in [5,10,15,20]" :key="n" :value="n">{{ n }} years</option>
          </select>
        </div>

        <div class="filter-group">
          <span class="label">Top:</span>
          <select v-model.number="topN" @change="fetchData" class="filter-select">
            <option v-for="n in [5,10,15,20]" :key="n" :value="n">{{ n }} makes</option>
          </select>
        </div>

        <!-- Download visible data (inline SVG icon) -->
        <button
          class="icon-btn"
          title="Download current view as CSV"
          aria-label="Download current view as CSV"
          @click="downloadVisibleCSV"
        >
          <svg class="icon-svg" viewBox="0 0 24 24" aria-hidden="true">
            <path
              d="M12 3a1 1 0 0 1 1 1v8.586l2.293-2.293a1 1 0 1 1 1.414 1.414l-4.001 4a1 1 0 0 1-1.412 0l-4.001-4a1 1 0 1 1 1.414-1.414L11 12.586V4a1 1 0 0 1 1-1zM5 19a1 1 0 1 0 0 2h14a1 1 0 1 0 0-2H5z"
              fill="currentColor"
              fill-rule="evenodd"
              clip-rule="evenodd"
            />
          </svg>
        </button>
      </div>
    </template>

    <div style="height:450px;">
      <canvas ref="topMakesChart"></canvas>
    </div>
  </a-card>
</template>

<script>
import { Chart, registerables } from "chart.js";
import axios from "axios";

Chart.register(...registerables);

export default {
  name: "TopMakesOverTime",
  data() {
    return {
      chart: null,
      datasetId: "d_20d3fc7f08caa581c5586df51a8993c5",
      numYears: 10,
      topN: 10,

      // state for download
      visibleYears: [],
      visibleMakes: [],
      visibleMatrix: [], // [{ make, [year]: value, ... }]
    };
  },
  methods: {
    async fetchData() {
      try {
        const url = `https://data.gov.sg/api/action/datastore_search?resource_id=${this.datasetId}&limit=50000`;
        const { data: resp } = await axios.get(url);
        const records = resp.result.records;

        // Clean numeric records
        const valid = records.filter(
          (r) => r.year && r.make && r.number && !isNaN(r.number)
        );

        const base = valid.map((r) => ({
          year: parseInt(r.year, 10),
          make: String(r.make || "").trim(),
          number: parseInt(r.number, 10),
        }));

        // Time window
        const maxYear = Math.max(...base.map((d) => d.year));
        const minYear = maxYear - this.numYears + 1;
        const filtered = base.filter((d) => d.year >= minYear);

        // Aggregate by (year, make)
        const grouped = {};
        for (const r of filtered) {
          const key = `${r.year}__${r.make}`;
          grouped[key] = (grouped[key] || 0) + r.number;
        }

        const aggregated = Object.entries(grouped).map(([key, number]) => {
          const [year, make] = key.split("__");
          return { year: parseInt(year, 10), make, number };
        });

        // Top N makes by total across the window
        const totalByMake = {};
        for (const r of aggregated) {
          totalByMake[r.make] = (totalByMake[r.make] || 0) + r.number;
        }
        const topMakes = Object.entries(totalByMake)
          .sort((a, b) => b[1] - a[1])
          .slice(0, this.topN)
          .map(([make]) => make);

        const topData = aggregated.filter((r) => topMakes.includes(r.make));

        // Years and datasets for chart
        const years = [...new Set(topData.map((r) => r.year))].sort((a, b) => a - b);
        const datasets = topMakes.map((make, idx) => {
          const color = this.getColor(idx);
          const points = years.map((y) => {
            const found = topData.find((r) => r.year === y && r.make === make);
            return found ? found.number : null;
          });
          return {
            label: make,
            data: points,
            borderColor: color,
            fill: false,
            tension: 0.3,
            pointRadius: 0,
            borderWidth: 2,
          };
        });

        // Prepare download state (matrix)
        const matrix = topMakes.map((mk, i) => {
          const row = { make: mk };
          years.forEach((y, j) => {
            const v = datasets[i].data[j];
            row[y] = Number.isFinite(v) ? v : "";
          });
          return row;
        });

        this.visibleYears = years;
        this.visibleMakes = topMakes;
        this.visibleMatrix = matrix;

        await this.$nextTick();
        this.renderChart(years, datasets);
      } catch (err) {
        console.error("Error fetching car population data:", err);
      } finally {
        this.$emit("loaded", "TopMakes");
      }
    },

    renderChart(years, datasets) {
      if (this.chart) this.chart.destroy();
      const ctx = this.$refs.topMakesChart.getContext("2d");

      this.chart = new Chart(ctx, {
        type: "line",
        data: { labels: years, datasets },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: {
              position: "bottom",
              labels: {
                usePointStyle: true,
                pointStyle: "circle",
                boxWidth: 8,
                padding: 12,
                generateLabels(chart) {
                  const { data } = chart;
                  if (!data?.datasets) return [];
                  return data.datasets.map((ds, i) => ({
                    text: ds.label,
                    fillStyle: ds.borderColor,
                    strokeStyle: ds.borderColor,
                    lineWidth: 0, // solid dot
                    hidden: !chart.isDatasetVisible(i),
                    index: i,
                    datasetIndex: i,
                  }));
                },
              },
            },
            tooltip: {
              mode: "index",
              intersect: false,
              usePointStyle: true,
              callbacks: {
                labelColor: (context) => {
                  const c = context.dataset.borderColor || "#555";
                  return { borderColor: c, backgroundColor: c };
                },
                label: (context) =>
                  `${context.dataset.label}: ${Number(context.parsed.y).toLocaleString()}`,
              },
            },
          },
          interaction: { mode: "nearest", axis: "x", intersect: false },
          scales: {
            x: {
              title: { display: true, text: "Year" },
              grid: { display: false },
            },
            y: {
              title: { display: true, text: "Number of Cars" },
              beginAtZero: true,
              grid: { color: "rgba(0,0,0,0.05)" },
              ticks: { callback: (v) => Number(v).toLocaleString() },
            },
          },
        },
      });
    },

    getColor(i) {
      const colors = [
        "#1abc9c", "#3498db", "#9b59b6", "#e67e22", "#e74c3c",
        "#16a085", "#2980b9", "#8e44ad", "#2ecc71", "#f39c12",
        "#d35400", "#27ae60", "#c0392b", "#7f8c8d", "#34495e",
      ];
      return colors[i % colors.length];
    },

    downloadVisibleCSV() {
      // Build CSV with columns: Make, <year1>, <year2>, ...
      if (!this.visibleMatrix.length) return;

      const header = ["Make", ...this.visibleYears];
      const rows = this.visibleMatrix.map((row) => {
        const cells = [row.make, ...this.visibleYears.map((y) => row[y] ?? "")];
        return cells.map((c) => `"${String(c).replace(/"/g, '""')}"`).join(",");
      });

      const csv = [header.join(","), ...rows].join("\n");
      const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      const minY = this.visibleYears[0];
      const maxY = this.visibleYears[this.visibleYears.length - 1];
      a.href = url;
      a.download = `top_makes_over_time_${minY}-${maxY}_top${this.topN}.csv`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    },
  },
  mounted() {
    this.fetchData();
  },
};
</script>

<style scoped>
.filter-top-right {
  display: flex;
  align-items: center;
  gap: 1rem;
}
.filter-group {
  display: flex;
  align-items: center;
  gap: 0.3rem;
}
.label {
  font-size: 0.85rem;
}
.filter-select {
  min-width: 90px;
  padding: 0.15rem 0.3rem;
  font-size: 0.8rem;
  border-radius: 6px;
  border: 1px solid #d9d9d9;
}

/* icon button (same style used elsewhere) */
.icon-btn {
  background: transparent;
  border: none;
  outline: none;
  padding: 2px 6px;
  line-height: 1;
  cursor: pointer;
  border-radius: 6px;
  color: #595959;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}
.icon-btn:hover { background: #f5f5f5; }
.icon-svg { width: 18px; height: 18px; display: block; fill: currentColor; }
</style>
