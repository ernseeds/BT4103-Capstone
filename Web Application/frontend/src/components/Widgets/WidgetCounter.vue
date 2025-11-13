<template>
	<a-card :bordered="false" class="widget-1">
	  <a-statistic
		:title="title"
		:value="value"
		:prefix="prefix"
		:suffix="suffix"
		:precision="0"
		class="text-success"
		:class="'text-' + status"
	  />
	  <div class="icon">
		<img v-if="isImg" :src="icon" alt="" class="icon-img" />
		<span v-else v-html="icon" />
	  </div>
	</a-card>
  </template>
  
  <script>
  export default {
	props: {
	  title: String,
	  value: { type: [Number, String], default: 0 },
	  prefix: String,
	  suffix: String,
	  icon: { type: String, default: "" }, // can be URL or inline SVG string
	  status: { type: String, default: "success" },
	},
	computed: {
	  isImg() {
		return /\.(png|jpe?g|gif|svg|webp)$/i.test(this.icon) || this.icon.startsWith("/");
	  },
	},
  };
  </script>
  
  <style scoped>
  .icon { display: flex; align-items: center; }
  .icon-img { width: 24px; height: 24px; object-fit: contain; }
  </style>
  