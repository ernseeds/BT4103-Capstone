<template>
  <a-card
    :title="shortTitle"
    :bordered="false"
    class="h-full shadow-md rounded-lg price-coe-card"
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
            {{ colLabel(col) }}
          </option>
        </select>

        <template v-if="showTopN">
          <span class="ctrl-label">Top:</span>
          <input
            v-model.number="topN"
            type="number"
            min="1"
            max="30"
            class="ctrl-input"
            @change="updateChart"
          />
        </template>

        <span class="ctrl-label">X-axis:</span>
        <select
          v-model="xAxisMode"
          class="ctrl-select"
          @change="updateChart"
        >
          <option value="COE_LEFT">COE left (yrs)</option>
          <option value="AGE_VEHICLE">Vehicle age (yrs)</option>
        </select>

        <span class="ctrl-label">COE:</span>
        <select
          v-model="coeFilter"
          class="ctrl-select"
          @change="updateChart"
        >
          <option value="BOTH">Cat A & B</option>
          <option value="A">Cat A</option>
          <option value="B">Cat B</option>
        </select>        
      </div>
    </template>

    <div class="chart-shell">
      <canvas ref="priceCoEChart"></canvas>
    </div>
  </a-card>
</template>

<script>
import { Chart, registerables } from "chart.js";
Chart.register(...registerables);

