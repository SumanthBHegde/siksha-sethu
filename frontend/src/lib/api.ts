const API_BASE = "/api";

function token(): string | null {
  return localStorage.getItem("shiksha_token");
}

async function request<T = any>(path: string, options: RequestInit = {}): Promise<T> {
  const headers: Record<string, string> = {
    ...(options.headers as Record<string, string>),
  };
  if (!(options.body instanceof FormData) && !headers["Content-Type"]) {
    headers["Content-Type"] = "application/json";
  }
  const t = token();
  if (t) headers["Authorization"] = `Bearer ${t}`;

  const res = await fetch(`${API_BASE}${path}`, { ...options, headers });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || `${res.status} ${res.statusText}`);
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}

export const api = {
  login: (email: string, password: string) =>
    request<{ access_token: string; user: any }>("/auth/login-json", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }),

  register: (name: string, email: string, password: string, school_name: string) =>
    request<{ access_token: string; user: any }>("/auth/register", {
      method: "POST",
      body: JSON.stringify({ name, email, password, school_name }),
    }),

  me: () => request<any>("/auth/me"),

  dashboard: () => request<any>("/dashboard/home"),

  students: {
    list: () => request<any[]>("/students"),
    create: (payload: any) => request<any>("/students", { method: "POST", body: JSON.stringify(payload) }),
    delete: (id: number) => request<any>(`/students/${id}`, { method: "DELETE" }),
  },

  attendance: {
    summary: () => request<any>("/attendance/summary"),
    anomalies: () => request<any>("/attendance/anomalies"),
    byDate: (d: string) => request<any[]>(`/attendance/by-date?d=${d}`),
    bulk: (date: string, entries: { student_id: number; status: string }[]) =>
      request<any>("/attendance/bulk", { method: "POST", body: JSON.stringify({ date, entries }) }),
  },

  poshan: {
    summary: () => request<any>("/poshan/summary"),
    stockStatus: () => request<any>("/poshan/stock-status"),
    addMeal: (payload: any) => request<any>("/poshan/meals", { method: "POST", body: JSON.stringify(payload) }),
    addStock: (payload: any) => request<any>("/poshan/stock", { method: "POST", body: JSON.stringify(payload) }),
  },

  audit: {
    readiness: () => request<any>("/audit/readiness"),
    listDocs: () => request<any[]>("/audit/documents"),
    upload: (formData: FormData) => request<any>("/audit/documents", { method: "POST", body: formData }),
  },

  upload: {
    register: (formData: FormData) =>
      request<any>("/upload/register", { method: "POST", body: formData }),
    history: () => request<any[]>("/upload/history"),
  },

  chat: {
    send: (message: string) =>
      request<{ reply: string; agent: string; data?: any }>("/chat", {
        method: "POST",
        body: JSON.stringify({ message }),
      }),
    history: () => request<any[]>("/chat/history"),
  },
};

export { token };
