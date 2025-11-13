<template>
  <div class="chatbot-container" v-if="isVisible">
    <div class="chatbot-header">
      <h3>Data Assistant</h3>
      <button @click="toggleChatbot" class="close-btn">×</button>
    </div>
    
    <div class="chatbot-messages" ref="messagesContainer">
      <div v-for="(message, index) in messages" :key="index" 
           :class="['message', message.type]">
        <div class="message-content" v-html="message.content"></div>
        <div class="message-time">{{ formatTime(message.timestamp) }}</div>
      </div>
      <div v-if="isTyping" class="message bot typing">
        <div class="typing-indicator">
          <span></span><span></span><span></span>
        </div>
      </div>
    </div>
    
    <div class="chatbot-options" v-if="currentOptions.length > 0">
      <button 
        v-for="(option, index) in currentOptions" 
        :key="index"
        @click="selectOption(option)"
        class="option-btn"
      >
        {{ option.text }}
      </button>
    </div>
  </div>
  
  <div v-else>
    <!-- Auto-popup greeting -->
    <div v-if="showGreeting" class="greeting-popup">
      <div class="greeting-content">
        <img src="@/assets/logos/chatbot_logo.png" alt="Data Assistant" class="greeting-logo" />
        <div class="greeting-text">
          <div class="greeting-title">Hello! 👋</div>
          <div class="greeting-subtitle">I'm your Data Assistant, ready to help with analytics and insights!</div>
        </div>
      </div>
    </div>
    
    <!-- Chat toggle button -->
    <button @click="toggleChatbot" class="chatbot-toggle">
      <img src="@/assets/logos/chatbot_logo.png" alt="Data Assistant" class="toggle-logo" />
    </button>
  </div>
</template>

