<template>
  <a-card
    title="COE Premium Trends"
    :bordered="false"
    class="h-full shadow-md rounded-lg"
  >
    <template #extra>
      <div class="flex items-center space-x-2">
        <label for="yearFilter" style="font-size: 0.85rem; margin-right: 0.25rem;">
          Show last:
        </label>

        <select
          id="yearFilter"
          v-model.number="numYears"
          @change="fetchData"
          class="yearFilter"
        >
          <option v-for="n in 15" :key="n" :value="n">
            {{ n }} year{{ n > 1 ? 's' : '' }}
          </option>
        </select>

        <!-- Download icon button (Vue 2, ant-design-vue v1.x) -->
        <!-- <a-button
          class="icon-btn"
          type="link"
          @click="downloadCSV"
          title="Download data as CSV"
        >
          <a-icon type="download" />
        </a-button> -->

        <a-button
          type="text"
          class="icon-btn"
          title="Download current view as CSV"
          aria-label="Download current view as CSV"
          @click="downloadCSV"
        >
          <svg class="icon-svg" viewBox="0 0 24 24" aria-hidden="true">
            <path
              d="M12 3a1 1 0 0 1 1 1v8.586l2.293-2.293a1 1 0 1 1 1.414 1.414l-4.001 4a1 1 0 0 1-1.412 0l-4.001-4a1 1 0 1 1 1.414-1.414L11 12.586V4a1 1 0 0 1 1-1zM5 19a1 1 0 1 0 0 2h14a1 1 0 1 0 0-2H5z"
              fill="currentColor"
              fill-rule="evenodd"
              clip-rule="evenodd"
            />
          </svg>
        </a-button>
      </div>
    </template>


    <div style="height: 400px;">
      <canvas ref="coeChart"></canvas>
    </div>
  </a-card>
</template>

<script>
import { Chart, registerables } from "chart.js";
import dayjs from "dayjs";
Chart.register(...registerables);

