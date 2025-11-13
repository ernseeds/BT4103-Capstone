<template>
  <div class="metrics-container">  <!-- SINGLE ROOT WRAPPER -->
    <a-card class="metric-card" :bordered="false">
      <div class="card-content">
        <div class="metric-label-row">
          <div class="metric-label">Average Premium (Last Quarter)</div>
          <a-tooltip
            placement="topRight"
            :mouse-enter-delay="0.2"
            :overlay-style="{ maxWidth: '260px', whiteSpace: 'normal' }"
            title="Mean of winning bids across Cat A & B in the last 3 calendar months."
          >
            <!-- <InfoCircleOutlined class="info-icon" /> -->
          </a-tooltip>
        </div>

        <div class="value-row">
          <div class="metric-value">S${{ avgPremium.toLocaleString() }}</div>
          <div class="right-indicator">
            <div class="change-value" :class="avgPremiumChange >= 0 ? 'positive' : 'negative'">
              {{ avgPremiumChange >= 0 ? '+' : '' }}{{ avgPremiumChange.toFixed(1) }}%
            </div>
            <div class="change-label">vs prev quarter</div>
          </div>
        </div>
      </div>
    </a-card>

    <a-card class="metric-card" :bordered="false">
      <div class="card-content">
        <div class="metric-label-row">
          <div class="metric-label">COE Growth Rate (Last Quarter)</div>
          <a-tooltip
            placement="topRight"
            :mouse-enter-delay="0.2"
            :overlay-style="{ maxWidth: '260px', whiteSpace: 'normal' }"
            title="Percent change of average premium vs 3 months ago. Delta vs last quarter shown in pp (percentage points)."
          >
            <!-- <InfoCircleOutlined class="info-icon" /> -->
          </a-tooltip>
        </div>

        <div class="value-row">
          <div class="metric-value">{{ growthRate.toFixed(1) }}%</div>
          <div class="right-indicator">
            <div class="change-value" :class="growthRateChange >= 0 ? 'positive' : 'negative'">
              {{ growthRateChange >= 0 ? '+' : '' }}{{ growthRateChange.toFixed(1) }}pp
            </div>
            <div class="change-label">vs prev quarter</div>
          </div>
        </div>
      </div>
    </a-card>

    <a-card class="metric-card" :bordered="false">
      <div class="card-content">
        <div class="metric-label-row">
          <div class="metric-label">Maximum Premium (Current Year)</div>
          <a-tooltip
            placement="topRight"
            :mouse-enter-delay="0.2"
            :overlay-style="{ maxWidth: '260px', whiteSpace: 'normal' }"
            title="Highest winning premium observed this calendar year (Cat A & B combined)."
          >
            <!-- <InfoCircleOutlined class="info-icon" /> -->
          </a-tooltip>
        </div>

        <div class="value-row">
          <div class="metric-value">S${{ maxPremium.toLocaleString() }}</div>
          <div class="right-indicator">
            <div class="change-value" :class="maxPremiumChange >= 0 ? 'positive' : 'negative'">
              {{ maxPremiumChange >= 0 ? '+' : '' }}{{ maxPremiumChange.toFixed(1) }}%
            </div>
            <div class="change-label">vs last year</div>
          </div>
        </div>
      </div>
    </a-card>

    <a-card class="metric-card" :bordered="false">
      <div class="card-content">
        <div class="metric-label-row">
          <div class="metric-label">Minimum Premium (Current Year)</div>
          <a-tooltip
            placement="topRight"
            :mouse-enter-delay="0.2"
            :overlay-style="{ maxWidth: '260px', whiteSpace: 'normal' }"
            title="Lowest winning premium observed this calendar year (Cat A & B combined)."
          >
            <!-- <InfoCircleOutlined class="info-icon" /> -->
          </a-tooltip>
        </div>

        <div class="value-row">
          <div class="metric-value">S${{ minPremium.toLocaleString() }}</div>
          <div class="right-indicator">
            <div class="change-value" :class="minPremiumChange >= 0 ? 'positive' : 'negative'">
              {{ minPremiumChange >= 0 ? '+' : '' }}{{ minPremiumChange.toFixed(1) }}%
            </div>
            <div class="change-label">vs last year</div>
          </div>
        </div>
      </div>
    </a-card>
  </div>
