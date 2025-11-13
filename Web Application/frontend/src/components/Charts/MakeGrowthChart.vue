<template>
  <a-card title="Make Growth (YoY %)" :bordered="false">
    <template #extra>
      <div class="top-right-controls">
        <span class="label">Year:</span>
        <select v-model.number="selectedYear" @change="fetchData" class="filter-select">
          <option v-for="y in availableYears" :key="y" :value="y">{{ y }}</option>
        </select>
        
        <span class="label">Top:</span>
        <select v-model.number="topN" @change="fetchData" class="filter-select">
          <option v-for="n in [5,10,15,20]" :key="n" :value="n">{{ n }} makes</option>
        </select>
        
        <a-popover placement="left" trigger="hover">
          <template #content>
            <div style="max-width: 320px; font-size: 12px; line-height: 1.45;">
              <strong>What is YoY?</strong><br/>
              Year-over-Year compares this year against the previous year.<br/><br/>
              <strong>Formula</strong><br/>
              YoY% = <em>(Current − Previous) / Previous × 100</em><br/><br/>
              <strong>Colours</strong><br/>
              • <span class="chip chip-green">Green:</span> Strong growth (&gt; 50%)<br/>
              • <span class="chip chip-blue">Blue:</span> Good growth (20–50%)<br/>
              • <span class="chip chip-yellow">Yellow:</span> Mild growth (0–20%)<br/>
              • <span class="chip chip-orange">Orange:</span> Slight decline (0 to −20%)<br/>
              • <span class="chip chip-red">Red:</span> Strong decline (&lt; −20%)
            </div>
          </template>
          <button class="info-icon" aria-label="Demand & ratio explanation">ⓘ</button>
        </a-popover>
        
        <button class="icon-btn" @click="downloadVisibleCSV" title="Download CSV">
          <svg class="icon-svg" viewBox="0 0 24 24">
            <path d="M12 3a1 1 0 0 1 1 1v8.586l2.293-2.293a1 1 0 1 1 1.414 1.414l-4.001 4a1 1 0 0 1-1.412 0l-4.001-4a1 1 0 1 1 1.414-1.414L11 12.586V4a1 1 0 0 1 1-1zM5 19a1 1 0 1 0 0 2h14a1 1 0 1 0 0-2H5z" fill="currentColor"/>
          </svg>
        </button>
      </div>
    </template>
    
    <div style="height:400px;">
      <canvas ref="growthChart"></canvas>
    </div>
  </a-card>
</template>

<script>
import { Chart, registerables } from "chart.js";
import axios from "axios";
Chart.register(...registerables);

