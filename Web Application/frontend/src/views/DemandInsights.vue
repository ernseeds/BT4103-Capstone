<template>
	<div>
		<DataChatbot />
		
		<!-- Category Filter -->
		<div class="filter-container">
			<a-select 
				v-model="selectedCategory" 
				@change="onCategoryChange"
				placeholder="Filter by Category"
				style="width: 200px"
			>
				<a-select-option value="all">All Categories</a-select-option>
				<a-select-option value="Category A">Category A</a-select-option>
				<a-select-option value="Category B">Category B</a-select-option>
			</a-select>
		</div>

		<a-row :gutter="24" type="flex" align="stretch">
			<a-col :span="24" :lg="24" class="mb-24">
				<COECards :rows="filteredCoeRows" @loaded="onChildLoaded" />
			</a-col>
		</a-row>

		<!-- loading bar -->
		<div v-if="previewLoading" class="loading-strip">
			<div class="loading-strip__inner"></div>
		</div>

		<!-- error -->
		<div v-if="previewError" class="mb-24">{{ previewError }}</div>


		<a-row :gutter="24" type="flex" align="stretch">
			<a-col :span="24" :lg="16" class="mb-24">
				<COEChart :rows="coeRows" :selectedCategory="selectedCategory" @loaded="onChildLoaded" />
			</a-col>
			<a-col :span="24" :lg="8" class="mb-24">
				<COEGrowthChart :rows="coeRows" :selectedCategory="selectedCategory" @loaded="onChildLoaded" />
			</a-col>
		</a-row>

		<a-row :gutter="24" type="flex" align="stretch">
			<a-col :span="24" :lg="8" class="mb-24">
				<COESuccessRateTable :rows="coeRows" :selectedCategory="selectedCategory" @loaded="onChildLoaded" />
			</a-col>
			<a-col :span="24" :lg="16" class="mb-24">
				<QuotaBidsChart :rows="coeRows" :selectedCategory="selectedCategory" @loaded="onChildLoaded" />
			</a-col>
		</a-row>

		<a-row :gutter="24" type="flex" align="stretch">
			<a-col :span="24" :lg="24" class="mb-24">
				<CatACOEPrediction :rows="coeRows" @loaded="onChildLoaded" />
			</a-col>
		</a-row>

		<a-row :gutter="24" type="flex" align="stretch">
			<a-col :span="24" :lg="24" class="mb-24">
				<CatBCOEPrediction :rows="coeRows" @loaded="onChildLoaded" />
			</a-col>
		</a-row>

		<a-row :gutter="24" type="flex" align="stretch">
			<a-col :span="24" :lg="16" class="mb-24">
				<TopMakesOverTime @loaded="onChildLoaded" />
			</a-col>
			<a-col :span="24" :lg="8" class="mb-24">
				<MarketShareByMake @loaded="onChildLoaded" />
			</a-col>
		</a-row>

		<a-row :gutter="24" type="flex" align="stretch">
			<a-col :span="24" :lg="12" class="mb-24">
				<MakeGrowthChart @loaded="onChildLoaded" />
			</a-col>
			<a-col :span="24" :lg="12" class="mb-24">

				<!-- OwnershipByMake -->
				<OwnershipByMakeChart @loaded="onChildLoaded" />
				<!-- OwnershipByMake -->

			</a-col>
		</a-row>


	</div>
</template>

<script>
import COECards from '../components/Cards/COECards' ;

import DataChatbot from '../components/Chatbot/DataChatbot.vue';

import COEGrowthChart from '../components/Charts/COEGrowthRate.vue';

import COESuccessRateTable from '../components/Charts/BidsSuccessRate.vue';

import TopMakesOverTime from '../components/Charts/TopMakesOverTime.vue';

import MarketShareByMake from '../components/Charts/MarketShareByMake.vue';

import MakeGrowthChart from '../components/Charts/MakeGrowthChart.vue';

import CatACOEPrediction from '../components/Charts/CatACOEPrediction.vue';

import CatBCOEPrediction from '../components/Charts/CatBCOEPrediction.vue';

// Line chart for COE Premium card.
import COEChart from '../components/Charts/COEChart.vue';

// Stacked Bar chart for Quota Bids card.
import QuotaBidsChart from '../components/Charts/QuotaBidsChart.vue';

// Stacked Bar chart for Effective transfer of car ownership by make card.
import OwnershipByMakeChart from '../components/Charts/OwnershipByMakeChart.vue';

const API_BASE =
  process.env.VUE_APP_API_BASE ||
  (typeof window !== "undefined" ? window.API_BASE : null) ||
  "http://localhost:8000";

export default {
  name: "DemandInsights",
	components: {
		DataChatbot,
		COECards,
		COEGrowthChart,
		COESuccessRateTable,
		TopMakesOverTime,
		MarketShareByMake,
		MakeGrowthChart,
		CatACOEPrediction,
		CatBCOEPrediction,
		COEChart,
		QuotaBidsChart,
		OwnershipByMakeChart,
  },
  data() {
    return {
      previewLoading: true,
      loadedCount: 0,
      expectedChildren: 11,
      coeRows: [],
      coeError: null,
      previewError: '',
      selectedCategory: 'all',
    };
  },
  computed: {
    filteredCoeRows() {
      if (this.selectedCategory === 'all') {
        return this.coeRows;
      }
      return this.coeRows.filter(row => row.Vehicle_Class === this.selectedCategory);
    }
  },
  created() {
    this.loadCOEData();
  },
  methods: {
    async loadCOEData() {
      try {
        const res = await fetch(`${API_BASE}/fetch_coe_gcs`);
        const json = await res.json();
        this.coeRows = json.rows || json || [];
      } catch (err) {
        this.coeError = "Failed to load COE data";
        console.error(err);
      }
    },
    onChildLoaded(name) {
      this.loadedCount += 1;
      if (this.loadedCount >= this.expectedChildren) {
        this.previewLoading = false;
      }
    },
    onCategoryChange(value) {
      this.selectedCategory = value;
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
  0% { left: -30%; }
  100% { left: 100%; }
}

.filter-container {
  position: absolute;
  top: 40px;
  right: 20px;
  z-index: 100;
}
</style>