<script>
export default {
  name: 'DataChatbot',
  data() {
    return {
      isVisible: false,
      isTyping: false,
      showGreeting: false,
      hasShownGreeting: false,
      currentStep: 'start',
      selectedCategory: '',
      dataType: '',
      selectedStartYear: null,
      avgType: '',
      currentOptions: [],
      messages: [
        {
          type: 'bot',
          content: 'Hi, what do you need help with today?',
          timestamp: new Date()
        }
      ],
      knowledgeBase: {
        carFeaturesDefinitions: {
          'make': 'The specific model or variant of a vehicle (e.g., Toyota Corolla Altis).',
          'mileage': 'Total distance traveled by the vehicle, measured in kilometers.',
          'omv': 'Open Market Value (OMV) is the market value of a vehicle without COE, registration fees, and taxes.',
          'arf': 'Additional Registration Fee (ARF) is a tax based on the OMV of the vehicle.',
          'engine capacity': 'Engine displacement measured in cubic centimeters (cc), indicating engine size.',
          'horse power': 'Engine power output measured in kilowatts (kW) or brake horsepower (bhp).',
          'road tax payable': 'Annual tax paid to use the vehicle on Singapore roads, based on engine capacity.',
          'coe paid': 'The amount paid for the Certificate of Entitlement when the vehicle was registered.',
          'transmission': 'Type of gearbox - either Automatic or Manual transmission.',
          'fuel type': 'Type of fuel used - Petrol, Diesel, Hybrid, or Electric.',
          'coe cycles': 'Number of COE renewal cycles the vehicle has gone through.',
          'coe renewed': 'Whether the vehicle\'s COE has been renewed beyond the initial 10-year period.',
          'classic car': 'Vehicles over 35 years old that qualify for classic car status with special regulations.'
        },
        demandInsightsDefinitions: {
          'average premium (last quarter)': 'Mean of COE premium prices across Categories A & B in the last 3 calendar months (6 bidding rounds).',
          'coe growth rate (last quarter)': 'Percentage change of average premium in the last 3 calendar months (6 bidding rounds) compared to the previous quarter.',
          'coe growth rate': 'The COE premium change represents the percentage increase or decrease in COE prices compared to the previous bidding exercise.', 
          'coe success rate': 'Percentage of successful bids out of total bids submitted in a COE bidding round.',
          'quota': 'Number of COE certificates available for bidding in each exercise, set by LTA.',
          'bids success': 'Total number of successful bids that secured COE certificates.',
          'bids received': 'Total number of bids submitted during a COE bidding exercise.',
          'bid-quota ratio': 'Bid-to-Quota Ratio (BQR) is the ratio of total bids received to available quota (Bids ÷ Quota). Higher BQR indicates more competition.',
          'market share by make': 'Percentage distribution of vehicle registrations by car manufacturer/brand.',
          'make growth': 'Percentage change in registrations for specific car makes over time.',
          'car ownership transfers by make': 'Number of vehicle ownership changes segmented by car manufacturer.',
          'coe': 'Certificate of Entitlement (COE) is a quota license required to own and use a vehicle in Singapore for 10 years.',
          'premium': 'COE Premium is the price paid for a COE certificate through the bidding system.',
          'category a': 'Category A COE is for cars with engine capacity ≤1600cc and maximum power ≤130bhp.',
          'category b': 'Category B COE is for cars with engine capacity >1600cc or maximum power >130bhp.',
        },
      }
    }
  },
  methods: {
    toggleChatbot() {
      this.isVisible = !this.isVisible;
      if (this.isVisible) {
        this.initializeChat();
        this.$nextTick(() => {
          this.scrollToBottom();
        });
      }
    },
    
    showAutoGreeting() {
      if (!this.hasShownGreeting) {
        this.showGreeting = true;
        this.hasShownGreeting = true;
        
        setTimeout(() => {
          this.showGreeting = false;
        }, 4000);
      }
    },
    
    initializeChat() {
      this.currentStep = 'start';
      this.currentOptions = [
        { text: 'Car Features Analytics', value: 'car-features' },
        { text: 'Demand Insights', value: 'demand-insights' }
      ];
    },
    
    async selectOption(option) {
      // Add user message
      this.messages.push({
        type: 'user',
        content: option.text,
        timestamp: new Date()
      });
      
      this.currentOptions = [];
      this.isTyping = true;
      this.scrollToBottom();
      
      await new Promise(resolve => setTimeout(resolve, 800));
      
      this.handleOptionSelection(option.value);
      this.isTyping = false;
      this.scrollToBottom();
    },
    
    handleOptionSelection(value) {
      switch (this.currentStep) {
        case 'start':
          this.currentStep = 'category-selected';
          this.selectedCategory = value;
          this.messages.push({
            type: 'bot',
            content: 'What do you need assistance with?',
            timestamp: new Date()
          });
          if (this.selectedCategory === 'car-features') {
            this.currentOptions = [
              { text: 'Definitions', value: 'definitions' },
              { text: 'Interpretation of Metrics', value: 'interpretation' }
            ];
          } else {
            this.currentOptions = [
              { text: 'Definitions', value: 'definitions' },
              { text: 'Interpretation of Metrics', value: 'interpretation' },
              { text: 'Fetching Data', value: 'data' }
            ];
          }
          break;
          
        case 'category-selected':
          this.currentStep = 'assistance-type';
          if (value === 'definitions') {
            this.messages.push({
              type: 'bot',
              content: 'What definition do you need?',
              timestamp: new Date()
            });
            
            if (this.selectedCategory === 'car-features') {
              this.currentOptions = [
                { text: 'Make', value: 'def-make' },
                { text: 'Mileage', value: 'def-mileage' },
                { text: 'OMV', value: 'def-omv' },
                { text: 'ARF', value: 'def-arf' },
                { text: 'Engine Capacity', value: 'def-engine capacity' },
                { text: 'Horse Power', value: 'def-horse power' },
                { text: 'Road Tax Payable', value: 'def-road tax payable' },
                { text: 'COE Paid', value: 'def-coe paid' },
                { text: 'Transmission', value: 'def-transmission' },
                { text: 'Fuel Type', value: 'def-fuel type' },
                { text: 'COE Cycles', value: 'def-coe cycles' },
                { text: 'COE Renewed', value: 'def-coe renewed' },
                { text: 'Classic Car', value: 'def-classic car' }
              ];
            } else {
              this.currentOptions = [
                { text: 'COE', value: 'coe' },
                { text: 'Premium', value: 'premium' },
                { text: 'Category A', value: 'category a' },
                { text: 'Category B', value: 'category b' },
                { text: 'Average Premium (Last Quarter)', value: 'def-average premium (last quarter)' },
                { text: 'COE Growth Rate (Last Quarter)', value: 'def-coe growth rate (last quarter)' },
                { text: 'COE Growth Rate', value: 'def-coe growth rate' },
                { text: 'COE Success Rate', value: 'def-coe success rate' },
                { text: 'Quota', value: 'def-quota' },
                { text: 'Bids Success', value: 'def-bids success' },
                { text: 'Bids Received', value: 'def-bids received' },
                { text: 'Bid-Quota Ratio', value: 'def-bid-quota ratio' },
                { text: 'Market Share by Make', value: 'def-market share by make' },
                { text: 'Make Growth', value: 'def-make growth' },
                { text: 'Car Ownership Transfers by Make', value: 'def-car ownership transfers by make' }
              ];
            }
          } else if (value === 'interpretation') {
            this.messages.push({
              type: 'bot',
              content: 'What metric would you like to interpret?',
              timestamp: new Date()
            });
            
            if (this.selectedCategory === 'car-features') {
              this.currentOptions = [
                { text: 'Price trend with COE years left', value: 'int-coe-years' },
                { text: 'Price trend vs the number of previous owners', value: 'int-owners' },
                { text: 'Price trend with OMV/ARF', value: 'int-omv-arf' }
              ];
            } else {
              this.currentOptions = [
                { text: 'BQR Values', value: 'int-bqr' },
                { text: 'Premium Levels', value: 'int-premium' },
                { text: 'Growth Rates', value: 'int-growth' },
                { text: 'Market Trends', value: 'int-trends' },
                { text: 'Category Comparison', value: 'int-compare' }
              ];
            }
          } else if (value === 'data') {
            this.messages.push({
              type: 'bot',
              content: 'What data do you need?',
              timestamp: new Date()
            });
            
            if (this.selectedCategory === 'demand-insights') {
              this.currentOptions = [
                { text: 'Latest Premium', value: 'data-latest' },
                { text: 'Fetch COE Data', value: 'data-coe-download' },
                { text: 'Fetch Average COE Data', value: 'data-avg-coe-download' },
                { text: 'Fetch Car Make Data', value: 'data-make-download' }
              ];
            } else {
              this.currentOptions = [
                { text: 'Fetch Car Make Data', value: 'data-make-download' },
                { text: 'Download All Resale Car Data', value: 'data-resale-download' }
              ];
            }
          }
          break;
          
        case 'assistance-type':
          if (value === 'data-coe-download') {
            this.currentStep = 'coe-start-year';
            this.dataType = value;
            this.messages.push({
              type: 'bot',
              content: 'Select start year:',
              timestamp: new Date()
            });
            this.currentOptions = [];
            for (let year = 2010; year <= 2025; year++) {
              this.currentOptions.push({ text: year.toString(), value: `start-${year}` });
            }
          } else if (value === 'data-resale-download') {
            this.currentStep = 'resale-confirm';
            this.dataType = value;
            this.messages.push({
              type: 'bot',
              content: 'Do you want to download all resale car data from Motorist, Carro and SGCarMart platforms?',
              timestamp: new Date()
            });
            this.currentOptions = [
              { text: 'Yes', value: 'resale-yes' },
              { text: 'No', value: 'resale-no' }
            ];
          } else if (value === 'data-avg-coe-download') {
            this.currentStep = 'avg-coe-type';
            this.dataType = value;
            this.messages.push({
              type: 'bot',
              content: 'Would you like monthly or yearly COE premium averages?',
              timestamp: new Date()
            });
            this.currentOptions = [
              { text: 'Monthly', value: 'avg-monthly' },
              { text: 'Yearly', value: 'avg-yearly' }
            ];
          } else if (value === 'data-make-download') {
            this.currentStep = 'make-start-year';
            this.dataType = value;
            this.messages.push({
              type: 'bot',
              content: 'Select start year:',
              timestamp: new Date()
            });
            this.currentOptions = [];
            for (let year = 2005; year <= 2024; year++) {
              this.currentOptions.push({ text: year.toString(), value: `start-${year}` });
            }
          } else {
            this.handleFinalSelection(value);
          }
          break;
          
        case 'coe-start-year':
          this.selectedStartYear = parseInt(value.replace('start-', ''));
          this.currentStep = 'coe-end-year';
          this.messages.push({
            type: 'bot',
            content: 'Select end year:',
            timestamp: new Date()
          });
          this.currentOptions = [];
          for (let year = this.selectedStartYear; year <= 2025; year++) {
            this.currentOptions.push({ text: year.toString(), value: `end-${year}` });
          }
          break;
          
        case 'coe-end-year':
          const endYear = parseInt(value.replace('end-', ''));
          this.handleCOEDownload(this.selectedStartYear, endYear);
          break;
          
        case 'make-start-year':
          this.selectedStartYear = parseInt(value.replace('start-', ''));
          this.currentStep = 'make-end-year';
          this.messages.push({
            type: 'bot',
            content: 'Select end year:',
            timestamp: new Date()
          });
          this.currentOptions = [];
          for (let year = this.selectedStartYear; year <= 2024; year++) {
            this.currentOptions.push({ text: year.toString(), value: `end-${year}` });
          }
          break;
          
        case 'make-end-year':
          const makeEndYear = parseInt(value.replace('end-', ''));
          this.handleMakeDownload(this.selectedStartYear, makeEndYear);
          break;
          
        case 'avg-coe-type':
          this.avgType = value.replace('avg-', '');
          this.currentStep = 'avg-coe-start-year';
          this.messages.push({
            type: 'bot',
            content: 'Select start year:',
            timestamp: new Date()
          });
          this.currentOptions = [];
          for (let year = 2010; year <= 2025; year++) {
            this.currentOptions.push({ text: year.toString(), value: `start-${year}` });
          }
          break;
          
        case 'avg-coe-start-year':
          this.selectedStartYear = parseInt(value.replace('start-', ''));
          this.currentStep = 'avg-coe-end-year';
          this.messages.push({
            type: 'bot',
            content: 'Select end year:',
            timestamp: new Date()
          });
          this.currentOptions = [];
          for (let year = this.selectedStartYear; year <= 2025; year++) {
            this.currentOptions.push({ text: year.toString(), value: `end-${year}` });
          }
          break;
          
        case 'avg-coe-end-year':
          const avgEndYear = parseInt(value.replace('end-', ''));
          this.handleAvgCOEDownload(this.selectedStartYear, avgEndYear, this.avgType);
          break;
          
        case 'resale-confirm':
          if (value === 'resale-yes') {
            this.handleResaleDownload();
          } else {
            this.messages.push({
              type: 'bot',
              content: 'Download cancelled.',
              timestamp: new Date()
            });
            setTimeout(() => {
              this.messages.push({
                type: 'bot',
                content: 'Is there anything else I can help you with?',
                timestamp: new Date()
              });
              this.initializeChat();
            }, 2000);
          }
          break;
      }
    },
    
    async handleFinalSelection(value) {
      let response = '';
      
      // Handle definitions
      if (value.startsWith('def-')) {
        const term = value.replace('def-', '');
        let definition = '';
        
        if (this.selectedCategory === 'car-features') {
          definition = this.knowledgeBase.carFeaturesDefinitions[term];
        } else {
          definition = this.knowledgeBase.demandInsightsDefinitions[term] || this.knowledgeBase.definitions[term];
        }
        
        response = definition ? `<strong>${term.toUpperCase()}:</strong> ${definition}` : 'Definition not found.';
      }
      // Handle interpretations
      else if (value.startsWith('int-')) {
        switch (value) {
          case 'int-coe-years':
            response = '<strong>Price increases with more COE years left</strong> because buyers are willing to pay a premium for vehicles with longer remaining COE validity. More COE years means the buyer can use the car longer before needing to renew the expensive COE certificate, making it a more valuable asset.';
            break;
          case 'int-owners':
            response = '<strong>Price decreases with more previous owners</strong> because multiple ownership changes often indicate potential reliability issues, higher wear and tear, or difficulty in reselling. Cars with fewer owners are perceived as better maintained and more reliable.';
            break;
          case 'int-omv-arf':
            response = '<strong>Price increases with higher OMV/ARF</strong> because these reflect the original value and tax paid on the vehicle. Higher OMV indicates a more expensive, premium vehicle, while higher ARF shows significant government taxes paid, both contributing to the car\'s inherent value and resale price.';
            break;
          case 'int-bqr':
            response = '<strong>BQR Interpretation:</strong><br/>• Below 1.3: Low competition<br/>• 1.3-1.7: Moderate competition<br/>• Above 1.7: High competition';
            break;
          case 'int-premium':
            response = '<strong>Premium Levels:</strong><br/>Based on 2025 data only,<br/>• Low: Below $65k<br/>• Moderate: $65k-$118k<br/>• Above $118k: High';
            break;
          case 'int-growth':
            response = '<strong>Growth Rate Interpretation:</strong><br/>Positive growth indicates increasing demand and prices, while negative growth suggests market cooling.';
            break;
          case 'int-trends':
            response = '<strong>Market Trends:</strong><br/>COE trends are influenced by quota supply, economic conditions, and vehicle demand cycles.';
            break;
          case 'int-compare':
            response = 'Category B premiums are typically higher than Category A due to larger engine capacity and higher demand for luxury vehicles.';
            break;
        }
      }
      // Handle data requests
      else if (value.startsWith('data-')) {
        switch (value) {
          case 'data-latest':
            response = await this.getLastPremium();
            break;

        }
      }
      
      this.messages.push({
        type: 'bot',
        content: response,
        timestamp: new Date()
      });
      
      // Reset to start
      setTimeout(() => {
        this.messages.push({
          type: 'bot',
          content: 'Is there anything else I can help you with?',
          timestamp: new Date()
        });
        this.initializeChat();
      }, 2000);
    },
    
    async handleCOEDownload(startYear, endYear) {
      const csvData = await this.generateCOECSV(startYear, endYear);
      this.downloadCSV(csvData, `COE_Data_${startYear}_${endYear}.csv`);
      
      this.messages.push({
        type: 'bot',
        content: `<strong>COE Data Downloaded!</strong><br/>File: COE_Data_${startYear}_${endYear}.csv<br/>Columns: Bidding_Date, Vehicle_Class, Quota, Bids_Success, Bids_Received, Premium`,
        timestamp: new Date()
      });
      
      setTimeout(() => {
        this.messages.push({
          type: 'bot',
          content: 'Is there anything else I can help you with?',
          timestamp: new Date()
        });
        this.initializeChat();
      }, 2000);
    },
    
    async handleMakeDownload(startYear, endYear) {
      const csvData = await this.generateMakeCSV(startYear, endYear);
      this.downloadCSV(csvData, `Car_Make_Data_${startYear}_${endYear}.csv`);
      
      this.messages.push({
        type: 'bot',
        content: `<strong>Car Make Data Downloaded!</strong><br/>File: Car_Make_Data_${startYear}_${endYear}.csv<br/>Columns: Year, Make, Fuel_Type, Number`,
        timestamp: new Date()
      });
      
      setTimeout(() => {
        this.messages.push({
          type: 'bot',
          content: 'Is there anything else I can help you with?',
          timestamp: new Date()
        });
        this.initializeChat();
      }, 2000);
    },
    
    async handleAvgCOEDownload(startYear, endYear, avgType) {
      const csvData = await this.generateAvgCOECSV(startYear, endYear, avgType);
      this.downloadCSV(csvData, `COE_${avgType}_Averages_${startYear}_${endYear}.csv`);
      
      this.messages.push({
        type: 'bot',
        content: `<strong>COE ${avgType.charAt(0).toUpperCase() + avgType.slice(1)} Averages Downloaded!</strong><br/>File: COE_${avgType}_Averages_${startYear}_${endYear}.csv<br/>Period: ${startYear}-${endYear}`,
        timestamp: new Date()
      });
      
      setTimeout(() => {
        this.messages.push({
          type: 'bot',
          content: 'Is there anything else I can help you with?',
          timestamp: new Date()
        });
        this.initializeChat();
      }, 2000);
    },
    
    async generateAvgCOECSV(startYear, endYear, avgType) {
      try {
        const response = await fetch('https://data.gov.sg/api/action/datastore_search?resource_id=d_69b3380ad7e51aff3a7dcc84eba52b8a&limit=10000');
        const data = await response.json();
        
        if (!data.result || !data.result.records) {
          return 'Period,Category_A_Avg,Category_B_Avg\nError: Invalid API response';
        }
        
        const filteredData = data.result.records.filter(row => {
          const year = parseInt(row.month.split('-')[0]);
          return year >= startYear && year <= endYear && row.premium && row.premium.trim() !== '';
        });
        
        const groupedData = {};
        
        filteredData.forEach(row => {
          const [year, month] = row.month.split('-');
          let key;
          
          if (avgType === 'monthly') {
            key = `${year}-${month}`;
          } else {
            key = year;
          }
          
          if (!groupedData[key]) {
            groupedData[key] = { catA: [], catB: [] };
          }
          
          const cleanPremium = parseFloat(row.premium.replace(/,/g, ''));
          if (!isNaN(cleanPremium)) {
            if (row.vehicle_class === 'Category A') {
              groupedData[key].catA.push(cleanPremium);
            } else if (row.vehicle_class === 'Category B') {
              groupedData[key].catB.push(cleanPremium);
            }
          }
        });
        
        const csvHeader = avgType === 'monthly' ? 
          'Year_Month,Category_A_Avg,Category_B_Avg\n' : 
          'Year,Category_A_Avg,Category_B_Avg\n';
          
        const csvRows = Object.keys(groupedData).sort().map(period => {
          const catAAvg = groupedData[period].catA.length > 0 ? 
            Math.round(groupedData[period].catA.reduce((sum, p) => sum + p, 0) / groupedData[period].catA.length) : '';
          const catBAvg = groupedData[period].catB.length > 0 ? 
            Math.round(groupedData[period].catB.reduce((sum, p) => sum + p, 0) / groupedData[period].catB.length) : '';
          
          return `${period},${catAAvg},${catBAvg}`;
        }).join('\n');
        
        return csvHeader + csvRows;
      } catch (error) {
        console.error('Error generating Average COE CSV:', error);
        return 'Period,Category_A_Avg,Category_B_Avg\nError fetching data';
      }
    },
    
    async generateCOECSV(startYear, endYear) {
      try {
        const response = await fetch('https://data.gov.sg/api/action/datastore_search?resource_id=d_69b3380ad7e51aff3a7dcc84eba52b8a&limit=10000');
        const data = await response.json();
        
        if (!data.result || !data.result.records) {
          return 'Month,Bidding_No,Vehicle_Class,Quota,Bids_Success,Bids_Received,Premium\nError: Invalid API response';
        }
        
        const filteredData = data.result.records.filter(row => {
          const year = parseInt(row.month.split('-')[0]);
          return year >= startYear && year <= endYear && 
                 (row.vehicle_class === 'Category A' || row.vehicle_class === 'Category B');
        });
        
        const csvHeader = 'Month,Bidding_No,Vehicle_Class,Quota,Bids_Success,Bids_Received,Premium\n';
        const csvRows = filteredData.map(row => {
          const cleanQuota = (row.quota || '').replace(/,/g, '');
          const cleanBidsSuccess = (row.bids_success || '').replace(/,/g, '');
          const cleanBidsReceived = (row.bids_received || '').replace(/,/g, '');
          const cleanPremium = (row.premium || '').replace(/,/g, '');
          
          return `${row.month},${row.bidding_no || ''},${row.vehicle_class || ''},${cleanQuota},${cleanBidsSuccess},${cleanBidsReceived},${cleanPremium}`;
        }).join('\n');
        
        return csvHeader + csvRows;
      } catch (error) {
        console.error('Error generating COE CSV:', error);
        return 'Month,Bidding_No,Vehicle_Class,Quota,Bids_Success,Bids_Received,Premium\nError fetching data';
      }
    },
    
    async generateMakeCSV(startYear, endYear) {
      try {
        const response = await fetch('https://data.gov.sg/api/action/datastore_search?resource_id=d_20d3fc7f08caa581c5586df51a8993c5&limit=10000');
        const data = await response.json();
        
        console.log('API Response:', data);
        
        if (!data.result || !data.result.records) {
          console.error('Invalid API response structure:', data);
          return 'Year,Make,Fuel_Type,Number\nError: Invalid API response';
        }
        
        const allRecords = data.result.records;
        console.log('Total records:', allRecords.length);
        console.log('Sample record:', allRecords[0]);
        
        const filteredData = allRecords.filter(row => {
          const year = parseInt(row.year);
          return year >= startYear && year <= endYear;
        });
        
        console.log('Filtered records:', filteredData.length);
        
        const csvHeader = 'Year,Make,Fuel_Type,Number\n';
        const csvRows = filteredData.map(row => 
          `${row.year},"${row.make}","${row.fuel_type}",${row.number}`
        ).join('\n');
        
        return csvHeader + csvRows;
      } catch (error) {
        console.error('Error generating Make CSV:', error);
        return 'Year,Make,Fuel_Type,Number\nError fetching data';
      }
    },
    
    downloadCSV(csvData, filename) {
      const blob = new Blob([csvData], { type: 'text/csv' });
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
    },

    async getLastPremium() {
      try {
        const response = await fetch('https://data.gov.sg/api/action/datastore_search?resource_id=d_69b3380ad7e51aff3a7dcc84eba52b8a&limit=10000');
        const data = await response.json();
        
        if (data.result && data.result.records && data.result.records.length > 0) {
          const sortedRows = data.result.records
            .filter(r => r.premium && r.month && r.vehicle_class)
            .sort((a, b) => new Date(b.month) - new Date(a.month));
          
          if (sortedRows.length > 0) {
            const latestMonth = sortedRows[0].month;
            const latestData = sortedRows.filter(r => r.month === latestMonth);
            
            const catA = latestData.find(r => r.vehicle_class === 'Category A');
            const catB = latestData.find(r => r.vehicle_class === 'Category B');
            
            let result = `<strong>${latestMonth}</strong><br/>`;
            if (catA) {
              const cleanPremium = parseFloat(catA.premium.replace(/,/g, ''));
              result += `Cat A: ${cleanPremium.toLocaleString()}<br/>`;
            }
            if (catB) {
              const cleanPremium = parseFloat(catB.premium.replace(/,/g, ''));
              result += `Cat B: ${cleanPremium.toLocaleString()}`;
            }
            
            return result;
          }
        }
      } catch (error) {
        console.error('Error fetching last premium:', error);
      }
      
      return 'Unable to fetch the latest premium data.';
    },
    
    async getYearlyAverage() {
      try {
        const response = await fetch('https://data.gov.sg/api/action/datastore_search?resource_id=d_69b3380ad7e51aff3a7dcc84eba52b8a&limit=10000');
        const data = await response.json();
        
        if (data.rows && data.rows.length > 0) {
          const currentYear = new Date().getFullYear();
          const yearData = data.rows.filter(r => {
            const year = new Date(r.Bidding_Date).getFullYear();
            return year === currentYear && r.Premium && r.Vehicle_Class;
          });
          
          const catAData = yearData.filter(r => r.Vehicle_Class === 'Category A');
          const catBData = yearData.filter(r => r.Vehicle_Class === 'Category B');
          
          let result = `<strong>Average COE ${currentYear}:</strong><br/>`;
          
          if (catAData.length > 0) {
            const avgA = catAData.reduce((sum, r) => sum + parseFloat(r.Premium), 0) / catAData.length;
            result += `Cat A: ${Math.round(avgA).toLocaleString()}<br/>`;
          }
          
          if (catBData.length > 0) {
            const avgB = catBData.reduce((sum, r) => sum + parseFloat(r.Premium), 0) / catBData.length;
            result += `Cat B: ${Math.round(avgB).toLocaleString()}`;
          }
          
          return result;
        }
      } catch (error) {
        console.error('Error fetching yearly average:', error);
      }
      
      return 'Unable to calculate yearly average.';
    },
    
    formatTime(timestamp) {
      return timestamp.toLocaleTimeString('en-SG', { 
        hour: '2-digit', 
        minute: '2-digit' 
      });
    },
    
    scrollToBottom() {
      this.$nextTick(() => {
        const container = this.$refs.messagesContainer;
        if (container) {
          container.scrollTop = container.scrollHeight;
        }
      });
    }
  },
  
  mounted() {
    // Show auto-greeting after 2 seconds
    setTimeout(() => {
      this.showAutoGreeting();
    }, 2000);
  },
  
  watch: {
    messages: {
      handler() {
        this.$nextTick(() => {
          this.scrollToBottom();
        });
      },
      deep: true
    },
    
    currentOptions() {
      this.$nextTick(() => {
        this.scrollToBottom();
      });
    }
  }
}
</script>