export default {
  name: "AvgPriceByCOEDropdown",
  props: {
    rows: {
      type: Array,
      default: () => [],
    },
  },
  data() {
    return {
      localRows: [],
      chart: null,
      selectedColumn: "Brand",
      topN: 8,
      coeFilter: "BOTH",
      xAxisMode: "COE_LEFT",
      filterColumns: [
        "Brand",
        "COE_Category",
        "Make",
        "Fuel_Type",
        "Transmission",
        "Website",
        "NONE",
      ],
    };
  },
  computed: {
    showTopN() {
      return ["Brand", "Make", "Website"].includes(this.selectedColumn);
    },
    shortTitle() {
      return this.xAxisMode === "COE_LEFT"
        ? "Average Listing Price vs COE Left"
        : "Average Listing Price vs Vehicle Age";
    },
  },
  watch: {
    rows: {
      handler(newVal) {
        this.localRows = this.normalizeRows(newVal || []);
        this.updateChart();
      },
      deep: true,
    },
    selectedColumn() {
      this.updateChart();
    },
  },
  methods: {
    colLabel(k) {
      return k === "NONE" ? "None (all vehicles)" : k.replaceAll("_", " ");
    },
    toNumber(v) {
      if (typeof v === "number") return v;
      if (v == null || v === "") return NaN;
      return parseFloat(String(v).replace(/[^0-9.]/g, ""));
    },
    parseDate(d) {
      if (!d) return null;
      const t = new Date(d);
      return isNaN(t) ? null : t;
    },
    coeLeftYearsFromExpiry(expiryDate) {
      if (!expiryDate) return NaN;
      const now = new Date();
      const exp = this.parseDate(expiryDate);
      if (!exp) return NaN;
      return (exp - now) / (365.25 * 24 * 3600 * 1000);
    },
    bucket(value, step = 1) {
      return Math.floor(value / step) * step;
    },
    average(arr) {
      return !arr || !arr.length ? null : arr.reduce((a, b) => a + b, 0) / arr.length;
    },
    palette(i) {
      const hue = (i * 57) % 360;
      return `hsl(${hue} 65% 45%)`;
    },
    normalizeRows(rawRows) {
      const now = new Date();
      return (rawRows || [])
        .map((r) => {
          const price = this.toNumber(r.Price ?? r.price);

          // COE left
          let coeLeft = NaN;
          const coeLeftDays = this.toNumber(r.COE_Left_Days ?? r.coe_left_days);
          if (isFinite(coeLeftDays)) {
            coeLeft = coeLeftDays / 365.25;
          } else {
            coeLeft = this.coeLeftYearsFromExpiry(r.COE_Expiry_Date ?? r.coe_expiry_date);
          }

          // vehicle age
          let vehicleAge = NaN;
          const regDate = this.parseDate(r.Registration_Date ?? r.registration_date);
          if (regDate) {
            vehicleAge = (now - regDate) / (365.25 * 24 * 3600 * 1000);
          }

          return {
            price,
            coeLeft,
            vehicleAge,
            COE_Category: (r.COE_Category || "").toString().trim().toUpperCase(),
            Brand: (r.Brand || "").toString().trim(),
            Make: (r.Make || "").toString().trim(),
            Fuel_Type: (r.Fuel_Type || "").toString().trim(),
            Transmission: (r.Transmission || "").toString().trim(),
            Website: (r.Website || "").toString().trim(),
          };
        })
        .filter((x) => {
          if (!isFinite(x.price)) return false;
          if (this.xAxisMode === "COE_LEFT") {
            return isFinite(x.coeLeft) && x.coeLeft >= 0;
          } else {
            return isFinite(x.vehicleAge) && x.vehicleAge >= 0;
          }
        });
    },
    topKGroups(splitField, allowedCats = ["A", "B"]) {
      if (splitField === "NONE") return ["All"];
      const counts = new Map();
      for (const r of this.localRows) {
        if (!allowedCats.includes(r.COE_Category)) continue;
        const key = r[splitField] || "N/A";
        counts.set(key, (counts.get(key) || 0) + 1);
      }
      let entries = [...counts.entries()].sort((a, b) => b[1] - a[1]);
      if (this.showTopN && entries.length > this.topN) {
        entries = entries.slice(0, this.topN);
      }
      return entries.map(([k]) => k);
    },
    buildDatasets() {
      const splitField = this.selectedColumn;
      const allowed = this.coeFilter === "BOTH" ? ["A", "B"] : [this.coeFilter];
      const groups = this.topKGroups(splitField, allowed);

      const xBins = new Set();
      const bucketMap = new Map();

      for (const r of this.localRows) {
        if (!allowed.includes(r.COE_Category)) continue;

        const group = splitField === "NONE" ? "All" : (r[splitField] || "N/A");
        if (!groups.includes(group)) continue;

        const xVal = this.xAxisMode === "COE_LEFT" ? r.coeLeft : r.vehicleAge;
        if (!isFinite(xVal) || xVal < 0) continue;

        const bin = this.bucket(xVal, 1);
        xBins.add(bin);

        if (!bucketMap.has(group)) bucketMap.set(group, new Map());
        const m = bucketMap.get(group);
        if (!m.has(bin)) m.set(bin, []);
        m.get(bin).push(r.price);
      }

      const labels = [...xBins].sort((a, b) => a - b);
      const datasets = [...bucketMap.entries()].map(([group, m], idx) => {
        const series = labels.map((bin) => this.average(m.get(bin) || []));
        return {
          label: group,
          data: series,
          borderColor: this.palette(idx),
          pointRadius: 1.5,
          fill: false,
          tension: 0.25,
          borderWidth: 2,
          spanGaps: true,
        };
      });

      return { labels, datasets };
    },
    updateChart() {
      if (!this.localRows.length) {
        if (this.chart) {
          this.chart.destroy();
          this.chart = null;
        }
        return;
      }

      const { labels, datasets } = this.buildDatasets();

      if (this.chart) this.chart.destroy();
      const ctx = this.$refs.priceCoEChart.getContext("2d");
      this.chart = new Chart(ctx, {
        type: "line",
        data: { labels, datasets },
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
              },
            },
            tooltip: {
              mode: "index",
              intersect: false,
              callbacks: {
                title: (items) => {
                  const val = items[0].label;
                  return this.xAxisMode === "COE_LEFT"
                    ? `COE left: ${val} yrs`
                    : `Vehicle age: ${val} yrs`;
                },
                label: (ctx) =>
                  `${ctx.dataset.label}: S$${Number(ctx.parsed.y).toLocaleString(undefined, {
                    maximumFractionDigits: 0,
                  })}`,
              },
            },
          },
          interaction: { mode: "nearest", axis: "x", intersect: false },
          scales: {
            x: {
              type: "linear",
              title: {
                display: true,
                text:
                  this.xAxisMode === "COE_LEFT"
                    ? "COE Left (years)"
                    : "Vehicle Age (years)",
              },
              ticks: { stepSize: 1 },
              grid: { display: false },
              reverse: this.xAxisMode === "COE_LEFT",
            },
            y: {
              title: { display: true, text: "Average Price (SGD)" },
              grid: { color: "rgba(0,0,0,0.05)" },
              ticks: {
                callback: (v) =>
                  "S$" + Number(v).toLocaleString(undefined, { maximumFractionDigits: 0 }),
              },
            },
          },
        },
      });
    },
  },
  mounted() {
    this.localRows = this.normalizeRows(this.rows || []);
    this.updateChart();
  },
};
</script>

<style scoped>
.price-coe-card :deep(.ant-card-head-title) {
  font-size: 0.9rem;
  font-weight: 600;
}

.chart-shell {
  height: 490px;
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

/* make native selects look like your COE card select */
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
  min-width: 50px;
}

.ctrl-select:focus,
.ctrl-input:focus {
  border-color: #a5b4fc;
}

.ctrl-input {
  width: 50px;
}
</style>