export default {
  name: "COEChart",
  props: {
    rows: {
      type: Array,
      default: () => [],
    },
    selectedCategory: {
      type: String,
      default: 'all',
    },
  },
  data() {
    return {
      chart: null,
      numYears: 5,
      previewLoading: false,
      previewError: "",
      viewLabels: [],
      viewCatA: [],
      viewCatB: [],
      firstRendered: false,
    };
  },
  watch: {
    // parent gives data
    rows: {
      immediate: true,
      handler(val) {
        if (Array.isArray(val) && val.length) {
          this.buildFromRows(val);
        }
      },
    },
    selectedCategory: {
      immediate: true,
      handler() {
        if (this.rows && this.rows.length) {
          this.buildFromRows(this.rows);
        }
      },
    },
  },
  methods: {
    // called when user changes "Show last"
    fetchData() {
      if (this.rows && this.rows.length) {
        this.buildFromRows(this.rows);
      }
    },

    buildFromRows(recordsRaw) {
      try {
        this.previewLoading = true;
        this.previewError = "";

        // keep only rows with premium
        let records = recordsRaw.filter(
          (r) =>
            r.Premium != null &&
            r.Premium !== "" &&
            !isNaN(parseFloat(r.Premium))
        );

        const catA = records.filter((r) => r.Vehicle_Class === "Category A");
        const catB = records.filter((r) => r.Vehicle_Class === "Category B");

        const currentYear = dayjs().year();
        const cutoffYear = currentYear - this.numYears;

        const withinWindow = (r) =>
          dayjs(r.Bidding_Date, "YYYY-MM-DD").year() >= cutoffYear;

        const filteredA = catA
          .filter((r) => r.Bidding_Date)
          .filter(withinWindow)
          .sort((a, b) => a.Bidding_Date.localeCompare(b.Bidding_Date));
        const filteredB = catB
          .filter((r) => r.Bidding_Date)
          .filter(withinWindow)
          .sort((a, b) => a.Bidding_Date.localeCompare(b.Bidding_Date));

        // we assume Cat A has all dates we want; if not, we could merge, but this was your original logic
        const labels = filteredA.map((r) => r.Bidding_Date);
        const premiumsA = filteredA.map((r) => parseFloat(r.Premium));

        // align B to labels (in case B missed a date)
        const mapB = new Map(
          filteredB.map((r) => [r.Bidding_Date, parseFloat(r.Premium)])
        );
        const premiumsB = labels.map((d) => mapB.get(d) ?? null);

        this.viewLabels = labels;
        this.viewCatA = premiumsA;
        this.viewCatB = premiumsB;

        this.$nextTick(() => {
          this.renderChart(labels, premiumsA, premiumsB);
        });
      } catch (e) {
        this.previewError = String(e?.message || e);
      } finally {
        this.previewLoading = false;
      }
    },

    renderChart(labels, premiumsA, premiumsB) {
      if (this.chart) this.chart.destroy();
      const ctx = this.$refs.coeChart.getContext("2d");

      const colorA = "#8e44ad";
      const colorB = "#2980b9";

      this.chart = new Chart(ctx, {
        type: "line",
        data: {
          labels,
          datasets: [
            {
              label: "Category A",
              data: premiumsA,
              borderColor: colorA,
              backgroundColor: "transparent",
              pointRadius: 0,
              fill: false,
              tension: 0.3,
              borderWidth: 2,
              hidden: this.selectedCategory === 'Category B',
            },
            {
              label: "Category B",
              data: premiumsB,
              borderColor: colorB,
              backgroundColor: "transparent",
              pointRadius: 0,
              fill: false,
              tension: 0.3,
              borderWidth: 2,
              hidden: this.selectedCategory === 'Category A',
            },
          ],
        },
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
                padding: 15,
                generateLabels(chart) {
                  const datasets = chart.data.datasets;
                  return datasets.map((dataset, i) => {
                    const isHidden = !chart.isDatasetVisible(i);
                    return {
                      text: dataset.label,
                      fillStyle: dataset.borderColor,
                      strokeStyle: dataset.borderColor,
                      lineWidth: 0,
                      hidden: isHidden,
                      datasetIndex: i,
                      fontColor: isHidden ? '#999' : '#333',
                      textDecoration: isHidden ? 'line-through' : 'none',
                    };
                  });
                },
              },
            },
            tooltip: {
              mode: "index",
              intersect: false,
              usePointStyle: false,
              callbacks: {
                labelColor: (ctx) => {
                  const color = ctx.dataset.borderColor;
                  return {
                    borderColor: color,
                    backgroundColor: color,
                  };
                },
                label: (context) => `S$${context.formattedValue}`,
              },
            },
          },
          interaction: {
            mode: "nearest",
            axis: "x",
            intersect: false,
          },
          scales: {
            x: {
              title: { display: true, text: "Month" },
              ticks: { maxRotation: 45, minRotation: 45 },
              grid: { display: false },
            },
            y: {
              title: { display: true, text: "Premium (SGD)" },
              beginAtZero: false,
              grid: { color: "rgba(0,0,0,0.05)" },
            },
          },
        },
      });
      if (!this.firstRendered) {
        this.$emit("loaded", "COEChart");
        this.firstRendered = true;
      }
    },

    downloadCSV() {
      const header = ["Date", "Category A", "Category B"];
      const rows = this.viewLabels.map((d, i) => [
        d,
        this.viewCatA[i] ?? "",
        this.viewCatB[i] ?? "",
      ]);

      const csv = [header, ...rows]
        .map((r) =>
          r
            .map((cell) => {
              const s = String(cell);
              const escaped = s.replace(/"/g, '""');
              return /[",\n]/.test(escaped) ? `"${escaped}"` : escaped;
            })
            .join(",")
        )
        .join("\n");

      const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `coe_premiums_last_${this.numYears}y.csv`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    },
  },
  mounted() {
    // if parent already has rows by the time this mounts
    if (this.rows && this.rows.length) {
      this.buildFromRows(this.rows);
    }
  },
};
</script>

<style scoped>
.flex {
  display: flex;
  justify-content: flex-end;
  align-items: center;
}
.space-x-2 > * + * {
  margin-left: 0.5rem;
}
.yearFilter {
  min-width: 90px;
  min-height: 27px;
  font-size: 0.8rem;
  border-radius: 6px;
  border: 1px solid #d9d9d9;
}
.download-btn {
  color: #595959;
  margin-left: 6px;
  padding: 0 6px;
}
.download-btn:hover {
  color: #1677ff;
}
.icon-btn {
  background: transparent;
  border: none !important; /* removes all borders/outlines */
  box-shadow: none !important;
  outline: none !important;
  padding: 0 6px;
  height: 24px;
  line-height: 24px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  color: #595959;
  cursor: pointer;
}

.icon-btn:hover {
  background: #f5f5f5; /* optional subtle hover */
  border: none !important;
}

.icon-btn:focus {
  outline: none !important;
  border: none !important;
  box-shadow: none !important;
}

.icon-svg {
  width: 18px;
  height: 18px;
  display: block;
  fill: currentColor;
}

.icon-svg { width: 18px; height: 18px; display: block; fill: currentColor; }
</style>