<style scoped>
.greeting-popup {
  position: fixed;
  bottom: 100px;
  right: 20px;
  background: white;
  border-radius: 16px;
  padding: 16px 20px;
  box-shadow: 0 10px 30px rgba(0,0,0,0.2);
  z-index: 1001;
  animation: slideIn 0.5s ease-out;
  max-width: 280px;
  border: 1px solid #e8e8e8;
}

.greeting-content {
  display: flex;
  align-items: center;
  gap: 12px;
}

.greeting-logo {
  width: 48px;
  height: 48px;
  object-fit: contain;
}

.greeting-text {
  color: #333;
}

.greeting-title {
  font-weight: 600;
  font-size: 16px;
  margin-bottom: 4px;
}

.greeting-subtitle {
  font-size: 13px;
  opacity: 0.9;
  line-height: 1.3;
}

@keyframes slideIn {
  from {
    transform: translateX(100%);
    opacity: 0;
  }
  to {
    transform: translateX(0);
    opacity: 1;
  }
}

.chatbot-toggle {
  position: fixed;
  bottom: 20px;
  right: 20px;
  width: 64px;
  height: 64px;
  background: transparent;
  border: none;
  cursor: pointer;
  z-index: 1000;
  transition: all 0.3s ease;
  display: flex;
  align-items: center;
  justify-content: center;
}

