<template>
  <a-card
    :title="shortTitle"
    :bordered="false"
    class="h-full shadow-md rounded-lg price-scatter-card"
  >
    <template #extra>
      <div class="controls-row">
        <span class="ctrl-label">X-axis:</span>
        <select
          v-model="xField"
          class="ctrl-select"
          @change="renderScatter"
        >
          <option
            v-for="opt in xOptions"
            :key="opt.value"
            :value="opt.value"
          >
            {{ opt.label }}
          </option>
        </select>

        <span class="ctrl-label">COE:</span>
        <select
          v-model="category"
          class="ctrl-select"
          @change="renderScatter"
        >
          <option value="ALL">Cat A & B</option>
          <option value="A">Cat A</option>
          <option value="B">Cat B</option>
        </select>

        <span class="ctrl-label">Fuel:</span>
        <select
          v-model="fuelFilter"
          class="ctrl-select"
          @change="renderScatter"
        >
          <option value="ALL">All</option>
          <option
            v-for="f in fuelOptions"
            :key="f"
            :value="f"
          >
            {{ f }}
          </option>
        </select>
      </div>
    </template>

    <div class="chart-shell">
      <canvas ref="chartEl"></canvas>
    </div>
  </a-card>
</template>

<script>
import { Chart, registerables } from "chart.js";
Chart.register(...registerables);

