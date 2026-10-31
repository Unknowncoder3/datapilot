import axios from "axios";

const api = axios.create({ baseURL: "/api/v1", timeout: 30000 });

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

export default api;
