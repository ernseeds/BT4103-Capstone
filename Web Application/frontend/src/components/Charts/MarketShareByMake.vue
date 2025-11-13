<template>
  <a-card
    title="Market Share by Make"
    :bordered="false"
    class="h-full shadow-md rounded-lg"
  >
    <!-- Top-right: download icon -->
    <template #extra>
      <button
        class="icon-btn"
        title="Download CSV (all makes for selected year)"
        aria-label="Download CSV"
        @click="downloadCSV"
      >
        <!-- Inline SVG icon (fills with current text color) -->
        <svg class="icon-svg" viewBox="0 0 24 24" aria-hidden="true">
          <path
            d="M12 3a1 1 0 0 1 1 1v8.586l2.293-2.293a1 1 0 1 1 1.414 1.414l-4.001 4a1 1 0 0 1-1.412 0l-4.001-4a1 1 0 1 1 1.414-1.414L11 12.586V4a1 1 0 0 1 1-1zM5 19a1 1 0 1 0 0 2h14a1 1 0 1 0 0-2H5z"
            fill="currentColor"
            fill-rule="evenodd"
            clip-rule="evenodd"
          />
        </svg>
      </button>
    </template>

    <!-- 🟢 Filters BELOW the title -->
    <div class="filter-container">
      <div class="filter-group">
        <span class="label">Year:</span>
        <select v-model.number="selectedYear" @change="fetchData" class="filter-select">
          <option v-for="y in availableYears" :key="y" :value="y">{{ y }}</option>
        </select>
      </div>

      <div class="filter-group">
        <span class="label">Top:</span>
        <select v-model.number="topN" @change="fetchData" class="filter-select">
          <option v-for="n in [5,10,15,20]" :key="n" :value="n">{{ n }} makes</option>
        </select>
      </div>
    </div>

    <!-- 🥧 Pie Chart -->
    <div class="chart-container" style="height:370px;">
      <canvas ref="marketShareChart"></canvas>
    </div>
  </a-card>
</template>

<script>
import { Chart, registerables } from "chart.js";
import axios from "axios";

Chart.register(...registerables);

export default {
  name: "MarketShareByMake",
  data() {
    return {
      chart: null,
      datasetId: "d_20d3fc7f08caa581c5586df51a8993c5",
      availableYears: [],
      selectedYear: null,
      topN: 5,
      yearAggAllMakes: [], // [{ make, count, pct }]
    };
  },
  methods: {
    async fetchData() {
      try {
        const url = `https://data.gov.sg/api/action/datastore_search?resource_id=${this.datasetId}&limit=50000`;
        const response = await axios.get(url);
        const records = response.data.result.records;

        const valid = records.filter(
          (r) => r.year && r.make && r.number && !isNaN(r.number)
        );

        const data = valid.map((r) => ({
          year: parseInt(r.year),
          make: r.make.trim(),
          number: parseInt(r.number),
        }));

        // Years
        this.availableYears = [...new Set(data.map((d) => d.year))].sort((a, b) => a - b);
        if (!this.selectedYear) this.selectedYear = Math.max(...this.availableYears);

        // Aggregate for selected year
        const yearData = data.filter((d) => d.year === this.selectedYear);
        const totals = {};
        yearData.forEach((d) => {
          totals[d.make] = (totals[d.make] || 0) + d.number;
        });

        const totalAll = Object.values(totals).reduce((s, v) => s + v, 0);
        this.yearAggAllMakes = Object.entries(totals)
          .map(([make, count]) => ({
            make,
            count,
            pct: totalAll ? (count / totalAll) * 100 : 0,
          }))
          .sort((a, b) => b.count - a.count);

        // Top N + Others for the pie
        const sortedAll = this.yearAggAllMakes.map(({ make, count }) => [make, count]);
        const top = sortedAll.slice(0, this.topN);
        const others = sortedAll.slice(this.topN);
        const othersTotal = others.reduce((sum, [, v]) => sum + v, 0);

        const labels = [...top.map(([make]) => make), "Others"];
        const values = [...top.map(([, val]) => val), othersTotal];

        await this.$nextTick();
        this.renderChart(labels, values);
      } catch (err) {
        console.error("Error fetching market share data:", err);
      } finally {
        this.$emit("loaded", "MarketShareMake");
      }
    },

    renderChart(labels, values) {
      if (this.chart) this.chart.destroy();
      const ctx = this.$refs.marketShareChart.getContext("2d");

      this.chart = new Chart(ctx, {
        type: "pie",
        data: {
          labels,
          datasets: [
            {
              data: values,
              backgroundColor: this.generateColors(labels.length),
              borderWidth: 1,
            },
          ],
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          layout: { padding: { top: 0, right: 0, bottom: 0, left: 0 } },
          plugins: {
            legend: {
              position: "bottom",
              padding: 12, // gap between pie & legend
              labels: {
                boxWidth: 12,
                boxHeight: 12,
                font: { size: 11 },
                padding: 6, // compact legend rows
              },
            },
            tooltip: {
              callbacks: {
                label: (context) => {
                  const make = context.label;
                  const value = context.raw;
                  const total = context.chart._metasets[0].total;
                  const pct = ((value / total) * 100).toFixed(2);
                  return `${make}: ${pct}% (${value.toLocaleString()} cars)`;
                },
              },
            },
            title: { display: false },
          },
        },
      });
    },

    generateColors(n) {
      const palette = [
        "#1abc9c", "#3498db", "#9b59b6", "#f39c12", "#e74c3c",
        "#2ecc71", "#16a085", "#2980b9", "#8e44ad", "#d35400",
        "#27ae60", "#c0392b", "#7f8c8d", "#34495e", "#e67e22",
        "#f1c40f", "#ff7675", "#55efc4", "#74b9ff", "#a29bfe",
      ];
      return Array.from({ length: n }, (_, i) => palette[i % palette.length]);
    },

    downloadCSV() {
      if (!this.yearAggAllMakes.length) {
        this.fetchData().then(() => this.downloadCSV());
        return;
      }
      const header = ["Year", "Make", "Number of Cars", "Market Share (%)"];
      const rows = this.yearAggAllMakes.map(({ make, count, pct }) => [
        this.selectedYear,
        make,
        count,
        pct.toFixed(2),
      ]);
      const csv = [header, ...rows]
        .map((r) => r.map((c) => `"${String(c).replace(/"/g, '""')}"`).join(","))
        .join("\n");
      const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `market_share_by_make_${this.selectedYear}.csv`;
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
/* icon button styles */
.icon-btn {
  background: transparent;
  border: none;
  outline: none;
  padding: 2px 6px;
  line-height: 1;
  cursor: pointer;
  border-radius: 6px;
  color: #595959;            /* visible on light header */
  display: inline-flex;
  align-items: center;
  justify-content: center;
}
.icon-btn:hover {
  background: #f5f5f5;
}
.icon-svg {
  width: 18px;
  height: 18px;
  display: block;
  fill: currentColor;
}

/* filters */
.filter-container {
  display: flex;
  align-items: center;
  gap: 1rem;
  margin-bottom: 1rem;
  flex-wrap: wrap;
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

:deep(.ant-card-body) {
  padding-bottom: 12px;
}

/* Force filters into card body */
:deep(.ant-card-body) {
  display: flex;
  flex-direction: column;
  position: relative;
  margin-left: 20px;
}

.filter-container {
  position: static !important;
  order: 1;
  width: 100% !important;
  z-index: 1 !important;
}

.chart-container {
  order: 2;
  position: static !important;
}
</style>