.toggle-logo {
  width: 60px;
  height: 60px;
  object-fit: contain;
}

.chatbot-toggle:hover {
  transform: scale(1.1);
}

.chatbot-container {
  position: fixed;
  bottom: 100px;
  right: 20px;
  width: 380px;
  height: 500px;
  background: white;
  border-radius: 16px;
  box-shadow: 0 10px 40px rgba(0,0,0,0.15);
  display: flex;
  flex-direction: column;
  z-index: 1000;
  border: none;
  overflow: hidden;
  animation: chatbotSlideIn 0.3s ease-out;
}

@keyframes chatbotSlideIn {
  from {
    transform: translateY(-20px);
    opacity: 0;
  }
  to {
    transform: translateY(0);
    opacity: 1;
  }
}

.chatbot-header {
  padding: 16px 20px;
  background: #1890ff;
  color: white;
  border-radius: 16px 16px 0 0;
  display: flex;
  justify-content: space-between;
  align-items: center;
  position: relative;
}

.chatbot-header::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: linear-gradient(45deg, rgba(255,255,255,0.1) 0%, transparent 100%);
  pointer-events: none;
}

.chatbot-header h3 {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
}

.close-btn {
  background: none;
  border: none;
  color: white;
  font-size: 24px;
  cursor: pointer;
  padding: 0;
  width: 30px;
  height: 30px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  transition: background 0.2s;
}

