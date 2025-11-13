<template>
  <div class="page">
    <section>
      <!-- SEARCHBAR: Filtering (Always Visible) -->
      <div class="searchbar">

        <div class="seg">
          <label>Brand</label> 
          <select v-model="filters.brand">
            <option value="">Any</option>
            <option v-for="b in BRAND_OPTIONS" :key="b" :value="b">{{ b }}</option>
          </select>
        </div>

        <div class="seg">
          <label>Make / Model</label>
          <input type="text" placeholder="e.g. S-Class" v-model.trim="filters.make">
        </div>

        <div class="seg">
          <label>Price</label>
          <div class="twocol">
            <input type="number" placeholder="Min" v-model.number="filters.priceMin">
            <input type="number" placeholder="Max" v-model.number="filters.priceMax">
          </div>
        </div>

        <div class="seg">
          <label>Age of Vehicle (Years)</label>
          <div class="twocol">
            <input type="number" placeholder="Min"v-model.number="filters.ageMin">
            <input type="number" placeholder="Max" v-model.number="filters.ageMax">
          </div>
        </div>

        <div class="seg seg--mileage">
          <label>Mileage ≤</label>
          <input
            class="single-slider"
            type="range"
            v-model.number="filters.mileageMax"
            :min="limits.mileage.min"
            :max="limits.mileage.max"
            :step="limits.mileage.step"
          >
          <small class="hint">
            {{ fmt(filters.mileageMax != null ? filters.mileageMax : limits.mileage.max) }} km
          </small>
        </div>

        <div class="seg">
          <label>Fuel</label>
          <select v-model="filters.fuel">
            <option value="">Any</option>
            <option value="Petrol">Petrol</option>
            <option value="Hybrid">Hybrid</option>
            <option value="Electric">Electric</option>
            <option value="Diesel">Diesel</option>
          </select>
        </div>

        <div class="seg">
          <label>Transmission</label>
          <select v-model="filters.transmission">
            <option value="">Any</option>
            <option value="Automatic">Automatic</option>
            <option value="Manual">Manual</option>
          </select>
        </div>

        <div class="seg">
          <label>Max Owners</label>
          <input type="number" placeholder="Number of Owners" v-model.number="filters.owners_max">
        </div>
      </div>

      <!-- SEARCHBAR: Show More Filters Button -->
      <button
          class="more"
          type="button"
          @click="toggleMore"
          :aria-expanded="showMore.toString()"
          aria-controls="advanced-filters"
        >
          {{ showMore ? 'Hide filters' : 'View More Filters' }}
        </button>

      <!-- SEARCHBAR: Collapsed Filters (Hidden until clicked) -->
      <transition name="fade">
        <div
          id="advanced-filters"
          class="searchbar searchbar--advanced"
          v-show="showMore"
          aria-hidden="!showMore"
        >
        <div class="seg">
          <label>COE Category</label>
          <select v-model="filters.coe_cat">
            <option value="">Any</option>
            <option value="A">Category A</option>
            <option value="B">Category B</option>
          </select>
        </div>

        <div class="seg">
          <label>COE Left (Months)</label>
          <input type="number" placeholder="Minimum COE Left" v-model.number="filters.coe_months_min">
        </div>

        <div class="seg">
          <label>Engine Capacity</label>
          <div class="twocol">
            <input type="number" placeholder="Min" v-model.number="filters.engine_cc_min">
            <input type="number" placeholder="Max" v-model.number="filters.engine_cc_max">
          </div>
        </div>

        <div class="seg">
          <label>Horse Power (kW)</label>
          <div class="twocol">
            <input type="number" placeholder="Min" v-model.number="filters.hp_kw_min">
            <input type="number" placeholder="Max" v-model.number="filters.hp_kw_max">
          </div>
        </div>

        <div class="seg">
          <label>Max Days Since Posted</label>
          <input type="number" placeholder="e.g. 30" v-model.number="filters.freshness_max">
        </div>

        <div class="seg">
          <label>Website</label>
          <select v-model="filters.website">
            <option value="">Any</option>
            <option value="sgcarmart.com">SgCarMart.com</option>
            <option value="Carro.co">Carro.co</option>
            <option value="Motorist.sg">Motorist.sg</option>
          </select>
        </div>

        <div class="seg">
          <label>COE Renewed</label>
            <select v-model="filters.coe_renewed">
            <option value="">All</option>
            <option value="true">Only COE Renewed</option>
            <option value="false">Exclude COE Renewed</option>
          </select>
        </div>

        <!-- SEARCHBAR: Tickboxes -->
        <div class="seg seg--flags">
          <label class="vis-hidden">Options</label>
          <div class="flags-inline">
            <label class="flag"><input type="checkbox" v-model="filters.five_year"><span>5-Year COE</span></label>
            <label class="flag flag--classic"><input type="checkbox" v-model="filters.classic"><span>Classic Car</span></label>
            <label class="flag"><input type="checkbox" v-model="filters.sold"><span>Show Only Sold Cars</span></label>
          </div>
        </div>
      </div>
    </transition>

  <!-- SEARCHBAR: Go Button -->
  <button class="go" @click="fetchResults">Search</button>
