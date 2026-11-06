import axios from "axios";

const api = axios.create({
  baseURL: "/api/v1",
  // BI endpoints may profile large uploaded files before returning results.
  timeout: 120000,
});

export const getHealth = () => api.get("/health");
export const getDatasets = () => api.get("/datasets");
export const uploadDataset = (file, onUploadProgress) => {
  const body = new FormData();
  body.append("file", file);
  return api.post("/datasets/upload", body, {
    headers: { "Content-Type": "multipart/form-data" },
    onUploadProgress,
  });
};
export const getDataset = (id) => api.get(`/datasets/${id}`);
export const getProfile = (id) => api.get(`/datasets/${id}/profile`);
export const getPreview = (id) => api.get(`/datasets/${id}/preview`);
export const deleteDataset = (id) => api.delete(`/datasets/${id}`);

// Phase 2: analytics and interactive chart APIs.
export const getChartRecommendations = (datasetId) =>
  api.get(`/analytics/${datasetId}/charts/recommendations`);

export const getDatasetChart = (datasetId, params) =>
  api.get(`/analytics/${datasetId}/charts`, { params });

// Phase 3: business intelligence APIs.
export const getBusinessMapping = (datasetId) =>
  api.get(`/analytics/${datasetId}/bi/mapping`);

export const validateBusinessMapping = (datasetId, mapping) =>
  api.post(`/analytics/${datasetId}/bi/mapping`, mapping);

export const getBusinessKpis = (datasetId) =>
  api.get(`/analytics/${datasetId}/bi/kpis`);

export const getSalesTrends = (datasetId, frequency = "month") =>
  api.get(`/analytics/${datasetId}/bi/sales/trends`, {
    params: { frequency },
  });

export const getSalesByCountry = (datasetId, limit = 20) =>
  api.get(`/analytics/${datasetId}/bi/sales/countries`, {
    params: { limit },
  });

export const getTopProducts = (datasetId, limit = 20) =>
  api.get(`/analytics/${datasetId}/bi/sales/products`, {
    params: { limit },
  });

export const getCustomerIntelligence = (datasetId, limit = 20) =>
  api.get(`/analytics/${datasetId}/bi/customers`, {
    params: { limit },
  });

export const getCustomerRfm = (datasetId) =>
  api.get(`/analytics/${datasetId}/bi/customers/rfm`);

export const getProductIntelligence = (datasetId, limit = 20) =>
  api.get(`/analytics/${datasetId}/bi/products`, {
    params: { limit },
  });

export const runBusinessQuery = (datasetId, query) =>
  api.post(`/analytics/${datasetId}/bi/query`, query);

// Phase 4: insights, anomaly detection, drivers and recommendations.
export const getBusinessInsights = (datasetId, topN = 5) =>
  api.get(`/analytics/${datasetId}/bi/insights`, {
    params: { top_n: topN },
  });

export const getBusinessAnomalies = (
  datasetId,
  { sensitivity = 3.5, limit = 100, minPeriods = 14 } = {},
) =>
  api.get(`/analytics/${datasetId}/bi/anomalies`, {
    params: {
      sensitivity,
      limit,
      min_periods: minPeriods,
    },
  });

export const getBusinessDrivers = (
  datasetId,
  { topN = 10, frequency = "month" } = {},
) =>
  api.get(`/analytics/${datasetId}/bi/drivers`, {
    params: { top_n: topN, frequency },
  });

export const getRevenueRecommendations = (datasetId, params = {}) =>
  api.get(`/analytics/${datasetId}/bi/recommendations/revenue`, {
    params,
  });

export const getCustomerRecommendations = (datasetId, params = {}) =>
  api.get(`/analytics/${datasetId}/bi/recommendations/customers`, {
    params,
  });

export const getProductRecommendations = (datasetId, params = {}) =>
  api.get(`/analytics/${datasetId}/bi/recommendations/products`, {
    params,
  });

export const getMarketRecommendations = (datasetId, params = {}) =>
  api.get(`/analytics/${datasetId}/bi/recommendations/markets`, {
    params,
  });

export const getPrioritizedRecommendations = (datasetId, topN = 50) =>
  api.get(`/analytics/${datasetId}/bi/recommendations`, {
    params: { top_n: topN },
  });

export const getApiErrorMessage = (
  error,
  fallback = "Something went wrong. Please try again.",
) => {
  const detail = error?.response?.data?.detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return detail.map((item) => item.msg || "Invalid request").join(", ");
  }
  if (error?.code === "ECONNABORTED") {
    return "The request took too long. Try again or use a smaller dataset.";
  }
  if (!error?.response) {
    return "Cannot reach the DataPilot API. Check that the backend is running.";
  }
  return fallback;
};

export default api;


// Advanced BI dashboard: aggregated dataset visuals and dashboard filters.
export const getAdvancedDashboard = (datasetId, params = {}) =>
  api.get(`/analytics/${datasetId}/bi/advanced-dashboard`, { params });


// Phase 5.6: natural-language analytics questions.
export const askBusinessQuestion = (datasetId, question, conversation = []) =>
  api.post(`/analytics/${datasetId}/bi/ask`, { question, conversation });

// Phase 6: unified evidence-backed AI insights feed.
export const getUnifiedAIInsights = (datasetId, topN = 10) =>
  api.get(`/analytics/${datasetId}/bi/ai-insights`, { params: { top_n: topN } });


// Phase 8: baseline predictive analytics.
export const getRevenueForecast = (datasetId, { horizon = 6, frequency = "month" } = {}) =>
  api.get(`/analytics/${datasetId}/bi/forecast/revenue`, {
    params: { horizon, frequency },
  });


// Phase 12: automated reporting workspace.
export const createReport = (datasetId, payload) => api.post(`/datasets/${datasetId}/reports`, payload);
export const getDatasetReports = (datasetId, limit = 50) => api.get(`/datasets/${datasetId}/reports`, { params: { limit } });
export const getReport = (reportId) => api.get(`/reports/${reportId}`);
export const deleteReport = (reportId) => api.delete(`/reports/${reportId}`);
