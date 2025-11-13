<template>
  <a-card
    title="Quota vs Bids by Category"
    :bordered="false"
    class="h-full shadow-md rounded-lg"
  >
    <!-- 🟣 Top-right filters + info + download -->
    <template #extra>
      <div class="filter-top-right">
        <span class="label">Category:</span>
        <select
          v-model="internalCategory"
          @change="fetchData"
          class="filter-input"
        >
          <option value="All">All</option>
          <option value="Category A">A</option>
          <option value="Category B">B</option>
        </select>

        <span class="label">Show last:</span>
        <input
          type="number"
          min="1"
          v-model.number="numRounds"
          @change="fetchData"
          class="filter-input"
        />
        <span>rounds</span>

        <!-- ℹ️ Info popover -->
        <a-popover placement="left" trigger="hover">
          <template #content>
            <div style="max-width: 280px; font-size: 12px; line-height: 1.4;">
              <strong>What this shows</strong><br />
              • <em>Quota</em> = available certificates.<br />
              • <em>Bids Received</em> = total bids submitted.<br />
              • <em>Bid-Quota Ratio</em> = Bids / Quota (x).<br /><br />
              <strong>Interpretation</strong><br />
              Ratio is usually <strong>1.3–1.7×</strong>. Spikes above <strong>1.7×</strong> can mean short-term demand surges or tight quotas. Watching the ratio helps you spot shifts in market pressure.
            </div>
          </template>
          <button class="info-icon" aria-label="Demand & ratio explanation">ⓘ</button>
        </a-popover>

        <!-- ⬇️ Download CSV icon (Ant Design button for reliable clicks) -->
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

    <div style="height: 450px;">
      <canvas ref="quotaBidsChart"></canvas>
    </div>
  </a-card>
</template>

<script>
import { Chart, registerables } from "chart.js";
Chart.register(...registerables);

