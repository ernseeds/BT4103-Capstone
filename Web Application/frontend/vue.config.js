module.exports = {
  runtimeCompiler: true,
  transpileDependencies: ["chartjs-chart-matrix", "chart.js"],
  configureWebpack: {
    resolve: {
      alias: {
        "chartjs-chart-matrix$":
          "chartjs-chart-matrix/dist/chartjs-chart-matrix.umd.js",
      },
    },
  },
  chainWebpack: (config) => {
    config.plugin("html").tap((args) => {
      args[0].title = "Landscanner";
      return args;
    });
  },
};
