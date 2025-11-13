<template>
    <a-card
      title="Average Listing Price vs Vehicle Age — by Brand"
      :bordered="false"
      class="h-full shadow-md rounded-lg"
    >
      <template #extra>
        <div class="flex items-center gap-3">
          <span>Category:</span>
          <a-select v-model="category" style="width: 120px">
            <a-select-option value="ALL">All</a-select-option>
            <a-select-option value="A">Cat A</a-select-option>
            <a-select-option value="B">Cat B</a-select-option>
          </a-select>
  
          <span class="ml-3">Top Brands:</span>
          <a-input-number v-model="topN" :min="1" :max="20" style="width: 90px" />
        </div>
      </template>
  
      <div style="height:400px;">
        <canvas ref="chartEl"></canvas>
      </div>
    </a-card>
  </template>
  
  <script>
  import { Chart, registerables } from "chart.js";
  import Papa from "papaparse";
  
  Chart.register(...registerables);
  
  export default {
    name: "PriceAgeBrand",
    data() {
      return {
        chart: null,
        rawRows: [],
        category: "ALL", // ALL | A | B
        topN: 8,
      };
    },
    watch: {
      category() {
        this.recomputeAndRender();
      },
      topN() {
        this.recomputeAndRender();
      },
    },
    methods: {
      // --- helpers ---
      toNumber(v) {
        if (typeof v === "number") return v;
        if (v == null) return NaN;
        return parseFloat(String(v).replace(/[^0-9.]/g, ""));
      },
      parseDate(d) {
        if (!d) return null;
        const t = new Date(d);
        return isNaN(t) ? null : t;
      },
      ageYearsFrom(regDate) {
        if (!regDate) return NaN;
        const now = new Date();
        const diffMs = now - regDate;
        return diffMs / (365.25 * 24 * 3600 * 1000);
      },
      bucketAge(age) {
        return Math.floor(age); // change to 0.5 bins if you like
      },
      average(arr) {
        return arr.length ? arr.reduce((a, b) => a + b, 0) / arr.length : null;
      },
      palette(i) {
        // a simple deterministic palette
        const colors = [
          "#1f77b4","#ff7f0e","#2ca02c","#d62728","#9467bd",
          "#8c564b","#e377c2","#7f7f7f","#bcbd22","#17becf",
          "#4e79a7","#f28e2b","#e15759","#76b7b2","#59a14f",
          "#edc948","#b07aa1","#ff9da7","#9c755f","#bab0ab",
        ];
        return colors[i % colors.length];
      },
  
      // --- data loading ---
      async loadCsv() {
        const url = (process.env.BASE_URL || "/") + "data/v2_combined_datasets.csv";
        const csvText = await fetch(url).then((r) => r.text());
        const { data: rows } = Papa.parse(csvText, {
          header: true,
          skipEmptyLines: true,
        });
  
        // normalize now; keep only rows that have price & age (or computable age)
        this.rawRows = rows
          .map((r) => {
            const brand = (r.Brand || "").toString().trim();
            const cat = (r.COE_Category || "").toString().trim().toUpperCase();
            const price = this.toNumber(r.Price);
            let age = this.toNumber(r.Vehicle_Age_Years);
  
            if (!isFinite(age) || age <= 0) {
              const reg = this.parseDate(r.Registration_Date);
              age = this.ageYearsFrom(reg);
            }
            return { brand, cat, price, age };
          })
          .filter(
            (x) =>
              x.brand &&
              isFinite(x.price) &&
              isFinite(x.age) &&
              x.age >= 0 &&
              (x.cat === "A" || x.cat === "B" || x.cat === "")
          );
  
        this.recomputeAndRender();
      },
  
      // --- compute & render ---
      recomputeAndRender() {
        if (!this.rawRows.length) return;
  
        // filter by category
        const rows =
          this.category === "ALL"
            ? this.rawRows.filter((r) => r.cat === "A" || r.cat === "B")
            : this.rawRows.filter((r) => r.cat === this.category);
  
        if (!rows.length) {
          this.render([], []); // nothing to show
          return;
        }
  
        // count brands (post-filter) and select top N by listing count
        const counts = {};
        for (const r of rows) counts[r.brand] = (counts[r.brand] || 0) + 1;
        const topBrands = Object.entries(counts)
          .sort((a, b) => b[1] - a[1])
          .slice(0, this.topN)
          .map(([brand]) => brand);
  
        const filtered = rows.filter((r) => topBrands.includes(r.brand));
  
        // group: brand -> ageBucket -> [prices]
        const brandBuckets = {};
        for (const r of filtered) {
          const bin = this.bucketAge(r.age);
          if (!brandBuckets[r.brand]) brandBuckets[r.brand] = {};
          if (!brandBuckets[r.brand][bin]) brandBuckets[r.brand][bin] = [];
          brandBuckets[r.brand][bin].push(r.price);
        }
  
        // unified label set (ages present in any brand)
        const ageSet = new Set();
        Object.values(brandBuckets).forEach((bucketObj) => {
          Object.keys(bucketObj).forEach((k) => ageSet.add(Number(k)));
        });
        const labels = Array.from(ageSet).sort((a, b) => a - b);
  
        // datasets per brand
        const datasets = topBrands.map((brand, idx) => {
          const series = labels.map((age) => this.average(brandBuckets[brand][age] || []));
          return {
            label: brand,
            data: series,
            borderColor: this.palette(idx),
            pointRadius: 1.5,
            fill: false,
            tension: 0.25,
            borderWidth: 2,
            spanGaps: true,
          };
        });
  
        this.render(labels, datasets);
      },
  
      render(labels, datasets) {
        if (this.chart) this.chart.destroy();
        const ctx = this.$refs.chartEl.getContext("2d");
  
        this.chart = new Chart(ctx, {
          type: "line",
          data: { labels, datasets },
          options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
              legend: {
                position: "bottom",
                labels: { usePointStyle: true, pointStyle: "line", boxWidth: 18 },
              },
              tooltip: {
                mode: "nearest",
                intersect: false,
                callbacks: {
                  title: (items) => `Age: ${items[0].label} yrs`,
                  label: (ctx) =>
                    `${ctx.dataset.label}: S$${Number(ctx.parsed.y ?? 0).toLocaleString(undefined, {
                      maximumFractionDigits: 0,
                    })}`,
                },
              },
            },
            interaction: { mode: "nearest", axis: "x", intersect: false },
            scales: {
              x: {
                type: "linear",
                title: { display: true, text: "Vehicle Age (years)" },
                ticks: { stepSize: 1 },
                grid: { display: false },
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
      this.loadCsv().catch((e) => console.error("PriceAgeBrand error:", e));
    },
  };
  </script>
  
  <style scoped>
  /* optional tiny utility if you don’t already use Tailwind */
  .flex { display: flex; }
  .items-center { align-items: center; }
  .gap-3 { gap: 0.75rem; }
  .ml-3 { margin-left: 0.75rem; }
  </style>
  