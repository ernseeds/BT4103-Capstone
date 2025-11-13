<template>
  <a-card
    title="COE Premium Forecast (Cat B)"
    :bordered="false"
    class="h-full shadow-md rounded-lg"
  >
    <!-- Top-right filters -->
    <template #extra>
      <div class="filters">
        <label for="histYears" class="filter-label">Show last:</label>
        <select
          id="histYears"
          v-model.number="historyYears"
          @change="fetchData"
          class="yearFilter"
        >
          <option v-for="n in 15" :key="'h'+n" :value="n">{{ n }} year{{ n > 1 ? 's' : '' }}</option>
        </select>

        <label for="fcYears" class="filter-label" style="margin-left:10px;">Predict next:</label>
        <select
          id="fcYears"
          v-model.number="forecastYears"
          @change="fetchData"
          class="yearFilter"
        >
          <option v-for="n in 10" :key="'f'+n" :value="n">{{ n }} year{{ n > 1 ? 's' : '' }}</option>
        </select>

        <a-popover placement="left" trigger="hover">
            <template #content>
                <div style="max-width: 280px; font-size: 12px; line-height: 1.4;">
                <strong>Forecast uncertainty</strong><br/>
                Predictions include a <em>95% Confidence Interval (CI)</em> — a range expected to
                contain the true premium 95% of the time under model assumptions.<br/>
                As forecasts extend further into the future, this interval widens, meaning the
                estimates become less reliable and should be interpreted with caution.
                </div>
            </template>
            <a-button class="info-icon-btn" aria-label="Forecast explanation">ⓘ</a-button>
        </a-popover>
      </div>
    </template>

    <div style="height: 450px;">
      <canvas ref="chartEl"></canvas>
    </div>
  </a-card>
</template>

<script>
import { Chart, registerables } from "chart.js";
import dayjs from "dayjs";
Chart.register(...registerables);