</template>

<script>
import dayjs from "dayjs";

export default {
  name: "COEMetricsFullWidth",
  props: {
    rows: {
      type: Array,
      default: () => [],
    },
  },
  data() {
    return {
      carClasses: ["Category A", "Category B"],
      avgPremium: 0,
      avgPremiumChange: 0,
      growthRate: 0,
      growthRateChange: 0,
      maxPremium: 0,
      maxPremiumChange: 0,
      minPremium: 0,
      minPremiumChange: 0,
      firstRendered: false,
    };
  },
  watch: {
    rows: {
      immediate: true,
      handler(newVal) {
        if (Array.isArray(newVal) && newVal.length) {
          this.computeMetrics(newVal);
        } else if (!this.firstRendered) {
          this.$emit("loaded", "COECards");
          this.firstRendered = true;
        }
      },
    },
  },
  methods: {
    computeMetrics(recordsRaw) {
      let records = recordsRaw.filter(
        (r) =>
          r.Premium != null &&
          r.Premium !== "" &&
          !isNaN(parseFloat(r.Premium))
      );

      const catA = records.filter((r) => r.Vehicle_Class === "Category A");
      const catB = records.filter((r) => r.Vehicle_Class === "Category B");

      const parseData = (data) =>
        data
          .map((r) => ({
            date: dayjs(r.Bidding_Date, "YYYY-MM-DD"),
            premium: parseFloat(r.Premium),
          }))
          .filter((d) => !isNaN(d.premium))
          .sort((a, b) => a.date - b.date);

      const dataA = parseData(catA);
      const dataB = parseData(catB);

      const dateMap = new Map();
      [...dataA, ...dataB].forEach((item) => {
        const dateStr = item.date.format("YYYY-MM-DD");
        if (!dateMap.has(dateStr)) {
          dateMap.set(dateStr, { date: item.date, premiums: [] });
        }
        dateMap.get(dateStr).premiums.push(item.premium);
      });

      const combinedData = Array.from(dateMap.values())
        .map((item) => ({
          date: item.date,
          avgPremium:
            item.premiums.reduce((sum, p) => sum + p, 0) /
            item.premiums.length,
        }))
        .sort((a, b) => a.date - b.date);

      if (combinedData.length === 0) {
        if (!this.firstRendered) {
          this.$emit("loaded", "COECards");
          this.firstRendered = true;
        }
        return;
      }

      // === your existing metric logic ===
      const threeMonthsAgo = dayjs().subtract(3, "months");
      const sixMonthsAgo = dayjs().subtract(6, "months");
      const lastQuarterData = combinedData.filter((d) =>
        d.date.isAfter(threeMonthsAgo)
      );
      const prevQuarterData = combinedData.filter(
        (d) => d.date.isAfter(sixMonthsAgo) && d.date.isBefore(threeMonthsAgo)
      );

      if (lastQuarterData.length > 0) {
        const premiumsLastQuarter = lastQuarterData.map((d) => d.avgPremium);
        this.avgPremium = Math.round(
          premiumsLastQuarter.reduce((sum, p) => sum + p, 0) /
            premiumsLastQuarter.length
        );

        if (prevQuarterData.length > 0) {
          const premiumsPrevQuarter = prevQuarterData.map((d) => d.avgPremium);
          const prevAvg =
            premiumsPrevQuarter.reduce((sum, p) => sum + p, 0) /
            premiumsPrevQuarter.length;
          this.avgPremiumChange =
            ((this.avgPremium - prevAvg) / prevAvg) * 100;
        }
      }

      const mostRecentData = combinedData[combinedData.length - 1];
      const threeMonthsAgoDate = dayjs().subtract(3, "months");
      const sixMonthsAgoDate = dayjs().subtract(6, "months");

      const threeMonthsAgoData = combinedData.reduce((closest, current) => {
        const currentDiff = Math.abs(
          current.date.diff(threeMonthsAgoDate, "day")
        );
        const closestDiff = Math.abs(
          closest.date.diff(threeMonthsAgoDate, "day")
        );
        return currentDiff < closestDiff ? current : closest;
      });

      const sixMonthsAgoData = combinedData.reduce((closest, current) => {
        const currentDiff = Math.abs(
          current.date.diff(sixMonthsAgoDate, "day")
        );
        const closestDiff = Math.abs(
          closest.date.diff(sixMonthsAgoDate, "day")
        );
        return currentDiff < closestDiff ? current : closest;
      });

      if (mostRecentData && threeMonthsAgoData) {
        const recentPremium = mostRecentData.avgPremium;
        const oldPremium = threeMonthsAgoData.avgPremium;
        this.growthRate = ((recentPremium - oldPremium) / oldPremium) * 100;

        if (sixMonthsAgoData && threeMonthsAgoData) {
          const prevQuarterGrowth =
            ((threeMonthsAgoData.avgPremium - sixMonthsAgoData.avgPremium) /
              sixMonthsAgoData.avgPremium) *
            100;
          this.growthRateChange = this.growthRate - prevQuarterGrowth;
        }
      }

      const currentYear = dayjs().year();
      const lastYear = currentYear - 1;

      const allPremiumsThisYear = [
        ...dataA.filter((d) => d.date.year() === currentYear).map((d) => d.premium),
        ...dataB.filter((d) => d.date.year() === currentYear).map((d) => d.premium),
      ];

      const allPremiumsLastYear = [
        ...dataA.filter((d) => d.date.year() === lastYear).map((d) => d.premium),
        ...dataB.filter((d) => d.date.year() === lastYear).map((d) => d.premium),
      ];

      if (allPremiumsThisYear.length > 0) {
        this.maxPremium = Math.round(Math.max(...allPremiumsThisYear));
        this.minPremium = Math.round(Math.min(...allPremiumsThisYear));

        if (allPremiumsLastYear.length > 0) {
          const lastYearMax = Math.max(...allPremiumsLastYear);
          const lastYearMin = Math.min(...allPremiumsLastYear);
          this.maxPremiumChange =
            ((this.maxPremium - lastYearMax) / lastYearMax) * 100;
          this.minPremiumChange =
            ((this.minPremium - lastYearMin) / lastYearMin) * 100;
        }
      }

      // tell parent this child is done — but only once
      if (!this.firstRendered) {
        this.$emit("loaded", "COECards");
        this.firstRendered = true;
      }
    },
  },
};
</script>

<style scoped>
.metrics-container {
  display: flex;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 1rem;
  /* margin-bottom: 0rem; */
}

.metric-card {
  flex: 1 1 22%;
  min-width: 200px;
  height: 110px;
}

.card-content {
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  height: 100%;
  padding: 0.3rem 0;
}

.metric-label-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 0.6rem; /* tighter than 0.6rem */
}

.info-icon {
  font-size: 14px;
  color: #bfbfbf;
  cursor: pointer;
}
.info-icon:hover {
  color: #8c8c8c;
}

.metric-label {
  font-size: 0.85rem;
  color: #8c8c8c;
  font-weight: 600;
  width: 100%;
}

.value-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
}

.metric-value {
  font-weight: 700;
  font-size: 1.8rem;
  color: #262626;
  line-height: 1;
}

.right-indicator {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: -0.1rem;
}

.change-value {
  font-size: 0.85rem;
  font-weight: 600;
  line-height: 1;
}

.change-value.positive { color: #52c41a; }
.change-value.negative { color: #f5222d; }

.change-label {
  font-size: 0.7rem;
  color: #bfbfbf;
  white-space: nowrap;
}
</style>