</section>

    <!-- Sort bar -->
    <section class="metabar">
      <div class="meta__left">
        <strong v-if="loading">Loading…</strong>
        <strong v-else>{{ fmt(total) }} cars</strong>
        <span class="muted" v-if="loading">fetching results</span>
        <span class="muted" v-else-if="error">⚠ {{ error }}</span>
        <span class="muted" v-else>matching your criteria</span>
      </div>

      <!-- SORTBAR: Ranked sorts -->
      <div class="meta__right sort-group sort-group--multi">
        <label class="sortlab">Sort (top = highest priority)</label>

        <draggable
          v-model="sortRules"
          handle=".drag-handle"
          @end="applySort"
          class="sort-rules"
        >
          <div
            v-for="(rule, idx) in sortRules"
            :key="idx"
            class="sort-rule-row"
          >
            <!-- drag handle -->
            <span class="drag-handle">⋮⋮</span>

            <select v-model="rule.field" @change="applySort">
              <option v-for="opt in sortFieldOptions" :key="opt.value" :value="opt.value">
                {{ opt.label }}
              </option>
            </select>

            <select
              v-model="rule.dir"
              :disabled="rule.field === 'best_value'"
              @change="applySort"
            >
              <option v-for="opt in sortDirOptions" :key="opt.value" :value="opt.value">
                {{ opt.label }}
              </option>
            </select>

            <button
              type="button"
              class="sort-btn sort-btn--danger"
              @click="removeSortRule(idx)"
              v-if="sortRules.length > 1"
            >×</button>
          </div>
        </draggable>

        <button type="button" class="add-sort" @click="addSortRule">
          + Add sort
        </button>
      </div>
    </section>

