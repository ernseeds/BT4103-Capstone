<template>
  <a-card
    title="Distribution Pie Chart"
    :bordered="false"
    class="shadow-md rounded-lg h-full pie-card"
  >
    <template #extra>
      <div class="controls-row">
        <span class="ctrl-label">Group By:</span>
        <select
          v-model="selectedColumn"
          class="ctrl-select"
          @change="updateChart"
        >
          <option
            v-for="col in filterColumns"
            :key="col"
            :value="col"
          >
            {{ col }}
          </option>
        </select>

        <template v-if="selectedColumn === 'Brand'">
          <span class="ctrl-label">Top:</span>
          <input
            type="number"
            v-model.number="topNBrand"
            min="1"
            max="30"
            class="ctrl-input"
            @change="updateChart"
          />
        </template>
      </div>
    </template>

    <div class="chart-shell">
      <canvas ref="pieChart"></canvas>
    </div>
  </a-card>
</template>

<script>
import { Chart, ArcElement, Tooltip, Legend } from "chart.js";
import ChartDataLabels from "chartjs-plugin-datalabels";

Chart.register(ArcElement, Tooltip, Legend);

export default {
  name: "PieChart",
  props: {
    rows: {
      type: Array,
      default: () => [],
    },
  },
  data() {
    return {
      dataRows: [],
      selectedColumn: "Brand",
      topNBrand: 5,
      filterColumns: [
        "Brand",
        "Number_of_Previous_Owners",
        "Transmission",
        "Fuel_Type",
        "COE_Category",
        "COE_Cycles",
        "COE_Renewed",
        "Website",
      ],
      chartInstance: null,
    };
  },
  mounted() {
    this.dataRows = this.rows || [];
    this.updateChart();
  },
  watch: {
    rows: {
      handler(newVal) {
        this.dataRows = newVal || [];
        this.updateChart();
      },
      deep: true,
    },
    selectedColumn() {
      this.updateChart();
    },
  },
  methods: {
    palette(i) {
      const colors = [
        "#4e79a7","#f28e2b","#e15759","#76b7b2","#59a14f",
        "#edc948","#b07aa1","#ff9da7","#9c755f","#bab0ab",
        "#1f77b4","#ff7f0e","#2ca02c","#d62728","#9467bd",
        "#8c564b","#e377c2","#7f7f7f","#bcbd22","#17becf",
      ];
      return colors[i % colors.length];
    },
    updateChart() {
      const rows = this.dataRows;
      if (!rows || !rows.length) {
        if (this.chartInstance) {
          this.chartInstance.destroy();
          this.chartInstance = null;
        }
        return;
      }

      // count by selected column
      const counts = {};
      for (const row of rows) {
        let v = row[this.selectedColumn];
        if (v === undefined || v === null || v === "") v = "N/A";
        counts[v] = (counts[v] || 0) + 1;
      }

      let entries = Object.entries(counts).sort((a, b) => b[1] - a[1]);

      // top N for Brand
      if (this.selectedColumn === "Brand" && this.topNBrand < entries.length) {
        const top = entries.slice(0, this.topNBrand);
        const other = entries.slice(this.topNBrand).reduce((s, [, c]) => s + c, 0);
        entries = [...top, ["Other", other]];
      }

      const labels = entries.map(([k]) => k);
      const data = entries.map(([, v]) => v);

      if (this.chartInstance) this.chartInstance.destroy();

      const ctx = this.$refs.pieChart.getContext("2d");
      this.chartInstance = new Chart(ctx, {
        type: "pie",
        data: {
          labels,
          datasets: [
            {
              label: `Distribution by ${this.selectedColumn}`,
              data,
              backgroundColor: labels.map((_, i) => this.palette(i)),
              borderWidth: 1,
            },
          ],
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          layout: {
            padding: 28,
          },
          plugins: {
            legend: { position: "right" },
            tooltip: {
              callbacks: {
                label: (context) => {
                  const label = context.label || "";
                  const val = context.raw || 0;
                  const total = context.dataset.data.reduce((s, x) => s + x, 0);
                  const pct = total ? ((val / total) * 100).toFixed(1) : "0.0";
                  return `${label}: ${val} (${pct}%)`;
                },
              },
            },
            datalabels: {
              color: "#000",
              formatter: (value, ctx) => {
                const dataset = ctx.chart.data.datasets[0].data;
                const total = dataset.reduce((s, x) => s + x, 0);
                const pct = total ? (value / total) * 100 : 0;
                return pct >= 2 ? `${pct.toFixed(1)}%` : "";
              },
              anchor: "end",
              align: "end",
              offset: 2,
              textStrokeColor: "#fff",
              textStrokeWidth: 2,
              clamp: true,
              clip: false,
            },
          },
        },
        plugins: [ChartDataLabels],
      });
    },
  },
};
</script>

<style scoped>
.pie-card :deep(.ant-card-head-title) {
  font-size: 0.9rem;
  font-weight: 600;
}

.chart-shell {
  height: 400px;
}

.controls-row {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  flex-wrap: nowrap;
  white-space: nowrap;
}

.ctrl-label {
  font-size: 0.75rem;
  color: #6b7280;
}

.ctrl-select,
.ctrl-input {
  height: 26px;
  background: #fff;
  border: 1px solid #e5e7eb;
  border-radius: 6px;
  font-size: 0.75rem;
  line-height: 1;
  color: #374151;
  padding: 0 8px;
  outline: none;
}

.ctrl-select {
  min-width: 70px;
}

.ctrl-input {
  width: 50px;
}

.ctrl-select:focus,
.ctrl-input:focus {
  border-color: #a5b4fc;
}

/* keep canvas from touching edges */
canvas {
  padding: 4px;
  box-sizing: border-box;
}
</style>
