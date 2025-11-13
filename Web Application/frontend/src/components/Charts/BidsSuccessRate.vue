<template>
  <a-card
    title="COE Success Rate"
    :bordered="false"
    class="card-container"
  >
    <!-- Top-right filters + info + download -->
    <template #extra>
      <div class="filter-top-right">
        <span style="font-size: 0.85rem; margin-right: 0.25rem;">Category:</span>
        <select
          v-model="internalCategory"
          @change="rebuildTable"
          class="category-select"
        >
          <option value="All">All</option>
          <option value="Category A">A</option>
          <option value="Category B">B</option>
        </select>
        
        <!-- Info popover -->
        <a-popover placement="left" trigger="hover">
          <template #content>
            <div style="max-width: 280px; font-size: 12px; line-height: 1.4;">
              <strong>What this shows</strong><br />
              • <em>Success Rate</em> = (Successful Bids ÷ Total Bids) × 100%<br />
              • Shows percentage of bids that secured COE certificates<br /><br />
              <strong>Interpretation</strong><br />
              Higher success rates indicate less competition. Rates below 50% suggest high demand periods with many unsuccessful bidders.
            </div>
          </template>
          <button class="info-icon" aria-label="Success rate explanation">ⓘ</button>
        </a-popover>
        
        <!-- Download CSV -->
        <a-button
          type="text"
          class="icon-btn"
          title="Download current view as CSV"
          @click="downloadCSV"
        >
          <svg class="icon-svg" viewBox="0 0 24 24">
            <path
              d="M12 3a1 1 0 0 1 1 1v8.586l2.293-2.293a1 1 0 1 1 1.414 1.414l-4.001 4a1 1 0 0 1-1.412 0l-4.001-4a1 1 0 1 1 1.414-1.414L11 12.586V4a1 1 0 0 1 1-1zM5 19a1 1 0 1 0 0 2h14a1 1 0 1 0 0-2H5z"
              fill="currentColor"
            />
          </svg>
        </a-button>
      </div>
    </template>

    <!-- Table -->
    <div class="table-content">
      <a-table
        :columns="columns"
        :data-source="pagedData"
        :pagination="false"
        row-key="id"
        class="growth-table"
      >
        <template #bodyCell="{ column, text }">
          <template v-if="column.key === 'success_rate'">
            <span style="font-weight: 600;">
              {{ formatRate(text) }}
            </span>
          </template>
        </template>
      </a-table>
    </div>

    <!-- Sticky Footer -->
    <div class="table-footer-sticky">
      <div class="footer-left">
        <span>Show last:</span>
        <input
          type="number"
          min="1"
          v-model.number="numRounds"
          @change="rebuildTable"
          class="rounds-input"
        />
        <span>rounds</span>
      </div>

      <div class="footer-right">
        <button
          class="arrow-btn"
          :disabled="currentPage <= 1"
          @click="currentPage--"
        >
          ▲
        </button>
        <span class="page-display">Page {{ currentPage }}</span>
        <button
          class="arrow-btn"
          :disabled="currentPage >= totalPages"
          @click="currentPage++"
        >
          ▼
        </button>
      </div>
    </div>
  </a-card>
</template>

<script>
import dayjs from "dayjs";

export default {
  name: "COESuccessRateTable",
  props: {
    rows: {
      type: Array,
      default: () => [],
    },
    selectedCategory: {
      type: String,
      default: 'all',
    },
  },
  data() {
    return {
      numRounds: 5,
      internalCategory: "All",
      successData: [],
      currentPage: 1,
      pageSize: 5,
      previewLoading: false,
      previewError: "",
      firstRendered: false,     // ← add this
      columns: [
        { title: "Date", dataIndex: "date", key: "date", width: "121px" },
        { title: "Bidding Round", dataIndex: "round", key: "round", width: "33%" },
        { title: "Success Rate (%)", dataIndex: "success_rate", key: "success_rate", width: "34%" },
      ],
    };
  },
  computed: {
    totalPages() {
      return Math.ceil(this.successData.length / this.pageSize) || 1;
    },
    pagedData() {
      const start = (this.currentPage - 1) * this.pageSize;
      return this.successData.slice(start, start + this.pageSize);
    },
  },
  watch: {
    rows: {
      immediate: true,
      handler(val) {
        if (Array.isArray(val)) {
          this.rebuildTable();
        } else if (!this.firstRendered) {
          this.firstRendered = true;
        }
      },
    },
    numRounds() {
      this.currentPage = 1;
    },
    selectedCategory: {
      immediate: true,
      handler(val) {
        if (val === 'all') {
          this.internalCategory = 'All';
        } else {
          this.internalCategory = val;
        }
        this.rebuildTable();
      },
    },
  },
  methods: {
    formatRate(value) {
      const num = Number(typeof value === "string" ? value.replace("%", "") : value);
      if (!isFinite(num)) return String(value);
      return `${num.toFixed(2)}%`;
    },
    getBiddingRound(dateString) {
      const day = parseInt(dateString.split("-")[2]);
      return day <= 14 ? 1 : 2;
    },
    toNumberMaybe(x) {
      if (x == null) return 0;
      if (typeof x === "number") return x;
      const s = String(x).replace(/,/g, "").trim();
      const n = parseFloat(s);
      return isNaN(n) ? 0 : n;
    },
    rebuildTable() {
      try {
        this.previewLoading = true;
        this.previewError = "";

        if (!Array.isArray(this.rows) || this.rows.length === 0) {
          this.successData = [];
          return;
        }

        // base cleaning
        let records = this.rows.filter(
          (r) =>
            r.Premium != null &&
            r.Premium !== "" &&
            !isNaN(parseFloat(r.Premium))
        );

        // must have date & cat
        records = records.filter((r) => r.Bidding_Date && r.Vehicle_Class);

        // only A/B
        let filtered = records.filter((r) =>
          ["Category A", "Category B"].includes(r.Vehicle_Class)
        );

        if (this.internalCategory !== "All" && this.internalCategory !== 'all') {
          filtered = filtered.filter((r) => r.Vehicle_Class === this.internalCategory);
        }

        // group by date
        const grouped = {};
        filtered.forEach((r) => {
          const key = r.Bidding_Date;

          const received =
            this.toNumberMaybe(r.Bids_Received) ||
            this.toNumberMaybe(r.bids_received) ||
            this.toNumberMaybe(r.BidsReceived);

          const success =
            this.toNumberMaybe(r.Bids_Success) ||
            this.toNumberMaybe(r.bids_success) ||
            this.toNumberMaybe(r.BidsSuccess);

          if (!grouped[key]) {
            grouped[key] = {
              date: r.Bidding_Date,
              total_received: 0,
              total_success: 0,
            };
          }
          grouped[key].total_received += received;
          grouped[key].total_success += success;
        });

        const summarized = Object.values(grouped)
          .map((g, i) => {
            const rate =
              g.total_received > 0
                ? (g.total_success / g.total_received) * 100
                : 0;
            return {
              id: i + 1,
              date: g.date,
              round: this.getBiddingRound(g.date),
              success_rate: Number(rate.toFixed(1)),
            };
          })
          .sort((a, b) => a.date.localeCompare(b.date));

        this.successData = summarized.slice(-this.numRounds).reverse();
        this.currentPage = 1;
      } catch (err) {
        console.error("Error building COE success rate data:", err);
        this.previewError = String(err?.message || err);
      } finally {
        this.previewLoading = false;
        if (!this.firstRendered) {
          this.$emit("loaded", "BidsSuccess");
          this.firstRendered = true;
        }
      }
    },
    
    downloadCSV() {
      const header = ["Date", "Bidding Round", "Success Rate (%)"];
      const rows = this.successData.map(item => [
        item.date,
        item.round,
        item.success_rate
      ]);
      
      const csv = [header, ...rows]
        .map(row => row.join(","))
        .join("\n");
      
      const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `coe_success_rate_${this.internalCategory.toLowerCase().replace(' ', '_')}.csv`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    },
  },
};
</script>