<!-- RESULTS rows -->
  <section class="rows">
    <div v-if="loading" class="rows__loader">
      <div class="loadbar"><div class="loadbar__bar"></div></div>
    </div>
      <div v-else-if="error" class="error">⚠ {{ error }}</div>
      <article v-else class="row" v-for="(car, i) in allRows" :key="i">
        <div class="col car">
          <!-- RESULTS Images -->
          <div class="logo">
            <img
              v-if="logoSrc(car.Website)"
              class="thumb thumb--logo"
              :src="logoSrc(car.Website)"
              :alt="car.Website"
            >
          </div>
          <!-- RESULTS Name + Badges -->
          <div class="info">
            <h3>{{ car.Brand }} {{ car.Make }}</h3>
            <div class="badges">
              <span class="badge">{{ car.Vehicle_Age_Years }} years old</span>
              <span class="badge">{{ car.Transmission }}</span>
              <span class="badge">{{ car.Fuel_Type }}</span>
              <span class="badge">Cat {{ car.COE_Category }}</span>
            </div>
             <div class="sub">{{ car.Website }}</div>
          </div>
        </div>

        <!-- RESULTS Price + Depreciation -->
        <div class="col price">
          <div class="main">${{ fmt(car.Price) }}</div>
          <div class="sub">Depre. ${{ Math.round(car.DPM).toLocaleString() }} / mth</div>
        </div>

        <!-- RESULTS Additional Information: Mileage, COE Expiry, Registration Date -->
        <div class="col specs">
          <ul>
            <li><span>Mileage</span><b>{{ fmt(car.Mileage_km) }} km</b></li>
            <li><span>COE Expiry Date</span><b>{{ car.COE_Expiry_Date }}</b></li>
            <li><span>Registration Date</span><b>{{ car.Registration_Date }}</b></li>
          </ul>
        </div>

        <!-- RESULTS Button to View Listing Website -->
        <div class="col cta">
          <a
            class="btn"
            :href="car.URL"
            target="_blank"
            rel="noopener noreferrer"
          >
          View Listing
          </a>
        </div>
      </article>
    </section>

    <!-- Footer paginator -->
    <section class="pager" v-if="!error">
      <button class="pager__btn" @click="goToPage(1)" :disabled="page===1 || loading">« First</button>
      <button class="pager__btn" @click="prevPage"   :disabled="page===1 || loading">‹ Prev</button>
      <span class="pager__page">Page {{ page }} / {{ totalPages }}</span>
      <button class="pager__btn" @click="nextPage"   :disabled="page===totalPages || loading">Next ›</button>
      <button class="pager__btn" @click="goToPage(totalPages)" :disabled="page===totalPages || loading">Last »</button>
    </section>
  </div>
</template>

<script>
// Import logos
import logoSgcarmart from '@/assets/logos/sgcarmart_logo.png'
import logoMotorist  from '@/assets/logos/motorist_logo.png'
import logoCarro     from '@/assets/logos/carro_logo.png'
import draggable from 'vuedraggable'

// Set API Base
const API_BASE =
  process.env.VUE_APP_API_BASE ||
  (typeof window !== "undefined" ? window.API_BASE : null) ||
  "http://localhost:8000";

