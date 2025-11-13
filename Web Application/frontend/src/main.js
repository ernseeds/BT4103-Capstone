import Vue from "vue";
import Antd from "ant-design-vue";
import "ant-design-vue/dist/antd.css";
import App from "./App.vue";
import DashboardLayout from "./layouts/Dashboard.vue";
import router from "./router";
// import './plugins/click-away'

import "./scss/app.scss";

Vue.use(Antd);

Vue.config.productionTip = false;
Vue.config.silent = true; // Suppress Vue warnings in production

// Adding template layouts to the vue components.
Vue.component("layout-dashboard", DashboardLayout);

new Vue({
  router,
  render: (h) => h(App),
}).$mount("#app");
