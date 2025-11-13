<template>
  <div class="brand-cards-column">
    <!-- Cheapest Brands Card -->
    <a-card
      title="Top 5 Cheapest Brands by Average Price"
      :bordered="false"
      class="brand-card shadow-md rounded-lg"
    >
      <ul class="brand-list">
        <li
          v-for="brand in cheapestBrands.slice(0, 5)"
          :key="'cheapest-' + brand.brand"
          class="brand-row"
        >
          <span class="brand-name">{{ brand.brand }}</span>
          <span class="brand-price">
            S${{ Math.round(brand.avgPrice).toLocaleString() }}
          </span>
        </li>
      </ul>
    </a-card>

    <!-- Most Expensive Brands Card -->
    <a-card
      title="Top 5 Most Expensive Brands by Average Price"
      :bordered="false"
      class="brand-card shadow-md rounded-lg"
    >
      <ul class="brand-list">
        <li
          v-for="brand in expensiveBrands.slice(0, 5)"
          :key="'expensive-' + brand.brand"
          class="brand-row"
        >
          <span class="brand-name">{{ brand.brand }}</span>
          <span class="brand-price">
            S${{ Math.round(brand.avgPrice).toLocaleString() }}
          </span>
        </li>
      </ul>
    </a-card>
  </div>
</template>

<script>
export default {
  name: "BrandPriceCharts",
  props: {
    // parent dashboard should do :rows="previewRows"
    rows: {
      type: Array,
      default: () => [],
    },
  },
  data() {
    return {
      cheapestBrands: [],
      expensiveBrands: [],
    };
  },
  watch: {
    // whenever API data changes, recompute
    rows: {
      handler(newVal) {
        this.computeFromRows(newVal || []);
      },
      deep: true,
    },
  },
  mounted() {
    this.computeFromRows(this.rows || []);
  },
  methods: {
    toNumber(v) {
      if (typeof v === "number") return v;
      if (v == null || v === "") return NaN;
      return parseFloat(String(v).replace(/[^0-9.\-]/g, ""));
    },
    computeFromRows(data) {
      const brandMap = {};

      for (const row of data) {
        const brand = (row.Brand || row.brand || "").trim();
        if (!brand) continue;

        const price = this.toNumber(row.Price ?? row.price);
        if (!isFinite(price)) continue;

        if (!brandMap[brand]) brandMap[brand] = [];
        brandMap[brand].push(price);
      }

      // turn into array of { brand, avgPrice }
      const brandAvgPrices = Object.entries(brandMap).map(([brand, prices]) => ({
        brand,
        avgPrice: prices.reduce((a, b) => a + b, 0) / prices.length,
      }));

      // sort two ways
      this.cheapestBrands = [...brandAvgPrices].sort((a, b) => a.avgPrice - b.avgPrice);
      this.expensiveBrands = [...brandAvgPrices].sort((a, b) => b.avgPrice - a.avgPrice);
    },
  },
};
</script>

<style scoped>
.brand-cards-column {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.brand-card {
  width: 100%;
}

.brand-list {
  list-style: none;
  padding: 0;
  margin: 0;
}

.brand-row {
  display: flex;
  justify-content: space-between;
  padding: 0.5rem 0;
}

.brand-name {
  text-align: left;
  font-weight: 500;
}

.brand-price {
  text-align: right;
  font-weight: 600;
}
</style>