.close-btn:hover {
  background: rgba(255,255,255,0.2);
  transform: rotate(90deg);
}

.chatbot-messages {
  flex: 1;
  padding: 16px;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.message {
  max-width: 85%;
  word-wrap: break-word;
}

.message.user {
  align-self: flex-end;
}

.message.user .message-content {
  background: #1890ff;
  color: white;
  padding: 12px 16px;
  border-radius: 20px 20px 6px 20px;
  box-shadow: 0 2px 8px rgba(24, 144, 255, 0.3);
  display: flex;
  align-items: center;
  justify-content: center;
  text-align: center;
  min-height: 40px;
}

.message.bot .message-content {
  background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
  color: #333;
  padding: 16px 20px;
  border-radius: 20px 20px 20px 6px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.05);
  border: 1px solid rgba(0,0,0,0.05);
  min-height: 40px;
  line-height: 1.5;
  word-wrap: break-word;
  white-space: pre-wrap;
}

.message-time {
  font-size: 11px;
  color: #999;
  margin-top: 4px;
  text-align: right;
}

.message.bot .message-time {
  text-align: left;
}

.typing-indicator {
  display: flex;
  gap: 4px;
  padding: 12px 16px;
  background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
  border-radius: 20px 20px 20px 6px;
  border: 1px solid rgba(0,0,0,0.05);
}