export default {
  name: "PriceScatter",
  props: {
    rows: {
      type: Array,
      default: () => [],
    },
  },
  data() {
    return {
      chart: null,
      localRows: [],
      xField: "Mileage_km",
      category: "ALL",
      fuelFilter: "ALL",
      fuelOptions: ["Petrol", "Diesel", "Hybrid", "Electric"],
      xOptions: [
        { value: "Mileage_km",        label: "Mileage (km)" },
        { value: "Vehicle_Age_Years", label: "Vehicle Age (years)" },
        { value: "COE",               label: "COE Paid (S$)" },
        { value: "OMV",               label: "OMV (S$)" },
        { value: "Engine_Capacity_cc",label: "Engine Capacity (cc)" },
        { value: "Horse_Power_kW",    label: "Horse Power (kW)" },
        { value: "COE_Left_Days",     label: "COE Left (days)" },
        { value: "Road_Tax_Payable",  label: "Road Tax Payable (S$)" },
      ],
    };
  },
  computed: {
    shortTitle() {
      const found = this.xOptions.find((o) => o.value === this.xField);
      const xLabel = found ? found.label : this.xField;
      return `Price vs ${xLabel} (Scatter)`;
    },
  },
  watch: {
    rows: {
      handler(newVal) {
        this.localRows = this.normalizeRows(newVal || []);
        this.renderScatter();
      },
      deep: true,
    },
  },
  methods: {
    num(v) {
      if (typeof v === "number") return v;
      if (v == null) return NaN;
      return parseFloat(String(v).replace(/[^0-9.\-]/g, ""));
    },
    parseDate(s) {
      if (!s) return null;
      const d = new Date(s);
      return isNaN(d) ? null : d;
    },
    ageYearsFrom(regDate) {
      if (!regDate) return NaN;
      const now = new Date();
      return (now - regDate) / (365.25 * 24 * 3600 * 1000);
    },
    colorByFuel(fuel) {
      const map = {
        Petrol: "#1f77b4",
        Diesel: "#ff7f0e",
        Hybrid: "#2ca02c",
        Electric: "#9467bd",
        CNG: "#d62728",
        Others: "#7f7f7f",
      };
      return map[fuel] || "#7f7f7f";
    },
    normalizeRows(raw) {
      return (raw || []).map((r) => {
        const fuel = (r.Fuel_Type || r.fuel_type || "").trim() || "Others";
        const brand = (r.Brand || r.brand || "").trim();
        const cat = (r.COE_Category || r.coe_category || "").toUpperCase().trim();
        const price = this.num(r.Price ?? r.price);

        let age = this.num(r.Vehicle_Age_Years ?? r.vehicle_age_years);
        if (!isFinite(age) || age <= 0) {
          const reg = this.parseDate(r.Registration_Date ?? r.registration_date);
          age = this.ageYearsFrom(reg);
        }

        return {
          Brand: brand,
          Fuel_Type: fuel,
          COE_Category: (cat === "A" || cat === "B") ? cat : "",
          Price: price,
          Mileage_km: this.num(r.Mileage_km ?? r.mileage_km),
          Vehicle_Age_Years: age,
          COE: this.num(r.Previous_COE),
          OMV: this.num(r.OMV),
          Engine_Capacity_cc: this.num(r.Engine_Capacity_cc ?? r.engine_capacity_cc),
          Horse_Power_kW: this.num(r.Horse_Power_kW ?? r.horse_power_kw),
          COE_Left_Days: this.num(r.COE_Left_Days ?? r.coe_left_days),
          Road_Tax_Payable: this.num(r.Road_Tax_Payable ?? r.road_tax_payable),
        };
      });
    },
    filteredRows() {
      let rows = this.localRows.filter((r) => isFinite(r.Price) && r.Price > 0);

      if (this.category !== "ALL") {
        rows = rows.filter((r) => r.COE_Category === this.category);
      } else {
        rows = rows.filter((r) => r.COE_Category === "A" || r.COE_Category === "B");
      }

      if (this.fuelFilter !== "ALL") {
        rows = rows.filter((r) => r.Fuel_Type === this.fuelFilter);
      }

      rows = rows.filter((r) => isFinite(r[this.xField]));
      return rows;
    },
    renderScatter() {
      if (!this.localRows.length) {
        if (this.chart) {
          this.chart.destroy();
          this.chart = null;
        }
        return;
      }

      const rows = this.filteredRows();
      const fuels = [...new Set(rows.map((r) => r.Fuel_Type))].slice(0, 6);
      const datasets = fuels.map((fuel) => {
        const points = rows
          .filter((r) => r.Fuel_Type === fuel)
          .map((r) => ({
            x: r[this.xField],
            y: r.Price,
            brand: r.Brand,
            cat: r.COE_Category,
          }));
        return {
          label: fuel,
          data: points,
          showLine: false,
          borderColor: this.colorByFuel(fuel),
          backgroundColor: this.colorByFuel(fuel),
          pointRadius: 3,
          pointHoverRadius: 5,
          hitRadius: 8,
        };
      });

      const xLabel =
        (this.xOptions.find((o) => o.value === this.xField) || {}).label ||
        this.xField;

      if (this.chart) this.chart.destroy();
      const ctx = this.$refs.chartEl.getContext("2d");
      this.chart = new Chart(ctx, {
        type: "scatter",
        data: { datasets },
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
              callbacks: {
                title: (items) => {
                  const p = items[0].raw;
                  return `${xLabel}: ${p.x?.toLocaleString?.() ?? p.x}`;
                },
                label: (ctx) => {
                  const p = ctx.raw;
                  const price = `Price: S$${Number(p.y).toLocaleString()}`;
                  return [
                    `Fuel: ${ctx.dataset.label}`,
                    `Brand: ${p.brand}`,
                    `Cat: ${p.cat}`,
                    price,
                  ];
                },
              },
            },
          },
          scales: {
            x: {
              title: { display: true, text: xLabel },
              grid: { display: false },
            },
            y: {
              title: { display: true, text: "Price (SGD)" },
              ticks: {
                callback: (v) => "S$" + Number(v).toLocaleString(),
              },
              grid: { color: "rgba(0,0,0,0.05)" },
            },
          },
        },
      });
    },
  },
  mounted() {
    this.localRows = this.normalizeRows(this.rows || []);
    this.renderScatter();
  },
};
</script>

<style scoped>
.price-scatter-card :deep(.ant-card-head-title) {
  font-size: 0.9rem;
  font-weight: 600;
}

.chart-shell {
  height: 420px;
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

.ctrl-select {
  height: 26px;
  background: #fff;
  border: 1px solid #e5e7eb;
  border-radius: 6px;
  font-size: 0.75rem;
  line-height: 1;
  color: #374151;
  padding: 0 8px;
  outline: none;
  min-width: 50px;
}

.ctrl-select:focus {
  border-color: #a5b4fc;
}
</style>