<style scoped>
.card-container {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 400px;
}

/* Tight title ↔ header spacing — same as COEGrowthRate.vue */
.card-container :deep(.ant-card-head) {
  padding: 8px 16px;                 /* tighter than default */
}

.card-container :deep(.ant-card-body) {
  display: flex;
  flex-direction: column;
  height: 100%;
  padding-top: 8px;
  padding-right: 24px;
  padding-bottom: 24px;
  padding-left: 24px;
  overflow: hidden;
}

/* Table content area */
.table-content {
  flex: 1;
  overflow: auto;
  margin-bottom: 0;
  min-height: 0;
}

.growth-table :deep(.ant-table) {
  width: 100%;
}

.growth-table :deep(.ant-table-thead > tr > th),
.growth-table :deep(.ant-table-tbody > tr > td) {
  padding: 12px 16px !important;
  text-align: center;
  white-space: nowrap;
}

.growth-table :deep(.ant-table-thead > tr > th:first-child),
.growth-table :deep(.ant-table-tbody > tr > td:first-child) {
  text-align: left;
  min-width: 120px;
}

.filter-top-right {
  display: flex;
  align-items: center;
  gap: 8px;
}

.category-select {
  min-width: 70px;
  min-height: 27px;
  font-size: 0.8rem;
  border-radius: 6px;
  border: 1px solid #d9d9d9;
}

.info-icon {
  background: transparent;
  border: none;
  color: #595959;
  cursor: pointer;
  font-size: 14px;
  padding: 2px 4px;
  border-radius: 50%;
  transition: all 0.2s;
}

.info-icon:hover {
  background: #f5f5f5;
  color: #1677ff;
}

.icon-btn {
  background: transparent;
  border: none !important;
  box-shadow: none !important;
  outline: none !important;
  padding: 0 6px;
  height: 24px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  color: #595959;
  cursor: pointer;
}

.icon-btn:hover {
  background: #f5f5f5;
  border: none !important;
}

.icon-svg {
  width: 18px;
  height: 18px;
  fill: currentColor;
}

/* Sticky Footer — same as COEGrowthRate.vue */
.table-footer-sticky {
  position: sticky;
  bottom: 0;
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.75rem 0 0 0;
  margin-top: auto;
  margin-left: 10px;
  margin-right: 10px;
  font-size: 0.9rem;
  background-color: white;
  border-top: 1px solid #f0f0f0;
  z-index: 100;
  flex-shrink: 0;
}

/* Left: Show Last N Rounds */
.footer-left {
  display: flex;
  align-items: center;
  gap: 0.25rem;
}

.rounds-input {
  width: 60px;
  margin: 0 0.25rem;
  padding: 0.15rem 0.3rem;
  font-size: 0.85rem;
  border-radius: 5px;
  border: 1px solid #d9d9d9;
}

/* Right: Pagination with arrows */
.footer-right {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.arrow-btn {
  background: #f5f5f5;
  border: 1px solid #ccc;
  border-radius: 4px;
  font-size: 0.8rem;
  padding: 0.1rem 0.3rem;
  cursor: pointer;
  transition: background 0.2s;
}

.arrow-btn:hover:not(:disabled) { background: #e0e0e0; }
.arrow-btn:disabled { opacity: 0.4; cursor: not-allowed; }

.page-display {
  font-size: 0.85rem;
  color: #555;
}
</style>