export default {
  name: "QuotaBidsChart",
  props: {
    // parent passes COE data
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
      internalCategory: "All",
      numRounds: 10,

      // for CSV of current view
      viewLabels: [],
      viewQuota: [],
      viewReceived: [],
      viewRatio: [],

      firstRendered: false,
    };
  },
  watch: {
    // parent finishes loading coeRows
    rows: {
      immediate: true,
      handler(val) {
        if (Array.isArray(val) && val.length) {
          this.rebuildFromRows(val);
        }
      },
    },
    selectedCategory: {
      immediate: true,
      handler(val) {
        if (val === 'all') {
          this.internalCategory = 'All';
        } else {
          this.internalCategory = val;
        }
        if (this.rows && this.rows.length) {
          this.rebuildFromRows(this.rows);
        }
      },
    },
  },
  methods: {
    toNumberMaybe(x) {
      if (x == null) return 0;
      if (typeof x === "number") return x;
      const n = parseFloat(String(x).replace(/,/g, "").trim());
      return isNaN(n) ? 0 : n;
    },

    // triggered by select / input in template
    fetchData() {
      if (this.rows && this.rows.length) {
        this.rebuildFromRows(this.rows);
      }
    },

    rebuildFromRows(allRows) {
      try {
        // base filter: valid premium + date + cat A/B
        let records = allRows.filter(
          (r) =>
            r.Premium != null &&
            r.Premium !== "" &&
            !isNaN(parseFloat(r.Premium))
        );

        let filtered = records.filter(
          (r) =>
            r.Bidding_Date &&
            ["Category A", "Category B"].includes(r.Vehicle_Class)
        );

        if (this.internalCategory !== "All" && this.internalCategory !== 'all') {
          filtered = filtered.filter(
            (r) => r.Vehicle_Class === this.internalCategory
          );
        }

        // group by date
        const grouped = {};
        filtered.forEach((r) => {
          const key = r.Bidding_Date;

          const quota =
            this.toNumberMaybe(r.Quota) ||
            this.toNumberMaybe(r.quota) ||
            this.toNumberMaybe(r.Total_Quota) ||
            this.toNumberMaybe(r.Quota_Available);

          const bidsReceived =
            this.toNumberMaybe(r.Bids_Received) ||
            this.toNumberMaybe(r.bids_received) ||
            this.toNumberMaybe(r.BidsReceived);

          if (!grouped[key]) {
            grouped[key] = {
              date: r.Bidding_Date,
              quota: 0,
              received: 0,
            };
          }
          grouped[key].quota += quota;
          grouped[key].received += bidsReceived;
        });

        const dataArr = Object.values(grouped).sort((a, b) =>
          a.date.localeCompare(b.date)
        );
        const recent = dataArr.slice(-this.numRounds);

        const labels = recent.map((r) => r.date);
        const quotaData = recent.map((r) => r.quota);
        const receivedData = recent.map((r) => r.received);
        const ratioData = recent.map((r) =>
          r.quota > 0 ? Number((r.received / r.quota).toFixed(2)) : 0
        );

        // store view for CSV
        this.viewLabels = labels;
        this.viewQuota = quotaData;
        this.viewReceived = receivedData;
        this.viewRatio = ratioData;

        this.$nextTick(() => {
          this.renderChart(labels, quotaData, receivedData, ratioData);
        });
      } catch (err) {
        console.error("Error building Quota vs Bids chart:", err);
      }
    },

    renderChart(labels, quotaData, receivedData, ratioData) {
      if (this.chart) this.chart.destroy();
      const ctx = this.$refs.quotaBidsChart.getContext("2d");

      // vertical separators plugin kept from your original
      const verticalSeparatorsPlugin = {
        id: "verticalSeparatorsBetweenGroups",
        afterDraw: (chart) => {
          const { ctx, chartArea, scales } = chart;
          const { top, bottom } = chartArea;
          const x = scales.x;
          if (!x || !x.ticks || x.ticks.length < 2) return;

          ctx.save();
          ctx.strokeStyle = "rgba(0,0,0,0.15)";
          ctx.lineWidth = 1;

          for (let i = 0; i < x.ticks.length - 1; i++) {
            const x1 = x.getPixelForTick(i);
            const x2 = x.getPixelForTick(i + 1);
            const mid = (x1 + x2) / 2;
            ctx.beginPath();
            ctx.moveTo(mid, top);
            ctx.lineTo(mid, bottom);
            ctx.stroke();
          }

          ctx.restore();
        },
      };

      const ratioColor = "#000000";

      this.chart = new Chart(ctx, {
        type: "bar",
        data: {
          labels,
          datasets: [
            {
              type: "bar",
              label: "Quota",
              data: quotaData,
              backgroundColor: "rgba(52, 152, 219, 0.7)",
              yAxisID: "y",
            },
            {
              type: "bar",
              label: "Bids Received",
              data: receivedData,
              backgroundColor: "rgba(231, 76, 60, 0.7)",
              yAxisID: "y",
            },
            {
              type: "line",
              label: "Bid-Quota Ratio",
              data: ratioData,
              borderColor: ratioColor,
              borderWidth: 2,
              tension: 0.3,
              pointRadius: 3,
              pointBackgroundColor: ratioColor,
              pointStyle: "circle",
              yAxisID: "y1",
            },
          ],
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          interaction: { mode: "index", intersect: false },
          plugins: {
            legend: {
              position: "bottom",
              labels: {
                usePointStyle: true,
                padding: 14,
                generateLabels: (chart) => {
                  const { datasets } = chart.data;
                  return datasets.map((ds, i) => {
                    let fillStyle =
                      ds.type === "line" && ds.label === "Bid-Quota Ratio"
                        ? ratioColor
                        : ds.backgroundColor || ds.borderColor || "#999";
                    if (Array.isArray(fillStyle)) fillStyle = fillStyle[0];
                    return {
                      text: ds.label,
                      fillStyle,
                      strokeStyle: fillStyle,
                      lineWidth: 0,
                      hidden: !chart.isDatasetVisible(i),
                      datasetIndex: i,
                      pointStyle: "circle",
                    };
                  });
                },
              },
            },
            tooltip: {
              mode: "index",
              intersect: false,
              callbacks: {
                labelColor: (ctx) => {
                  if (ctx.dataset.label === "Bid-Quota Ratio") {
                    return {
                      borderColor: ratioColor,
                      backgroundColor: ratioColor,
                    };
                  }
                  const c =
                    ctx.dataset.backgroundColor ||
                    ctx.dataset.borderColor ||
                    "#999";
                  return { borderColor: c, backgroundColor: c };
                },
                label: (context) => {
                  if (context.dataset.label === "Bid-Quota Ratio") {
                    return `Ratio: ${context.formattedValue}x`;
                  }
                  const val = Number(context.raw).toLocaleString();
                  return `${context.dataset.label}: ${val}`;
                },
              },
            },
          },
          scales: {
            x: {
              title: { display: true, text: "Bidding Date" },
              ticks: { maxRotation: 45, minRotation: 45 },
              grid: { display: false },
            },
            y: {
              title: { display: true, text: "Quota / Bids" },
              beginAtZero: true,
              ticks: { callback: (v) => Number(v).toLocaleString() },
            },
            y1: {
              position: "right",
              title: { display: true, text: "Bid-Quota Ratio" },
              grid: { drawOnChartArea: false },
            },
          },
        },
        plugins: [verticalSeparatorsPlugin],
      });
      if (!this.firstRendered) {
        this.$emit("loaded", "QuotaBids");
        this.firstRendered = true;
      }
    },

    // unchanged — uses view* arrays
    downloadCSV() {
      const header = ["Date", "Quota", "Bids Received", "Bid-Quota Ratio"];
      const rows = this.viewLabels.map((d, i) => [
        d,
        this.viewQuota[i] ?? "",
        this.viewReceived[i] ?? "",
        this.viewRatio[i] ?? "",
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
      const cat = this.selectedCategory.replace(/\s+/g, "") || "All";
      a.href = url;
      a.download = `quota_bids_${cat}_last_${this.numRounds}_rounds.csv`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    },
  },
  mounted() {
    // in case parent already has rows before we mount
    if (this.rows && this.rows.length) {
      this.rebuildFromRows(this.rows);
    }
  },
};
</script>

<style scoped>
/* Ensure header tools are clickable */
:deep(.ant-card-head) { overflow: visible; }
:deep(.ant-card-extra) { pointer-events: auto; }

/* 🟣 Filter Layout */
.filter-top-right {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  pointer-events: auto; /* make sure children receive clicks */
}

.label {
  font-size: 0.85rem;
}

/* Unified styling for both select & number input */
.filter-input {
  min-width: 55px;
  min-height: 27px;
  font-size: 0.8rem;
  border-radius: 6px;
  border: 1px solid #d9d9d9;
  padding: 0.15rem 0.3rem;
  background: #fff;
  outline: none;
  line-height: 1;
  gap: 0.6rem;
}

.filter-input[type="number"] {
  width: 55px;
  min-width: 0;
}

/* remove spinners (webkit) */
.filter-input[type="number"]::-webkit-outer-spin-button,
.filter-input[type="number"]::-webkit-inner-spin-button {
  -webkit-appearance: none;
  margin: 0;
}

/* focus ring */
.filter-input:focus {
  border-color: #1677ff;
  box-shadow: 0 0 0 2px rgba(22, 119, 255, 0.2);
}

/* ⓘ Info icon with no border */
.info-icon {
  background: transparent;
  border: none;
  padding: 0 6px;
  line-height: 1;
  cursor: pointer;
  color: #595959;
  font-size: 16px;
}
.info-icon:hover,
.info-icon:focus {
  color: #1677ff;
  outline: none;
}

/* Download icon button (AntD <a-button type="text">) */
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
