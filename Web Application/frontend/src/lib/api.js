// src/lib/api.js
import axios from "axios";

export const api = axios.create({
  baseURL: process.env.VUE_APP_API_BASE || "/api", // <-- Vue CLI style
  timeout: 20000,
});