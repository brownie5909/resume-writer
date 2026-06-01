console.log("Hire Ready dashboard.js loaded");

const HIRE_READY_API_BASE = "https://resume-writer.onrender.com";

function hireReadyGetToken() {
  return localStorage.getItem("hire_ready_token");
}
