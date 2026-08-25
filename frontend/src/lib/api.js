import axios from "axios";

export const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
export const API = `${BACKEND_URL}/api`;

const api = axios.create({ baseURL: API, withCredentials: true });

api.interceptors.request.use((config) => {
  const token = localStorage.getItem("bg_token");
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

api.interceptors.response.use(
  (r) => r,
  (err) => {
    if (err.response?.status === 401 && !window.location.pathname.startsWith("/auth")) {
      localStorage.removeItem("bg_token");
    }
    return Promise.reject(err);
  }
);

export default api;

export const CATEGORIES = [
  "Food & Water",
  "Tools",
  "Home",
  "Garden",
  "Transportation",
  "Clothing",
  "Electronics",
  "Outdoor & Camping",
  "Baby & Family",
  "Books & Education",
  "Building Materials",
  "Services & Skills",
  "Household",
  "Recreation",
  "Other",
];

export const KIND_META = {
  have: { label: "I HAVE", cls: "bg-accent text-accent-foreground", ring: "ring-accent" },
  need: { label: "I NEED", cls: "bg-secondary text-secondary-foreground", ring: "ring-secondary" },
  service: { label: "I CAN DO", cls: "bg-primary text-primary-foreground", ring: "ring-primary" },
};