.typing-indicator span {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  animation: typing 1.4s infinite ease-in-out;
}

.typing-indicator span:nth-child(2) {
  animation-delay: 0.2s;
}

.typing-indicator span:nth-child(3) {
  animation-delay: 0.4s;
}

@keyframes typing {
  0%, 60%, 100% {
    transform: translateY(0);
    opacity: 0.5;
  }
  30% {
    transform: translateY(-10px);
    opacity: 1;
  }
}

.chatbot-options {
  padding: 16px;
  border-top: 1px solid rgba(0,0,0,0.05);
  display: flex;
  flex-direction: column;
  gap: 10px;
  max-height: 200px;
  overflow-y: auto;
  background: linear-gradient(180deg, rgba(248,249,250,0.5) 0%, transparent 100%);
}

.option-btn {
  padding: 16px 20px;
  background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
  border: 1px solid #dee2e6;
  border-radius: 12px;
  cursor: pointer;
  font-size: 14px;
  text-align: left;
  transition: all 0.3s ease;
  position: relative;
  overflow: hidden;
  min-height: 48px;
  line-height: 1.4;
  word-wrap: break-word;
}

.option-btn::before {
  content: '';
  position: absolute;
  top: 0;
  left: -100%;
  width: 100%;
  height: 100%;
  background: linear-gradient(90deg, transparent, rgba(102, 126, 234, 0.1), transparent);
  transition: left 0.5s;
}

.option-btn:hover {
  background: #1890ff;
  border-color: #1890ff;
  color: white;
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(24, 144, 255, 0.3);
}

.option-btn:hover::before {
  left: 100%;
}

@media (max-width: 768px) {
  .chatbot-container {
    width: calc(100vw - 40px);
    height: calc(100vh - 40px);
    bottom: 20px;
    right: 20px;
  }
  
  .chatbot-toggle {
    right: 20px;
    bottom: 20px;
  }
}
</style>