export default {
  name: "MakeGrowthChart",
  data() {
    return {
      chart: null,
      datasetId: "d_20d3fc7f08caa581c5586df51a8993c5",
      availableYears: [],
      selectedYear: null,
      topN: 10,

      // For download of visible/filtered table
      tableRows: [], // [{ make, previousYear, currentYear, yoy }]
      prevYear: null,
    };
  },
  methods: {
    async fetchData() {
      try {
        const url = `https://data.gov.sg/api/action/datastore_search?resource_id=${this.datasetId}&limit=50000`;
        const { data: resp } = await axios.get(url);
        const records = resp.result.records;

        const valid = records.filter(
          (r) => r.year && r.make && r.number && !isNaN(r.number)
        );

        const data = valid.map((r) => ({
          year: parseInt(r.year, 10),
          make: String(r.make || "").trim(),
          number: parseInt(r.number, 10),
        }));

        // Available years
        this.availableYears = [...new Set(data.map((d) => d.year))].sort((a, b) => a - b);
        if (!this.selectedYear) this.selectedYear = Math.max(...this.availableYears);

        const prevYear = this.selectedYear - 1;
        this.prevYear = prevYear;

        const yearData = data.filter((d) => d.year === this.selectedYear);
        const prevData = data.filter((d) => d.year === prevYear);

        // Aggregate by make
        const currTotals = {};
        yearData.forEach((d) => (currTotals[d.make] = (currTotals[d.make] || 0) + d.number));
        const prevTotals = {};
        prevData.forEach((d) => (prevTotals[d.make] = (prevTotals[d.make] || 0) + d.number));

        // Compute YoY
        const growthData = Object.keys(currTotals).map((make) => {
          const curr = currTotals[make];
          const prev = prevTotals[make] || 0;
          const yoy = prev > 0 ? ((curr - prev) / prev) * 100 : 0;
          return { make, curr, prev, yoy };
        });

        // Sort by YoY and take Top N
        const sorted = growthData
          .sort((a, b) => b.yoy - a.yoy)
          .slice(0, this.topN);

        // Save table for CSV
        this.tableRows = sorted.map(({ make, curr, prev, yoy }) => ({
          make,
          previousYear: prev,
          currentYear: curr,
          yoy: Number.isFinite(yoy) ? Number(yoy.toFixed(2)) : 0,
        }));

        // Render chart
        this.renderChart(
          sorted.map((d) => d.make),
          sorted.map((d) => d.yoy)
        );
      } catch (err) {
        console.error("Error fetching growth data:", err);
      } finally {
        this.$emit("loaded", "MakeGrowth");
      }
    },

    // 🎨 Colour bands for YoY%
    colorForGrowth(value) {
      if (value > 50) return "rgba(88, 214, 141, 0.9)";  // strong growth - green
      if (value > 20) return "rgba(46, 134, 193, 0.9)";  // good growth   - blue
      if (value > 0)  return "rgba(244, 208, 63, 0.9)";  // mild growth   - yellow
      if (value > -20) return "rgba(230, 126, 34, 0.9)"; // slight decline- orange
      return "rgba(231, 76, 60, 0.9)";                   // strong decline- red
    },

    renderChart(labels, values) {
      if (this.chart) this.chart.destroy();
      const ctx = this.$refs.growthChart.getContext("2d");

      const colors = values.map((v) => this.colorForGrowth(v));

      this.chart = new Chart(ctx, {
        type: "bar",
        data: {
          labels,
          datasets: [
            {
              label: "YoY Growth (%)",
              data: values,
              backgroundColor: colors,
              borderRadius: 6,
            },
          ],
        },
        options: {
          indexAxis: "y",
          responsive: true,
          maintainAspectRatio: false,
          layout: { padding: { top: 10, bottom: 20 } },
          scales: {
            x: {
              title: { display: true, text: "YoY Growth (%)" },
              beginAtZero: true,
              grid: { color: "rgba(0,0,0,0.05)" },
              ticks: { callback: (v) => `${v}%` },
            },
            y: {
              title: { display: false },
              ticks: { autoSkip: false, font: { size: 12 } },
            },
          },
          plugins: {
            legend: { display: false },
            tooltip: {
              callbacks: {
                label: (ctx) => `${ctx.label}: ${Number(ctx.parsed.x).toFixed(2)}%`,
              },
            },
          },
        },
      });
    },

    // ⬇️ Download the visible table (Top N, selected year vs prev year)
    downloadVisibleCSV() {
      if (!this.tableRows.length) return;
      const header = ["Make", `${this.prevYear}`, `${this.selectedYear}`, "YoY %"];
      const rows = this.tableRows.map((r) => ([
        r.make,
        Number.isFinite(r.previousYear) ? r.previousYear : "",
        Number.isFinite(r.currentYear) ? r.currentYear : "",
        Number.isFinite(r.yoy) ? r.yoy : "",
      ].map((c) => `"${String(c).replace(/"/g, '""')}"`).join(",")));

      const csv = [header.join(","), ...rows].join("\n");
      const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `make_growth_yoy_top${this.topN}_${this.prevYear}-${this.selectedYear}.csv`;
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

.info-icon {
  background: transparent;
  border: none;
  color: #595959;
  cursor: pointer;
  font-size: 14px;
  padding: 2px 4px;
  border-radius: 50%;
  transition: all 0.2s;
}
.info-icon:hover {
  background: #f5f5f5;
  color: #1677ff;
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


.chip {
  display: inline-block;
  padding: 1px 4px;
  border-radius: 3px;
  color: #fff;
  font-size: 11px;
  font-weight: 500;
  margin-right: 2px;
}
.chip-green { background: rgba(88, 214, 141, 0.9); }
.chip-blue { background: rgba(46, 134, 193, 0.9); }
.chip-yellow { background: rgba(244, 208, 63, 0.9); color: #333; }
.chip-orange { background: rgba(230, 126, 34, 0.9); }
.chip-red { background: rgba(231, 76, 60, 0.9); }
</style>