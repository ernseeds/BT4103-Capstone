<!-- 
	This is the dashboard page, it uses the dashboard layout in: 
	"./layouts/Dashboard.vue" .
 -->

<template>
	<div>
		<!-- Counter Widgets -->
		<a-row :gutter="24">
			<a-col :span="24" :lg="12" :xl="6" class="mb-24" v-for="(stat, index) in stats" :key="index">
				<!-- Widget 1 Card -->
				<WidgetCounter
					:title="stat.title"
					:value="stat.value"
					:prefix="stat.prefix"
					:suffix="stat.suffix"
					:icon="stat.icon"
					:status="stat.status"
				></WidgetCounter>
				<!-- / Widget 1 Card -->
			</a-col>
		</a-row>
		<!-- / Counter Widgets -->

		<!-- Charts -->
		 <!-- COE Chart Row -->
		<!-- <a-row :gutter="24" type="flex" align="stretch">
		<a-col :span="24" :lg="44" class="mb-24">
			<a-card>
			<div class="iframe-container">
				<iframe
				width="1085"
				height="600"
				src="https://data.gov.sg/datasets/d_69b3380ad7e51aff3a7dcc84eba52b8a/chart/1356"
				frameborder="0"
				allowfullscreen
				></iframe>
			</div>
			</a-card>
		</a-col>
		</a-row> -->

		<a-row :gutter="24" type="flex" align="stretch">
			<a-col :span="34" :lg="16" class="mb-24">
				<PriceAgeCatChart />
			</a-col>
			<a-col :span="24" :lg="8
		" class="mb-24">
				<BrandPriceCharts />
			</a-col>
		</a-row>

		<!-- <a-row :gutter="24" type="flex" align="stretch">
		<a-col :span="24" :lg="34" class="mb-24">
			<a-card>
			<div class="iframe-container">
				<iframe
				width="1085"
				height="600"
				src="https://data.gov.sg/datasets/d_ab595ec8b7cbcb7a40d49e5435c2f78a/chart/1102"
				frameborder="0"
				>
				</iframe>
			</div>
			</a-card>
		</a-col>
		</a-row> -->

		<a-row :gutter="24" type="flex" align="stretch">
		<a-col :span="24" :lg="24" class="mb-24">
			<PriceAgeBrandChart />
		</a-col>
		</a-row>

		<a-row :gutter="24" type="flex" align="stretch">
		<a-col :span="24" :lg="24" class="mb-24">
			<PieChart />
		</a-col>
		</a-row>


	</div>
</template>

<script>
	import PriceAgeCatChart from "../components/Charts/PriceAgeCat.vue";
	import PriceAgeBrandChart from "../components/Charts/PriceAgeBrand.vue";
	import BrandPriceCharts from "../components/Charts/Top5CheapestBrands.vue";
	import PieChart from "../components/Charts/PieChart.vue";

	// Line chart for COE Premium card.
	import COEChart from '../components/Charts/COEChart.vue';

	// Line chart for COE vs Income trend.
	import COEIncomeChart from '../components/Charts/COEIncomeChart.vue';

	// Stacked Bar chart for Quota Bids card.
	import QuotaBidsChart from '../components/Charts/QuotaBidsChart.vue';

	// Stacked Bar chart for Effective transfer of car ownership by make card.
	import OwnershipByMakeChart from '../components/Charts/OwnershipByMakeChart.vue';

	// Counter Widgets
	import WidgetCounter from '../components/Widgets/WidgetCounter' ;

	// Counter Widgets stats
	const stats = [
  { title: "Active Listings", value: 1842, suffix: "", icon: `<svg/>` },
  { title: "Avg Price (SGD)", value: 685000, prefix: "$" },
] ;



	export default {
		components: {
			PriceAgeCatChart,
			PriceAgeBrandChart,
			WidgetCounter,
			COEChart,
			QuotaBidsChart,
			OwnershipByMakeChart,
			COEIncomeChart,
			BrandPriceCharts,
			PieChart,
		},
		data() {
			return {
				// Counter Widgets Stats
				stats,
			}
		},
	}

</script>

<style lang="scss">
</style>