// Map source names to logos
const LOGOS = {
  "Carro.co": logoCarro,
  "sgcarmart.com": logoSgcarmart,
  "Motorist.sg": logoMotorist,
}
export default {
  name: 'Landscanner',
  components: { draggable },
  data() {
    return {
      API: API_BASE, // Load data from backend
      //Filter
      filters: {
        brand: "",
        make: "",
        priceMin: null,
        priceMax: null,
        ageMin: null,
        ageMax: null,
        mileageMax: 999999,
        fuel: "",
        transmission: "",
        owners_max: null,
        // Advanced Filters
        coe_cat: "",
        coe_months_min: null,
        engine_cc_min: null,
        engine_cc_max: null,
        hp_kw_min: null,
        hp_kw_max: null,
        freshness_max: null,
        website: "",
        coe_renewed: "",
        five_year: false,
        classic: false,
        sold: false,
      },
      BRAND_OPTIONS: [
        "Aion", "Alfa Romeo", "Alpine", "Aston Martin", "Audi", "Austin", "Bentley",
        "Bertone", "BMW", "BYD", "Cadillac", "Caterham", "Chevrolet", "Chrysler",
        "Citroen", "CUPRA", "Daihatsu", "Daimler", "Datsun", "DENZA", "Dodge", "DS",
        "Ferrari", "Fiat", "Ford", "Honda", "Hummer", "Hyundai", "Infiniti",
        "International", "Jaguar", "Jeep", "Kia", "Lamborghini", "Land Rover",
        "Lexus", "Lotus", "Maserati", "Maxus", "Maybach", "Mazda", "McLaren",
        "Mercedes-Benz", "MG", "MINI", "Mitsubishi", "Mitsuoka", "Morgan", "Morris",
        "Nissan", "Opel", "ORA", "Perodua", "Peugeot", "Polestar", "Pontiac",
        "Porsche", "Proton", "Renault", "Rolls-Royce", "Rover", "RUF", "Saab",
        "SEAT", "Skoda", "smart", "Ssangyong", "Subaru", "Sunbeam", "Suzuki", "TD",
        "Tesla", "Toyota", "Triumph", "Valiant", "Volkswagen", "Volvo", "XPENG",
        "ZEEKR", "DEEPAL", "GAC", "GREAT"
      ], // Provide data for drop down menu for Brands filter 
      limits: { mileage: { min: 0, max: 999999, step: 1000 }, // Mileage slider limits and step
      },
      // Sort
      sortField: 'best_value',
      sortDir: 'desc',
      sortFieldOptions: [
        { value: 'best_value',      label: 'Best' },
        { value: 'price',           label: 'Price' },
        { value: 'mileage',         label: 'Mileage' },
        { value: 'owners',          label: 'Number of Owners' },
        { value: 'posted_date',     label: 'Days Since Posted' },
        { value: 'coe_months',      label: 'COE Left (Months)' },
        { value: 'dpm',             label: 'Depreciation / Month' },
      ],
      sortDirOptions: [
        { value: 'asc',  label: 'Low to High' },
        { value: 'desc', label: 'High to Low' },
      ],
      sortRules: [
        { field: 'best_value', dir: 'desc' },
      ],
      // Results
      allRows: [], // Initialize empty rows to be displayed 
      LOGOS, //Images
      showMore: false, // Initialize show more filters to be false 
      loading: false, // Initialize loading state
      page :1, // Current page
      pageSize: 20, // Results per page
      total: 0, // Keep track of total results
      _reqId: 0
    }
  },
  mounted() {
    //this.fetch_landscanner_bq(); // Fetch initial data from backend
    this.fetchResults(); // Fetch results
  },

  watch: {
    //clamp when user types an out-of-range number
    'filters.mileageMax'(v) {
      if (v == null || isNaN(v)) return
      const { min, max } = this.limits.mileage
      if (v < min) this.filters.mileageMax = min
      if (v > max) this.filters.mileageMax = max
    },
  },
  computed: {
    totalPages() {
      return Math.max(1, Math.ceil(this.total / this.pageSize || 0));
    },
    rangeStart() {
      return this.total === 0 ? 0 : (this.page - 1) * this.pageSize + 1;
    },
    rangeEnd() {
      return Math.min(this.total, this.page * this.pageSize);
    },
  },
  methods: {
    // Fetch data from backend
    // async fetch_landscanner_bq() {
    //   try {
    //     this.loading = true // show loading state
    //     this.error = "" // reset error state
    //     const res = await fetch(`${this.API}/fetch_landscanner_bq`) 
    //     if (!res.ok) throw new Error(`HTTP ${res.status}`)
    //     const data = await res.json()
    //     this.allRows = Array.isArray(data.rows) ? data.rows : [] // populate rows with fetched data

    //   } catch (e) {
    //     this.error = String(e?.message || e)
    //   } finally {
    //     this.loading = false 
    //   }
    // },
    // Filtering methods
    toggleMore() {
      this.showMore = !this.showMore;
    },

    buildPayload() {
      const f = this.filters;

      const isEmpty = v => v === '' || v === null || v === undefined;

      const cleanStr = v => {
        if (isEmpty(v)) return undefined;
        const s = String(v).trim();
        return s.length ? s : undefined;
      };

      const cleanNum = v => {
        if (isEmpty(v)) return undefined;
        const n = Number(v);
        return Number.isFinite(n) ? n : undefined;
      };

      const cleanBool = v => (typeof v === 'boolean' ? v : undefined);

      const cleanArr1 = (v, {anyLabel} = {}) => {
        const s = cleanStr(v);
        if (!s) return undefined;
        if (anyLabel && s.toLowerCase() === anyLabel.toLowerCase()) return undefined;
        return [s];
      };

      // Map UI -> API (omit empties)
      const payload = {
        // text contains
        make_contains: cleanStr(f.make),

        // dropdowns (treat 'Any' as undefined)
        brand_in:       cleanArr1(f.brand,       { anyLabel: 'Any' }),
        fuel_in:        cleanArr1(f.fuel,        { anyLabel: 'Any' }),
        trans_in:       cleanArr1(f.transmission,{ anyLabel: 'Any' }),
        website_in:     cleanArr1(f.website,     { anyLabel: 'Any' }),

        // COE category like "Category A" -> "A"
        coe_cat_in: (() => {
          const s = cleanStr(f.coe_cat);
          if (!s || s.toLowerCase() === 'any') return undefined;
          return [s.replace(/category\s*/i, '').trim()];
        })(),

        // numbers
        price_min:      cleanNum(f.priceMin),
        price_max:      cleanNum(f.priceMax),
        mileage_max:    cleanNum(f.mileageMax),
        owners_max:     cleanNum(f.owners_max),
        age_min:        cleanNum(f.ageMin),
        age_max:        cleanNum(f.ageMax),
        coe_months_min: cleanNum(f.coe_months_min),
        engine_cc_min:  cleanNum(f.engine_cc_min),
        engine_cc_max:  cleanNum(f.engine_cc_max),
        hp_kw_min:      cleanNum(f.hp_kw_min),
        hp_kw_max:      cleanNum(f.hp_kw_max),
        freshness_max:  cleanNum(f.freshness_max),

        coe_renewed: (() => {
          if (f.coe_renewed === '') return undefined;   // user chose "All" -> don't filter
          if (f.coe_renewed === 'true') return true;    // Only COE Renewed
          if (f.coe_renewed === 'false') return false;  // Exclude COE Renewed
          return undefined;
        })(),

        // booleans (only send when explicitly true/false)
        five_year:      f.five_year   ? true : undefined,
        classic:        f.classic     ? true : undefined,
        sold: (() => {
          if (f.sold === true) return true;   // user ticked → show sold
          return false;                        // default → show unsold
        })(),

        // pagination + sorting
        page:           this.page,
        page_size:      this.pageSize,

        sort_by:        cleanStr(f.sort_by),
        sort_dir:       cleanStr(f.sort_dir),
      };

  // remove undefined keys
  Object.keys(payload).forEach(k => payload[k] === undefined && delete payload[k]);
  return payload;
},


    // Sorting methods
    onFieldChange() { 
      if (this.sortField === 'best_value') {
        this.sortDir = 'desc'; // best_value is always desc
      }
      if (this.sortField == 'owners') {
        this.sortDir = 'asc'; // number of owners default to asc
      }
    this.applySort(); // apply sort after field change
    },
    composeSortKey() {
      if (this.sortField === 'best_value') return 'best_value'; // special case
      if (this.sortField === 'owners') return 'owners_asc'; // special case
      const map = {
        price: 'price',
        dpm: 'dpm',
        dpy: 'dpy',
        coe_months: 'coe_months',
        mileage: 'mileage',
        posted_date: 'posted_date',
      };
      const base = map[this.sortField] || 'best_value'; // default to best
      const dir  = this.sortDir === 'desc' ? 'desc' : 'asc'; // default to asc
      return `${base}_${dir}`;   // e.g. 'price_desc'
    },
    async applySort() {
      this.page = 1; // reset to first page on sort change
      await this.fetchResults();
    },

    // addSortRule() {
    //   // default new rule
    //   this.sortRules.push({ field: 'price', dir: 'asc' });
    // },

    addSortRule() {
      // fields already used
      const used = this.sortRules.map(r => r.field);
      // find first option not yet used (skip 'best_value')
      const nextOpt = this.sortFieldOptions.find(opt => !used.includes(opt.value));
      if (nextOpt) {
        // add unused field
        this.sortRules.push({
          field: nextOpt.value,
          dir: nextOpt.value === 'owners' ? 'asc' : 'desc',
        });
      } else {
        // all used → just duplicate something sensible
        this.sortRules.push({ field: 'price', dir: 'asc' });
      }
      this.applySort();
    },

    removeSortRule(idx) {
      this.sortRules.splice(idx, 1);
      // always keep at least one
      if (this.sortRules.length === 0) {
        this.sortRules.push({ field: 'price', dir: 'asc' });
      }
      this.applySort();
    },

    moveSortUp(idx) {
      if (idx === 0) return;
      const rule = this.sortRules[idx];
      this.sortRules.splice(idx, 1);
      this.sortRules.splice(idx - 1, 0, rule);
      this.applySort();
    },

    moveSortDown(idx) {
      if (idx === this.sortRules.length - 1) return;
      const rule = this.sortRules[idx];
      this.sortRules.splice(idx, 1);
      this.sortRules.splice(idx + 1, 0, rule);
      this.applySort();
    },

    // turn UI rules into backend keys
    composeSortKeysFromRules() {
      const keys = [];
      this.sortRules.forEach(rule => {
        let base = 'price';

        // match your existing mapping in composeSortKey()
        switch (rule.field) {
          case 'best_value':
            keys.push('best_value');
            return; // this one is complete
          case 'owners':
            keys.push('owners_asc');
            return;
          case 'price':
            base = 'price'; break;
          case 'dpm':
            base = 'dpm'; break;
          case 'dpy':
            base = 'dpy'; break;
          case 'coe_months':
            base = 'coe_months'; break;
          case 'mileage':
            base = 'mileage'; break;
          case 'posted_date':
            base = 'posted_date'; break;
          case 'age':
            base = 'age'; break;
          default:
            base = 'price';
        }
        const dir = rule.dir === 'desc' ? 'desc' : 'asc';
        keys.push(`${base}_${dir}`);
      });
      return keys;
    },

    // Results
    logoSrc(source) {
      return LOGOS[source]  || undefined
    },
    fmt(n) { //pretty print numbers with commas
      if (n === null || n === undefined || n === '') return ''
      const x = Number(n)
      if (!Number.isFinite(x)) return String(n)
      return x.toLocaleString()
    },
    
    async fetchResults() {
      const myId = ++this._reqId;
      this.loading = true;
      this.error = "";
      try {
        const payload = {
          ...this.buildPayload(),
          page: this.page,
          page_size: this.pageSize,
          sort_keys: this.composeSortKeysFromRules(),
        };        
        const res = await fetch(`${API_BASE}/cars/search`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();
        this.total   = data.total ?? 0;
        this.page    = data.page  ?? 1;
        this.pageSize= data.page_size ?? this.pageSize;
        this.allRows = Array.isArray(data.rows) ? data.rows : [];
        if (myId === this._reqId) {
        this.total   = data.total ?? 0;
        this.allRows = Array.isArray(data.rows) ? data.rows : [];
      }
      } catch (e) {
        console.error(e);
        this.error = "Failed to load results.";
        this.allRows = [];
      } finally {
        this.loading = false;
      }
    },
    async goToPage(p) {
      const target = Math.min(Math.max(1, p), this.totalPages);
      if (target === this.page) return;
      this.page = target;
      await this.fetchResults();
    },
    async nextPage() {
      if (this.page < this.totalPages) {
        this.page += 1;
        await this.fetchResults();
      }
    },
    async prevPage() {
      if (this.page > 1) {
        this.page -= 1;
        await this.fetchResults();
      }
    }

  }
}

</script>

<style scoped>
:root{ --container: 1100px;  color-scheme: light dark; }
@media (min-width: 1200px){ :root{ --container: 1280px; } }
@media (min-width: 1600px){ :root{ --container: 1440px; } }

.page{
  max-width: var(--container);
  margin: 0 auto;
  padding-inline: clamp(12px, 2vw, 28px);
}

.searchbar {
  display: grid;
  grid-template-columns: repeat(4, minmax(240px, 1fr));
  gap: 8px;
  width: 100%;
  overflow: hidden;
  box-sizing: border-box;

}
.searchbar .seg { display: flex; flex-direction: column; gap: 4px; }
.searchbar label { font-size: .74rem; font-weight: 600; color: #374151; }
.searchbar input, .searchbar select { padding: 10px 12px; border: 1px solid #e5e7eb; border-radius: 10px; background: #f9fafb; }
.searchbar .twocol {display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 1fr); gap: 6px;}
.searchbar input[type="range"] {
  width: 100%;
  display: block;
  -webkit-appearance: none;
  appearance: none;
  height: 6px;
  background: #e5e7eb;
  border-radius: 999px;
  outline: none;
  padding: 0; 
  margin: 10;
}
.more { margin-right: 10px; margin-top: 10px; margin-bottom: 10px; }  
.seg--mileage .single-slider {
  margin-top: 18px;
}

.seg--mileage .hint {
  margin-top: 6px;
  font-size: .8rem;
}

/* Mileage Slider */
input[type="range"] {
  -webkit-appearance: none; appearance: none;
  width: 100%; height: 6px; background: #e5e7eb; border-radius: 999px; outline: none;
}
input[type="range"]::-webkit-slider-thumb {
  -webkit-appearance: none; appearance: none;
  height: 18px; width: 18px; border-radius: 50%; background: #3B82F6; cursor: pointer;
}
input[type="range"]::-moz-range-thumb {
  height: 18px; width: 18px; border-radius: 50%; background: #111827; border: none; cursor: pointer;
}

/* Tick Boxes */
.vis-hidden { visibility: hidden; }

.seg--flags .flags-inline {
  display: grid;
  grid-template-columns: repeat(2, auto);  /* 4 flags inside one cell */
  gap: 3px;
  padding: 2px 5px;                      /* matches your input padding */
  border: none;                            /* remove border */
  background: transparent;                 /* remove background */
  border-radius: 0;                         /* no rounded box */
}

.flag {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  white-space: nowrap;
  font-size: .9rem;
  line-height: 1;
}
.flag input[type="checkbox"] { width: 16px; height: 16px; accent-color: #3B82F6; }
.flag--classic {
  margin-left: -35px;   /* adjust this number until it looks nice */
}
/* smooth show/hide */
.fade-enter-active, .fade-leave-active { transition: opacity .16s ease; }
.fade-enter-from, .fade-leave-to { opacity: 0; }

/* Sort */
.metabar { position: sticky; top: 78px; display: flex; justify-content: space-between;align-items: center; 
  border-radius: 12px; box-shadow: 0 1px 2px rgba(0,0,0,0.05); padding: 10px 8px;
  margin: 10px 0; border-bottom: 1px solid #e5e7eb; background: #fff; z-index: 9; }
.meta__left { display: flex; gap: 8px; align-items: baseline; }
.muted { color: #6b7280; font-size: .9rem; }
.meta__right { display: flex; gap: 10px; align-items: center; }
.sortlab { color: #6b7280; font-size: .9rem; }
.sorttabs button { padding: 6px 10px; border: 1px solid #e5e7eb; background: #fff; border-radius: 999px; cursor: default; }

.sort-group--multi {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center; 
}

/* .sort-rules {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
} */

.sort-rule-row {
  display: flex;
  gap: 4px;
  background: rgba(255,255,255,0.03);
  padding: 4px 6px;
  border-radius: 6px;
  align-items: center; 
}

/* .sort-rule-row select {
  padding: 2px 4px;
} */

.sort-btn {
  border: none;
  background: #e5e7eb;
  cursor: pointer;
  padding: 0 6px;
  border-radius: 4px;

}
.sort-btn:disabled {
  opacity: 0.4;
  cursor: default;
}
.sort-btn--danger {
  background: #fca5a5;
}

.add-sort {
  background: #3b82f6;
  color: #fff;
  border: none;
  padding: 1px 6px; 
  cursor: pointer;
  border-radius: 4px;
  
}
/* Results */

.rows__loader { padding: 16px 3px; }
.loadbar { position: relative; height: 4px; background: rgba(0,0,0,.08); border-radius: 3px; overflow: hidden; }
.loadbar__bar { position: absolute; top:0; left:-30%; width:30%; height:100%; border-radius:3px; opacity:.7;
  background: #3B82F6; animation: load-scan 1.1s infinite ease-in-out; }
@keyframes load-scan { 0%{transform:translateX(0)} 100%{transform:translateX(430%)} }

@media (max-width: 680px) {
  .seg--flags .flags-inline { grid-template-columns: repeat(2, auto); }
}

@media (max-width: 680px) {
  .seg--flags .flags-input { grid-template-columns: repeat(2, 1fr); }
}

.logo {
  width: 120px;
  height: 80px;
  border-radius: 10px;
  background: #f8fafc;
  border: 1px solid #e5e7eb;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
}

.thumb {
  width: 120px;
  height: 80px;
  background: #f3f4f6;
} 
.rows { display: grid; gap: 10px; }
.row { display: grid; grid-template-columns: 1.4fr .6fr .8fr .5fr; gap: 10px; border: 1px solid #e5e7eb; border-radius: 14px; padding: 10px; background: #fff; box-shadow: 0 1px 2px rgba(0,0,0,.03); }
.col.car { display: grid; grid-template-columns: 120px 1fr; gap: 10px; align-items: center; }

.info h3 { margin: 0; font-size: 1.05rem; }
.badges { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 4px; }
.badge { padding: 4px 8px; font-size: .8rem; border: 1px solid #e5e7eb; border-radius: 999px; background: #f9fafb; }
.sub { color: #6b7280; font-size: .9rem; margin-top: 4px; }

.col.price { display: grid; align-content: center; justify-items: start; }
.col.price .main { font-weight: 800; font-size: 1.1rem; }
.col.price .sub { font-size: .85rem; }

.col.specs ul { list-style: none; margin: 0; padding: 0; display: grid; gap: 6px; }
.col.specs li { display: flex; justify-content: space-between; gap: 10px; }
.col.specs span { color: #6b7280; }
.col.specs b { font-weight: 700; }

.col.cta { display: grid; align-content: center; gap: 8px; justify-items: end; }
.btn { padding: 8px 12px; border: 1px solid #e5e7eb; border-radius: 10px; background: #f3f4f5; }
.ghost { color: #111827; opacity: .6; text-decoration: none; cursor: default; }
.actions { display:flex; gap:8px; align-items:center; margin: 6px 0 8px; }
.go { 
  padding: 10px 16px; border: none; border-radius: 12px; background: #3B82F6; color: #fff; margin-top: 10px; margin-bottom: 10px;
}
.more { padding:10px 12px; border:1px solid #e5e7eb; border-radius:10px; background:#fff; }

.advanced {
  display:grid;
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
  gap:8px;
}

.drag-handle {
  cursor: grab;
  padding: 0 4px;
  color: #6b7280;
}

/* Paginator */
.pager { display: flex; justify-content: center; align-items:center; gap: 12px; padding: 18px 0; color: #6b7280; }
.pager button { padding: 6px 10px; border: 1px solid #e5e7eb; background: #fff; border-radius: 10px; cursor: default; }

/* Responsive */
@media (max-width: 1100px) { .row { grid-template-columns: 1fr .6fr .8fr .5fr; } }
@media (max-width: 920px)  { .row { grid-template-columns: 1fr .7fr .7fr; } .col.cta { grid-column: 1 / -1; justify-items: start; } }
@media (max-width: 680px)  { .searchbar { grid-template-columns: 1fr 1fr; } .metabar { top: 120px; } .row { grid-template-columns: 1fr; } .col.car { grid-template-columns: 100px 1fr; } }
</style>
