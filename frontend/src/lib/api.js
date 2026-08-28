import axios from "axios";

export const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
export const API = `${BACKEND_URL}/api`;

// Auth is driven by the backend's httpOnly `session_token` cookie (set on signup/login
// and OAuth). `withCredentials: true` sends it on every request. We intentionally do NOT
// store the JWT in localStorage — this closes the XSS-exfiltration path.
const api = axios.create({ baseURL: API, withCredentials: true });

api.interceptors.response.use(
  (r) => r,
  (err) => Promise.reject(err)
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
