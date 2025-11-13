<template>
  <div>
    <DataChatbot />
    <!-- Counter Widgets -->
    <a-row :gutter="24">
      <a-col
        v-for="(stat, index) in stats"
        :key="index"
        :span="24"
        :lg="12"
        :xl="6"
        class="mb-24"
      >
        <WidgetCounter
          :title="stat.title"
          :value="stat.value"
          :prefix="stat.prefix"
          :suffix="stat.suffix"
          :icon="stat.icon"
          :status="stat.status"
        />
      </a-col>
    </a-row>

    <!-- animated loading bar -->
    <div v-if="previewLoading" class="loading-strip">
      <div class="loading-strip__inner"></div>
    </div>

    <!-- error -->
    <div v-if="previewError" class="mb-24">{{ previewError }}</div>

    <!-- Charts row 1 -->
    <a-row v-if="!previewError" :gutter="24" type="flex" align="stretch">
      <a-col :span="24" :lg="16" class="mb-24">
        <PriceAgeCatChart class="h-full" :rows="previewRows" />
      </a-col>

      <a-col :span="24" :lg="8" class="mb-24">
        <Top5CheapestBrands class="h-full" :rows="previewRows" />
      </a-col>
    </a-row>

    <!-- Charts row 2 -->
    <a-row v-if="!previewError" :gutter="24" type="flex" align="stretch">
      <a-col :span="24" :lg="14" class="mb-24">
        <PriceScatter class="h-full" :rows="previewRows" />
      </a-col>

      <a-col :span="24" :lg="10" class="mb-24">
        <PieChart class="h-full" :rows="previewRows" />
      </a-col>
    </a-row>
  </div>
</template>

<script>
import PieChart from "../components/Charts/PieChart.vue";
import Top5CheapestBrands from "../components/Charts/Top5CheapestBrands.vue";
import DataChatbot from "../components/Chatbot/DataChatbot.vue";
import PriceScatter from "../components/Charts/PriceScatter.vue";
import PriceAgeCatChart from "../components/Charts/PriceAgeCat.vue";
import WidgetCounter from "../components/Widgets/WidgetCounter";

const API_BASE =
  process.env.VUE_APP_API_BASE ||
  (typeof window !== "undefined" ? window.API_BASE : null) ||
  "http://localhost:8000";

export default {
  components: {
    DataChatbot,
    PieChart,
    Top5CheapestBrands,
    PriceScatter,
    PriceAgeCatChart,
    WidgetCounter,
  },
  data() {
    const base = process.env.BASE_URL || "/";
    return {
      API: API_BASE,
      previewRows: [],
      previewLoading: false,
      previewError: "",
      showRow1: false,
      showRow2: false,
      // we'll overwrite stats after we fetch
      stats: [
        { title: "Active Listings", value: 0, icon: base + "images/list-icon.png" },
        { title: "Avg Price (SGD)", value: 0, prefix: "$", icon: base + "images/price-icon.png" },
        { title: "Avg COE Left (yrs)", value: 0, icon: base + "images/calendar.png" },
        { title: "Avg Vehicle Age (yrs)", value: 0, icon: base + "images/clock.png" },
      ],
    };
  },
  mounted() {
    this.fetch_dashboard_gcs();
  },
  methods: {
    toNumber(v) {
      if (typeof v === "number") return v;
      if (v == null) return NaN;
      return parseFloat(String(v).replace(/[^0-9.\-]/g, ""));
    },
    parseDate(s) {
      if (!s) return null;
      const d = new Date(s);
      return isNaN(d) ? null : d;
    },
    yearsFromDate(d) {
      if (!d) return NaN;
      const now = new Date();
      return (now - d) / (365.25 * 24 * 3600 * 1000);
    },

    async fetch_dashboard_gcs() {
      try {
        this.previewLoading = true;
        this.previewError = "";

        const res = await fetch(`${this.API}/fetch_downloaded_dashboard`);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);

        const data = await res.json();

        let rows = [];
        if (Array.isArray(data?.rows)) {
          rows = data.rows;
        } else if (Array.isArray(data)) {
          rows = data;
        } else {
          this.previewError = "Backend returned unexpected shape";
          rows = [];
        }

        this.previewRows = rows;
        this.computeStatsFromRows(rows);

        this.$nextTick(() => {
          this.showRow1 = true;
          setTimeout(() => {
            this.showRow2 = true;
          }, 120);
        });
      } catch (e) {
        console.error(e);
        this.previewError = String(e?.message || e);
        this.computeStatsFromRows([]);
      } finally {
        this.previewLoading = false;
      }
    },

    computeStatsFromRows(rows) {
      let listingCount = 0;
      let priceSum = 0;
      let coeCount = 0;
      let coeYearsSum = 0;
      let vehicleAgeSum = 0;
      let vehicleAgeCount = 0;

      for (const r of rows) {
        // keep consistent: stats based on unsold
        if (r.Sold === true) continue;

        // price
        const price = this.toNumber(r.Price);
        if (isFinite(price) && price > 0) {
          listingCount += 1;
          priceSum += price;
        }

        // COE left
        const coeLeftDays = this.toNumber(r.COE_Left_Days);
        if (isFinite(coeLeftDays) && coeLeftDays >= 0) {
          const years = coeLeftDays / 365.25;
          coeYearsSum += years;
          coeCount += 1;
        }

        // vehicle age: try direct column, else derive from Registration_Date
        let ageYears = this.toNumber(r.Vehicle_Age_Years);
        if (!isFinite(ageYears) || ageYears <= 0) {
          const reg = this.parseDate(r.Registration_Date);
          ageYears = this.yearsFromDate(reg);
        }
        if (isFinite(ageYears) && ageYears >= 0) {
          vehicleAgeSum += ageYears;
          vehicleAgeCount += 1;
        }
      }

      const avgPrice = listingCount ? priceSum / listingCount : 0;
      const avgCoEYears = coeCount ? coeYearsSum / coeCount : 0;
      const avgVehicleAge = vehicleAgeCount ? vehicleAgeSum / vehicleAgeCount : 0;
      const base = process.env.BASE_URL || "/";

      this.stats = [
        {
          title: "Active Listings",
          value: listingCount,
          icon: base + "images/list-icon.png",
        },
        {
          title: "Avg Price (SGD)",
          value: Math.round(avgPrice),
          prefix: "$",
          icon: base + "images/price-icon.png",
        },
        {
          title: "Avg COE Left (yrs)",
          value: Number(avgCoEYears.toFixed(1)),
          icon: base + "images/calendar.png",
        },
        {
          title: "Avg Vehicle Age (yrs)",
          value: Number(avgVehicleAge.toFixed(1)),
          icon: base + "images/clock.png",
        },
      ];
    },
  },
};
</script>

<style lang="scss">
.loading-strip {
  position: relative;
  width: 100%;
  height: 4px;
  background: rgba(24, 144, 255, 0.15);
  margin-bottom: 16px;
  overflow: hidden;
}
.loading-strip__inner {
  position: absolute;
  top: 0;
  left: -30%;
  width: 30%;
  height: 100%;
  background: #1890ff;
  animation: loading-move 1s linear infinite;
}
@keyframes loading-move {
  0% {
    left: -30%;
  }
  100% {
    left: 100%;
  }
}
</style>
