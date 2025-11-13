<template>
  <div class="car-form-container">

    <h2>Resale Car Price Predictor</h2>

    <div v-if="brandsLoading" class="loading-strip">
      <div class="loading-strip__inner"></div>
    </div>

    <div v-if="brandsError" class="error mb-24">{{ brandsError }}</div>

    <div class="instruction-box">
      <h3>Instructions:</h3>
      <p>
        If you cannot find your desired car make, you can customize the car by leaving
        the <strong>Model Year</strong> and <strong>Make</strong> fields blank. You can proceed to fill in <strong>OMV</strong>, <strong>Engine Capacity</strong>, 
        <strong>Horse Power</strong> and <strong>Fuel Type</strong> manually.
      </p>
    </div>
    <form @submit.prevent="predict" class="car-form">
      <!-- Grid layout for inputs -->
      <div class="form-grid">
        <div class="form-group">
          <label>Brand<span class="required">*</span></label>
          <select v-model="form.brand" @change="onBrandChange" required>
            <option disabled value="">Select Brand</option>
            <option v-for="brand in brands" :key="brand" :value="brand">{{ brand }}</option>
          </select>
        </div>

        <div class="form-group">
          <label>Model Year</label>
          <select
            v-model="form.year"
            @change="onYearChange"
            :disabled="availableYears.length === 0"
            required
          >
            <option disabled value="">Select Year</option>
            <option v-for="year in availableYears" :key="year" :value="year">
              {{ year }}
            </option>
          </select>
        </div>

        <div class="form-group">
          <label>Make</label>
          <select
            v-model="form.make"
            @change="onMakeChange"
            :disabled="availableMakes.length === 0"
            required
          >
            <option disabled value="">Select Make</option>
            <option v-for="make in availableMakes" :key="make" :value="make">{{ make }}</option>
          </select>
        </div>

        <div class="form-group">
          <label>
            OMV ($)<span class="required">*</span>
            <span class="autofill-bubble" v-show="autofill.omv">Suggested</span>
          </label>
          <input
            type="number"
            v-model.number="form.omv"
            @input="autofill.omv = false"
          />
        </div>

        <div class="form-group">
          <label>
            Engine Capacity (cc)<span class="required">*</span>
            <span class="autofill-bubble" v-show="autofill.engine_cc">Suggested</span>
          </label>
          <input
            type="number"
            v-model.number="form.engine_cc"
            @input="autofill.engine_cc = false"
            required
          />
        </div>

        <div class="form-group">
          <label>
            Horse Power (kW)<span class="required">*</span>
            <span class="autofill-bubble" v-show="autofill.horse_power">Suggested</span>
          </label>
          <input
            type="number"
            v-model.number="form.horse_power"
            @input="autofill.horse_power = false"
            required
          />
        </div>

        <div class="form-group">
          <label>
            Fuel Type<span class="required">*</span>
            <span class="autofill-bubble" v-show="autofill.fuel_type">Suggested</span>
          </label>
          <select
            v-model="form.fuel_type"
            @change="autofill.fuel_type = false"
            required
          >
            <option disabled value="">Select Fuel Type</option>
            <option>Petrol</option>
            <option>Diesel</option>
            <option>Electric</option>
            <option>Hybrid</option>
          </select>
        </div>


        <div class="form-group">
          <label>COE Left<span class="required">*</span></label>
          <div style="display: flex; gap: 8px; align-items: center;">
            <!-- COE Left -->
            <input
              v-model.number="form.coe_left_years"
              type="number"
              min="0"
              placeholder="Years"
              class="form-control"
              style="flex: 1 1 0; max-width: 50%;"
            />

            <input
              v-model.number="form.coe_left_months"
              type="number"
              min="0"
              max="11"
              placeholder="Months"
              class="form-control"
              style="flex: 1 1 0; max-width: 50%;"
            />
          </div>
        </div>

        <div class="form-group">
          <label>Mileage (km)<span class="required">*</span></label>
          <input v-model.number="form.mileage" type="number" required />
        </div>

        

        <div class="form-group">
          <label>Previous COE ($)<span class="required">*</span></label>
          <input v-model.number="form.previous_coe" type="number" required />
        </div>

        <div class="form-group">
          <label>Vehicle Age<span class="required">*</span></label>
          <div style="display: flex; gap: 8px; align-items: center;">
            <!-- Vehicle Age -->
            <input
              v-model.number="form.vehicle_age_years"
              type="number"
              min="0"
              placeholder="Years"
              class="form-control"
              style="flex: 1 1 0; max-width: 50%;"
            />

            <input
              v-model.number="form.vehicle_age_months"
              type="number"
              min="0"
              max="11"
              placeholder="Months"
              class="form-control"
              style="flex: 1 1 0; max-width: 50%;"
            />
            <!-- <span>months</span> -->
          </div>
        </div>

        <div class="form-group">
          <label>Road Tax Payable ($/year)<span class="required">*</span></label>
          <input v-model.number="form.road_tax" type="number" required />
        </div>

        
      </div>

      <button type="submit" :disabled="loading" class="submit-btn">
        {{ loading ? "Predicting..." : "Predict Price" }}
      </button>
    </form>

    <p v-if="error" class="error">{{ error }}</p>

    <div v-if="predictedPrice !== null" class="result">
      <strong>Predicted Price:</strong> SGD ${{ Number(predictedPrice).toLocaleString() }}
    </div>

    <!-- Explanation block -->
    <div v-if="explanationMarkdown" class="result explanation-block" style="text-align:left; margin-top: 1rem;">
      <p class="explanation-title">Why this price?</p>
      <div v-html="renderMarkdown(explanationMarkdown)" class="markdown-content"></div>
    </div>


    <div v-if="drivers && drivers.length" class="drivers" style="margin-top: 12px; display:flex; flex-wrap:wrap; gap:8px;">
      <span
        v-for="(d, i) in drivers"
        :key="i"
        class="driver-chip"
        :title="d.raw_feature"
        :style="d.direction === 'up'
          ? 'background:#e8f7ee;color:#0a5b2d;border:1px solid #bce3cc;padding:4px 8px;border-radius:999px;font-size:12px;'
          : 'background:#fdecec;color:#7a0a0a;border:1px solid #f3c3c3;padding:4px 8px;border-radius:999px;font-size:12px;'"
      >
        {{ d.feature }} {{ d.direction === 'up' ? '▲' : '▼' }}
      </span>
    </div>

    
  </div>

  