export default {
  name: "CatBCOEPrediction",
  props: {
    // parent passes in COE rows
    rows: {
      type: Array,
      default: () => [],
    },
  },
  data() {
    return {
      chart: null,
      historyYears: 5,  // Show last: N years
      forecastYears: 1, // Predict next: N years
      firstRendered: false,
    };
  },
  watch: {
    // when parent fetches and sets coeRows
    rows: {
      immediate: true,
      handler(val) {
        if (Array.isArray(val) && val.length) {
          this.buildFromRows(val);
        }
      },
    },
  },
  methods: {
    num(x) {
      if (x == null || x === "") return null;
      const n = parseFloat(String(x).replace(/,/g, "").trim());
      return Number.isFinite(n) ? n : null;
    },

    // called by the selects in template
    fetchData() {
      if (this.rows && this.rows.length) {
        this.buildFromRows(this.rows);
      }
    },

    buildFromRows(allRows) {
      // Historical: Premium present, Cat B only
      let histRows = allRows.filter(
        (r) =>
          r.Premium != null &&
          r.Premium !== "" &&
          !isNaN(parseFloat(r.Premium))
      );
      histRows = histRows
        .filter((r) => r.Vehicle_Class === "Category B" && r.Bidding_Date)
        .sort((a, b) => a.Bidding_Date.localeCompare(b.Bidding_Date));

      // Window by "Show last: N years"
      const currentYear = dayjs().year();
      const cutoffYear = currentYear - this.historyYears;
      const histFiltered = histRows.filter((r) => {
        const yr = dayjs(r.Bidding_Date, "YYYY-MM-DD").year();
        return yr >= cutoffYear;
      });

      const histLabels = histFiltered.map((r) => r.Bidding_Date);
      const histValues = histFiltered.map((r) => this.num(r.Premium));

      // Last historical date (anchor forecast)
      const lastHistDateStr =
        histRows.length ? histRows[histRows.length - 1].Bidding_Date : null;

      // Forecast: Cat B from lastHistDate → +forecastYears
      let fcRows = allRows
        .filter((r) => r.Vehicle_Class === "Category B" && r.Bidding_Date)
        .sort((a, b) => a.Bidding_Date.localeCompare(b.Bidding_Date));

      if (lastHistDateStr) {
        const horizonEndStr = dayjs(lastHistDateStr)
          .add(this.forecastYears, "year")
          .format("YYYY-MM-DD");
        fcRows = fcRows.filter(
          (r) =>
            r.Bidding_Date >= lastHistDateStr &&
            r.Bidding_Date <= horizonEndStr
        );
      } else if (fcRows.length) {
        const startStr = fcRows[0].Bidding_Date;
        const horizonEndStr = dayjs(startStr)
          .add(this.forecastYears, "year")
          .format("YYYY-MM-DD");
        fcRows = fcRows.filter((r) => r.Bidding_Date <= horizonEndStr);
      }

      const fcLabels = fcRows.map((r) => r.Bidding_Date);
      const fcValues = fcRows.map((r) =>
        this.num(r.Premium_Forecast ?? r.premium_forecast)
      );
      const ciLo = fcRows.map((r) => this.num(r.CI_Lower ?? r.ci_lower));
      const ciHi = fcRows.map((r) => this.num(r.CI_Upper ?? r.ci_upper));

      // Merge axis labels (avoid duplicate join date)
      let labels = histLabels.slice();
      if (fcLabels.length) {
        const startIdx =
          labels.length && fcLabels[0] === labels[labels.length - 1] ? 1 : 0;
        labels = labels.concat(fcLabels.slice(startIdx));
      }

      // Align series to merged labels
      const mapHist = new Map(histLabels.map((d, i) => [d, histValues[i]]));
      const mapFc = new Map(fcLabels.map((d, i) => [d, fcValues[i]]));
      const mapLo = new Map(fcLabels.map((d, i) => [d, ciLo[i]]));
      const mapHi = new Map(fcLabels.map((d, i) => [d, ciHi[i]]));

      const histAligned = [];
      const fcAligned = [];
      const ciLoAligned = [];
      const ciHiAligned = [];

      for (const d of labels) {
        if (mapHist.has(d)) {
          histAligned.push(mapHist.get(d));
          fcAligned.push(null);
          ciLoAligned.push(null);
          ciHiAligned.push(null);
        } else {
          histAligned.push(null);
          fcAligned.push(mapFc.get(d) ?? null);
          ciLoAligned.push(mapLo.get(d) ?? null);
          ciHiAligned.push(mapHi.get(d) ?? null);
        }
      }

      this.$nextTick(() => {
        this.renderChart(labels, histAligned, fcAligned, ciLoAligned, ciHiAligned);
      });
    },

    renderChart(labels, hist, fc, ciLo, ciHi) {
      const el = this.$refs.chartEl;
      if (!el) return;
      const ctx = el.getContext("2d");
      if (!ctx) return;

      if (this.chart && typeof this.chart.destroy === "function") {
        this.chart.destroy();
      }

      // Same palette as Cat A
      const ciUpperLine = "#96d4af";
      const ciLowerLine = "#ffce1b";
      const ciBandFill = "rgba(30, 136, 229, 0.25)";
      const forecastLine = "#1976d2";
      const historicalLine = "#8e44ad"; // purple for Cat B

      this.chart = new Chart(ctx, {
        type: "line",
        data: {
          labels,
          datasets: [
            {
              label: "Lower Confidence Interval (CI)",
              data: ciLo,
              borderColor: ciLowerLine,
              backgroundColor: "transparent",
              borderDash: [4, 3],
              borderWidth: 1.5,
              pointRadius: 0,
              spanGaps: true,
              order: 3,
            },
            {
              label: "Upper Confidence Interval (CI)",
              data: ciHi,
              borderColor: ciUpperLine,
              backgroundColor: ciBandFill,
              fill: "-1",
              borderDash: [4, 3],
              borderWidth: 1.5,
              pointRadius: 0,
              spanGaps: true,
              order: 2,
            },
            {
              label: "Historical",
              data: hist,
              borderColor: historicalLine,
              backgroundColor: "transparent",
              borderWidth: 2,
              pointRadius: 0,
              spanGaps: false,
              order: 1,
            },
            {
              label: "Forecast",
              data: fc,
              borderColor: forecastLine,
              backgroundColor: "transparent",
              borderDash: [6, 6],
              borderWidth: 2,
              pointRadius: 0,
              spanGaps: false,
              order: 0,
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
              labels: { usePointStyle: true, pointStyle: "line" },
            },
            tooltip: {
              usePointStyle: false,
              itemSort: (a, b) => {
                const order = {
                  "Upper Confidence Interval (CI)": 0,
                  "Forecast": 1,
                  "Lower Confidence Interval (CI)": 2,
                  "Historical": 3,
                };
                const ai = order[a.dataset.label] ?? 99;
                const bi = order[b.dataset.label] ?? 99;
                return ai - bi;
              },
              callbacks: {
                labelColor: (ctx) => {
                  const idx = ctx.datasetIndex;
                  const color =
                    idx === 0
                      ? ciLowerLine
                      : idx === 1
                      ? ciBandFill
                      : idx === 2
                      ? historicalLine
                      : idx === 3
                      ? forecastLine
                      : "#999";
                  return {
                    borderColor: color,
                    backgroundColor: color,
                  };
                },
                label: (ctx) => {
                  const label = ctx.dataset.label || "";
                  const v = ctx.raw;
                  const val = v == null ? "–" : Number(v).toLocaleString();
                  if (label === "Upper Confidence Interval (CI)")
                    return `Upper CI: ${val}`;
                  if (label === "Forecast") return `Forecast: ${val}`;
                  if (label === "Lower Confidence Interval (CI)")
                    return `Lower CI: ${val}`;
                  return `${label}: ${val}`;
                },
              },
            },
          },
          scales: {
            x: {
              title: { display: true, text: "Date" },
              ticks: { maxRotation: 45, minRotation: 45 },
              grid: { display: false },
            },
            y: {
              title: { display: true, text: "Premium (SGD)" },
              beginAtZero: false,
              grid: { color: "rgba(0,0,0,0.05)" },
              ticks: { callback: (v) => Number(v).toLocaleString() },
            },
          },
        },
      });
      if (!this.firstRendered) {
        this.$emit("loaded", "CatBPred");
        this.firstRendered = true;
      }
    },
  },
  mounted() {
    // if parent already sent rows before mount
    if (this.rows && this.rows.length) {
      this.buildFromRows(this.rows);
    }
  },
};
</script>

<style scoped>
.filters {
  display: flex;
  align-items: center;
}
.filter-label {
  font-size: 0.85rem;
  margin-right: 0.25rem;
}
.yearFilter {
  min-width: 90px;
  min-height: 27px;
  font-size: 0.8rem;
  border-radius: 6px;
  border: 1px solid #d9d9d9;
  margin-right: 6px;
}
.info-icon-btn {
  border: none !important;
  background: transparent !important;
  box-shadow: none !important;
  color: #8c8c8c !important;
  padding: 0 4px !important;
  margin-left: 5px;
  font-size: 14px;
  line-height: 1;
  cursor: pointer;
}
.info-icon-btn:hover,
.info-icon-btn:focus,
.info-icon-btn:active {
  border: none !important;
  background: transparent !important;
  box-shadow: none !important;
  color: #1677ff !important; /* blue hover colour */
  outline: none !important;
}
</style>
