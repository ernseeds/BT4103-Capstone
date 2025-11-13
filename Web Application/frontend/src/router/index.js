import Vue from "vue";
import VueRouter from "vue-router";

Vue.use(VueRouter);

let routes = [
  {
    path: "/",
    name: "Home",
    redirect: "/CarFeaturesAnalytics",
  },
  {
    path: "/CarFeaturesAnalytics",
    name: "Car Features Analytics",
    layout: "dashboard",
    component: () => import("../views/CarFeaturesAnalytics.vue"),
  },
  {
    path: "/DemandInsights",
    name: "Demand Insights",
    layout: "dashboard",
    component: () => import("../views/DemandInsights.vue"),
  },

  {
    path: "/Landscanner",
    name: "Landscanner",
    layout: "dashboard",
    meta: { layoutClass: "dashboard-rtl" },
    component: () => import("../views/Landscanner.vue"),
  },
  {
    path: "/PricePrediction",
    name: "Price Prediction",
    layout: "dashboard",
    meta: { layoutClass: "dashboard" },
    component: () => import("../views/PricePrediction.vue"),
  },

  // 404 page (explicit route)
  {
    path: "/404",
    component: () => import("../views/404.vue"),
  },
  // Catch-all MUST be last
  {
    path: "*",
    redirect: "/404",
  },
];

// propagate layout to meta
function addLayoutToRoute(route, parentLayout = "default") {
  route.meta = route.meta || {};
  route.meta.layout = route.layout || parentLayout;
  if (route.children) {
    route.children = route.children.map((c) =>
      addLayoutToRoute(c, route.meta.layout)
    );
  }
  return route;
}
routes = routes.map((r) => addLayoutToRoute(r));

const router = new VueRouter({
  mode: "history",
  base: process.env.BASE_URL,
  routes,
  scrollBehavior(to) {
    if (to.hash) return { selector: to.hash, behavior: "smooth" };
    return { x: 0, y: 0, behavior: "smooth" };
  },
});

export default router;