</template>

<script>
import axios from "axios";
import { marked } from "marked";
import DOMPurify from "dompurify";

// Set API Base
const API_BASE =
  process.env.VUE_APP_API_BASE ||
  (typeof window !== "undefined" ? window.API_BASE : null) ||
  "http://localhost:8000";

export default {
  data() {
    return {
      form: {
        brand: '',
        year: null,
        make: '',
        omv: null,
        coe_left: null,
        mileage: null,
        engine_cc: null,
        horse_power: null,
        previous_coe: null,
        road_tax: null,
        fuel_type: '',
        vehicle_age_days: null,

        // To allow us to fill blank dates:
        coe_left_years: null,
        coe_left_months: null,
        vehicle_age_years: null,
        vehicle_age_months: null,

        // Loading Bar
        loading: false,
        error: null,
        brandsLoading: false,
        brandsError: null,
      },
      autofill: {
        omv: false,
        engine_cc: false,
        horse_power: false,
        fuel_type: false
      },
      brands: [], 
      availableMakes: [], // filtered based on Brand & Year
      availableYears: [], // filtered based on Brand
      loading: false,
      error: null,
      predictedPrice: null,
      explanationMarkdown: '',
      drivers: []
    };
  },

  created() {
    // We call the new method to fetch brands from the API.
    this.fetchBrands();
  },
  
  methods: {
    async fetchBrands() {
      this.brandsLoading = true;
      this.brandsError = null;
      
      try {
        // *******************************************************************
        // *** IMPORTANT: Replace '/api/brands' with your real API endpoint ***
        // *******************************************************************
        const response = await fetch(`${API_BASE}/get_brands`);

        if (!response.ok) {
          // Handle HTTP errors like 404 or 500
          throw new Error(`Failed to fetch brands. Status: ${response.status}`);
        }

        // Assuming your API returns a simple JSON array of strings:
        // e.g., ["ALFA ROMEO", "AUDI", "B.M.W.", ...]
        const data = await response.json();
        
        this.brands = data;

      } catch (error) {
        // Handle network errors or errors from the 'throw' statement above
        console.error("Error fetching brands:", error);
        this.brandsError = "Could not load brand list. Please try refreshing.";
      } finally {
        // This runs whether the fetch succeeded or failed
        this.brandsLoading = false;
      }
    },

    // ... you can add other methods here, like your form submission logic

    async predict() {
      this.loading = true;
      this.error = null;
      this.predictedPrice = null;
      this.explanationMarkdown = '';
      this.drivers = [];

      try {
        // 1. Validate COE left
        const hasCoeYears  = this.form.coe_left_years !== null && this.form.coe_left_years !== '' && !isNaN(this.form.coe_left_years);
        const hasCoeMonths = this.form.coe_left_months !== null && this.form.coe_left_months !== '' && !isNaN(this.form.coe_left_months);

        if (!hasCoeYears && !hasCoeMonths) {
          throw new Error("Please fill in COE Left (years, months, or both).");
        }

        // 2. Validate Vehicle age
        const hasVehYears  = this.form.vehicle_age_years !== null && this.form.vehicle_age_years !== '' && !isNaN(this.form.vehicle_age_years);
        const hasVehMonths = this.form.vehicle_age_months !== null && this.form.vehicle_age_months !== '' && !isNaN(this.form.vehicle_age_months);

        if (!hasVehYears && !hasVehMonths) {
          throw new Error("Please fill in Vehicle Age (years, months, or both).");
        }

        // Convert years & months to days
        const coeYears   = Number(this.form.coe_left_years || 0);
        const coeMonths  = Number(this.form.coe_left_months || 0);
        const ageYears   = Number(this.form.vehicle_age_years || 0);
        const ageMonths  = Number(this.form.vehicle_age_months || 0);
        const coe_left_days = (coeYears * 12 + coeMonths) * 30;
        const vehicle_age_days = (ageYears * 12 + ageMonths) * 30;

        // Prepare payload to match backend model
        const payload = {
          ...this.form,
          coe_left: coe_left_days, // override coe_left
          vehicle_age_days: vehicle_age_days, // override days
        };

        const res = await axios.post(`${API_BASE}/predict_explain`, payload);
        this.predictedPrice = res.data.predicted_price;
        this.explanationMarkdown = res.data.explanation_markdown || '';
        this.drivers = Array.isArray(res.data.drivers) ? res.data.drivers : [];
      } catch (e) {
        console.error(e);
        this.error = e.message || e.response?.data?.detail || "Prediction failed";
      } finally {
        this.loading = false;
      }
    },
    async onBrandChange() {
      this.form.year = "";
      this.form.make = "";
      this.availableYears = [];
      this.availableMakes = [];

      if (!this.form.brand) return;

      try {
        const res = await fetch(
          `${API_BASE}/get_model_year?brand=${encodeURIComponent(this.form.brand)}`
        );
        const data = await res.json();
        console.log("Fetched years:", data);
        this.availableYears = data.years || [];
      } catch (err) {
        console.error("Error fetching years:", err);
        this.availableYears = [];
      }
    },

    // Step 2: When year changes, fetch makes
    async onYearChange() {
      this.form.make = "";
      this.availableMakes = [];

      if (!this.form.brand || !this.form.year) return;

      try {
        const res = await fetch(
          `${API_BASE}/available-makes?brand=${encodeURIComponent(this.form.brand)}&year=${this.form.year}`
        );
        const data = await res.json();
        this.availableMakes = data.makes || [];
      } catch (err) {
        console.error("Error fetching makes:", err);
        this.availableMakes = [];
      }
    },

    async onMakeChange() {
      if (!this.form.make || !this.form.brand || !this.form.year) return;

      try {
        const res = await fetch(
          `${API_BASE}/get-omv?brand=${encodeURIComponent(this.form.brand)}&year=${this.form.year}&make=${encodeURIComponent(this.form.make)}`
        );
        const data = await res.json();

        
        if (data.omv !== null) {
          this.form.omv = data.omv;
          this.form.engine_cc = data.engine_cc;
          this.form.horse_power = data.horse_power;
          this.form.fuel_type = data.fuel_type;

          // Show "Suggested" bubble per field
          this.autofill.omv = true;
          this.autofill.engine_cc = true;
          this.autofill.horse_power = true;
          this.autofill.fuel_type = true;

        }
      } catch (err) {
        console.error("Error fetching OMV:", err);
      }
    },

    renderMarkdown(text) {
      if (!text) return "";
      const rawHtml = marked.parse(text);
      return DOMPurify.sanitize(rawHtml);
    }
  },

  
};
</script>

