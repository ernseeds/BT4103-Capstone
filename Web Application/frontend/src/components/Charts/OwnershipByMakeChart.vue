<template>
  <a-card title="Car Ownership Transfers by Make" :bordered="false">
    <template #extra>
      <div class="top-right-controls">
        <label class="checkbox-label">
          <input type="checkbox" v-model="showPercentage" @change="renderChart" />
          % Share
        </label>
        
        <span class="label">Top:</span>
        <select v-model.number="topN" @change="renderChart" class="filter-select">
          <option :value="5">5 makes</option>
          <option :value="10">10 makes</option>
          <option :value="20">20 makes</option>
          <option :value="makes.length">All</option>
        </select>
        
        <button class="icon-btn" @click="downloadVisibleCSV" title="Download CSV">
          <svg class="icon-svg" viewBox="0 0 24 24">
            <path d="M12 3a1 1 0 0 1 1 1v8.586l2.293-2.293a1 1 0 1 1 1.414 1.414l-4.001 4a1 1 0 0 1-1.412 0l-4.001-4a1 1 0 1 1 1.414-1.414L11 12.586V4a1 1 0 0 1 1-1zM5 19a1 1 0 1 0 0 2h14a1 1 0 1 0 0-2H5z" fill="currentColor"/>
          </svg>
        </button>
      </div>
    </template>
    
    <div style="height:400px;">
      <canvas ref="ownershipChart"></canvas>
    </div>
  </a-card>
</template>

<script>
import { Chart, registerables } from "chart.js";
import axios from "axios";
Chart.register(...registerables);

export default {
  name: "OwnershipByMakeChart",
  data() {
    return {
      chart: null,
      datasetId: "d_4974c1fb1ab0299977a5f6185f911963",
      labels: [],
      makes: [],
      totals: [],
      absoluteDatasets: [],
      percentDatasets: [],
      showPercentage: false,
      topN: 5,
    };
  },
  methods: {
    async fetchData() {
      try {
        const url =
          "https://data.gov.sg/api/action/datastore_search?resource_id=" +
          this.datasetId +
          "&limit=5000";
        const response = await axios.get(url);
        const records = response.data.result.records;

        // Group by year and make
        const grouped = {};
        records.forEach((r) => {
          const year = r.year;
          const make = r.make;
          const count = parseInt(r.number || 0);
          if (!grouped[year]) grouped[year] = {};
          if (!grouped[year][make]) grouped[year][make] = 0;
          grouped[year][make] += count;
        });

        this.labels = Object.keys(grouped).sort();

        // Totals per year
        this.totals = this.labels.map(
          (year) =>
            Object.values(grouped[year]).reduce((a, b) => a + (b || 0), 0) || 0
        );

        // Aggregate total per make for ranking
        const makeTotals = {};
        records.forEach((r) => {
          const make = r.make;
          const count = parseInt(r.number || 0);
          makeTotals[make] = (makeTotals[make] || 0) + count;
        });

        this.makes = Object.keys(makeTotals).sort(
          (a, b) => makeTotals[b] - makeTotals[a]
        );

        // Build datasets
        this.absoluteDatasets = this.makes.map((make, idx) => ({
          label: make,
          data: this.labels.map((year) => grouped[year][make] || 0),
          backgroundColor: this.getColor(idx),
          stack: "stack1",
        }));

        this.percentDatasets = this.makes.map((make, idx) => ({
          label: make,
          data: this.labels.map((year, i) => {
            const total = this.totals[i];
            const value = grouped[year][make] || 0;
            return total > 0 ? ((value / total) * 100).toFixed(1) : 0;
          }),
          backgroundColor: this.getColor(idx),
          stack: "stack1",
        }));

        this.renderChart();
      } catch (err) {
        console.error("Error fetching ownership data:", err);
      } finally {
        this.$emit("loaded", "OwnershipMake");
      }
    },

    renderChart() {
      if (this.chart) this.chart.destroy();
      const ctx = this.$refs.ownershipChart.getContext("2d");
      const datasets = (this.showPercentage
        ? this.percentDatasets
        : this.absoluteDatasets
      ).slice(0, this.topN);

      this.chart = new Chart(ctx, {
        type: "bar",
        data: { labels: this.labels, datasets },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          interaction: { mode: "index", intersect: false },
          plugins: {
            legend: {
              position: "bottom",
              labels: { usePointStyle: true, pointStyle: "circle" },
            },
            tooltip: {
              callbacks: {
                label: (context) => {
                  const value = context.raw;
                  const yearIdx = context.dataIndex;
                  if (this.showPercentage) {
                    return `${context.dataset.label}: ${value}%`;
                  } else {
                    const total = this.totals[yearIdx];
                    const pct =
                      total > 0 ? ((value / total) * 100).toFixed(1) : 0;
                    return `${context.dataset.label}: ${value.toLocaleString()} (${pct}%)`;
                  }
                },
                afterBody: (tooltipItems) => {
                  if (!this.showPercentage) {
                    const yearIdx = tooltipItems[0].dataIndex;
                    const total = this.totals[yearIdx];
                    return `Total: ${total.toLocaleString()}`;
                  }
                  return "";
                },
              },
            },
          },
          scales: {
            x: { title: { display: true, text: "Year" }, stacked: true },
            y: {
              title: {
                display: true,
                text: this.showPercentage
                  ? "Share of Transfers (%)"
                  : "No. of Transfers",
              },
              stacked: true,
              beginAtZero: true,
              max: this.showPercentage ? 100 : undefined,
            },
          },
        },
      });
    },

    getColor(idx) {
      const colors = [
        "#3498db", "#9b59b6", "#1abc9c", "#f39c12", "#e74c3c",
        "#2ecc71", "#16a085", "#2980b9", "#8e44ad", "#d35400",
        "#27ae60", "#c0392b", "#7f8c8d", "#34495e", "#e67e22",
        "#f1c40f", "#55efc4", "#74b9ff", "#a29bfe",
      ];
      return colors[idx % colors.length];
    },

    // ⬇️ CSV Export of visible data
    downloadVisibleCSV() {
      const mode = this.showPercentage ? "Percentage Share" : "Absolute";
      const labels = this.labels;
      const datasets = (this.showPercentage
        ? this.percentDatasets
        : this.absoluteDatasets
      ).slice(0, this.topN);

      if (!datasets.length) return;

      const header = ["Year", ...datasets.map((d) => d.label)];
      const rows = labels.map((year, i) => {
        const row = [year, ...datasets.map((d) => d.data[i])];
        return row.map((c) => `"${String(c).replace(/"/g, '""')}"`).join(",");
      });
      const csv = [header.join(","), ...rows].join("\n");

      const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `ownership_transfers_${mode.toLowerCase()}_top${this.topN}.csv`;
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
.top-right-controls {
  display: flex;
  align-items: center;
  gap: 8px;
}

.checkbox-label {
  display: flex;
  align-items: center;
  gap: 0.3rem;
  font-size: 0.85rem;
}

.label {
  font-size: 0.85rem;
}

.filter-select {
  min-width: 70px;
  padding: 0.15rem 0.3rem;
  font-size: 0.8rem;
  border-radius: 4px;
  border: 1px solid #d9d9d9;
}

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

</style>