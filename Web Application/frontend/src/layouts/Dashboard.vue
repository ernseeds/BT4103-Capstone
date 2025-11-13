<template>
  <div>
    <!-- Dashboard Layout -->
    <a-layout
      class="layout-dashboard"
      id="layout-dashboard"
      :class="[
        navbarFixed ? 'navbar-fixed' : '',
        !sidebarCollapsed ? 'has-sidebar' : '',
        layoutClass,
        isMobile ? 'is-mobile' : ''
      ]"
    >
      <!-- Main Sidebar -->
      <DashboardSidebar
        :sidebarCollapsed="sidebarCollapsed"
        :sidebarColor="sidebarColor"
        :sidebarTheme="sidebarTheme"
        @toggleSidebar="toggleSidebar"
      />
      <!-- / Main Sidebar -->

      <!-- Layout Content -->
      <a-layout>
        <!-- Header (keep yours) -->
        <DashboardHeader
          :sidebarCollapsed="sidebarCollapsed"
          :navbarFixed="navbarFixed"
          @toggleSidebar="toggleSidebar"
        />
        <!-- / Header -->

        <!-- Page Content -->
        <a-layout-content>
          <keep-alive>
            <router-view />
          </keep-alive>
        </a-layout-content>
        <!-- / Page Content -->

        <!-- Sidebar Overlay (only really needed when open) -->
        <div
          class="sidebar-overlay"
          @click="sidebarCollapsed = true"
          v-show="!sidebarCollapsed && isMobile"
        ></div>
        <!-- / Sidebar Overlay -->
      </a-layout>
      <!-- / Layout Content -->

      <!-- MOBILE HAMBURGER (always visible on mobile, above everything) -->
      <button
        v-if="isMobile"
        class="sidebar-fab"
        @click="toggleSidebar(!sidebarCollapsed)"
      >
        <span></span>
        <span></span>
        <span></span>
      </button>
    </a-layout>
    <!-- / Dashboard Layout -->
  </div>
</template>

<script>
import DashboardSidebar from '../components/Sidebars/DashboardSidebar'
import DashboardHeader from '../components/Headers/DashboardHeader'

export default {
  components: {
    DashboardSidebar,
    DashboardHeader,
  },
  data() {
    return {
      // start open on desktop
      sidebarCollapsed: false,
      sidebarColor: 'primary',
      sidebarTheme: 'light',
      navbarFixed: false,
      isMobile: false,
    }
  },
  computed: {
    layoutClass() {
      return this.$route.meta.layoutClass
    },
  },
  mounted() {
    this.checkIsMobile()
    window.addEventListener('resize', this.checkIsMobile)
  },
  beforeDestroy() {
    window.removeEventListener('resize', this.checkIsMobile)
  },
  methods: {
    toggleSidebar(value) {
      // child emits true/false, or we can toggle ourselves
      if (typeof value === 'boolean') {
        this.sidebarCollapsed = value
      } else {
        this.sidebarCollapsed = !this.sidebarCollapsed
      }
    },
    toggleNavbarPosition(value) {
      this.navbarFixed = value
    },
    updateSidebarTheme(value) {
      this.sidebarTheme = value
    },
    updateSidebarColor(value) {
      this.sidebarColor = value
    },
    checkIsMobile() {
      this.isMobile = window.innerWidth < 992
      // if we enter mobile, close it so it doesn't cover screen
      if (this.isMobile) {
        this.sidebarCollapsed = true
      }
    },
  },
}
</script>

<style scoped>
/* floating hamburger on mobile */
.sidebar-fab {
  position: fixed;
  top: 14px;
  left: 14px;
  z-index: 999;
  background: #fff;
  border: 1px solid #e5e7eb;
  border-radius: 999px;
  padding: 6px 8px;
  display: flex;
  flex-direction: column;
  gap: 3px;
  cursor: pointer;
  box-shadow: 0 4px 14px rgba(0,0,0,.08);
}
.sidebar-fab span {
  width: 20px;
  height: 2px;
  background: #111;
}

/* overlay already existed; just ensure it covers screen */
.sidebar-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0,0,0,.35);
  z-index: 998;
}
</style>