<style scoped>
.car-form-container {
  max-width: 800px;
  margin: 2rem auto;
  padding: 2rem;
  background: #fff;
  border-radius: 12px;
  box-shadow: 0 8px 20px rgba(0, 0, 0, 0.1);
  font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
}

h2 {
  text-align: center;
  margin-bottom: 1.5rem;
  color: #333;
}

.car-form .form-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: 1rem 2rem;
  margin-bottom: 1.5rem;
}

.form-group {
  display: flex;
  flex-direction: column;
}

label {
  margin-bottom: 0.5rem;
  font-weight: 500;
  color: #555;
}

input,
select {
  padding: 0.5rem 0.75rem;
  border: 1px solid #ccc;
  border-radius: 8px;
  font-size: 0.95rem;
  transition: border 0.2s, box-shadow 0.2s;
}

input:focus,
select:focus {
  border-color: #007bff;
  box-shadow: 0 0 0 2px rgba(0, 123, 255, 0.2);
  outline: none;
}

.submit-btn {
  display: block;
  width: 100%;
  padding: 0.75rem;
  background-color: #007bff;
  color: #fff;
  font-weight: 600;
  border: none;
  border-radius: 10px;
  cursor: pointer;
  transition: background 0.2s;
}

.submit-btn:hover {
  background-color: #0056b3;
}

.error {
  color: red;
  margin-top: 1rem;
  text-align: center;
}

.result {
  margin-top: 1rem;
  font-size: 1.1rem;
  text-align: center;
  background: #f0f8ff;
  padding: 0.75rem;
  border-radius: 8px;
}

.form-group {
  position: relative;
  margin-bottom: 16px;
}

.form-group label {
  display: flex;
  align-items: center;
  font-weight: 500;
  gap: 8px; /* space between label text and bubble */
}

/* Autofill bubble styling */
.autofill-bubble {
  background-color: #f0f8ff; /* light blue */
  color: #007bff;
  border: 1px solid #007bff;
  border-radius: 4px;
  padding: 2px 6px;
  font-size: 12px;
  white-space: nowrap;
  pointer-events: none;
}

/* Optional: fade-in animation for better effect */
.autofill-bubble[v-cloak] {
  display: none;
}

.autofill-bubble {
  transition: opacity 0.3s ease;
  opacity: 1;
}

.instruction-box {
  border: 1px solid #007bff;
  background-color: #f0f8ff;
  border-radius: 6px;
  padding: 12px 16px;
  margin-bottom: 20px;
  font-size: 14px;
  color: #003366;
}

.instruction-box h3 {
  margin: 0 0 6px 0;
  font-size: 16px;
}

.required {
  color: red;
  margin-left: -3px;
  display: inline;
}

.explanation-block {
  font-size: 1rem; /* base size for the whole block */
}

.explanation-title {
  font-weight: 600;
  margin: 0 0 8px 0;
  font-size: rem; /* same as body text */
}

/* Because we're using v-html + scoped styles, use :deep/::v-deep */
:deep(.markdown-content),
:deep(.markdown-content p),
:deep(.markdown-content li) {
  font-size: 1rem;  /* force bullets + paragraphs to match */
}

/* (optional) nicer list spacing */
:deep(.markdown-content ul) {
  padding-left: 20px;
  margin: 4px 0;
}

:deep(.markdown-content li) {
  margin-bottom: 4px;
}

.loading-strip {
  position: relative;
  width: 100%;
  height: 4px;
  background: rgba(24, 144, 255, 0.15);
  margin-bottom: 16px;
  overflow: hidden;
  border-radius: 2px;
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
  0% {
    left: -30%;
  }
  100% {
    left: 100%;
  }
}
</style>