import axios from 'axios';

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || "/api/v1",
  headers: {
    "Content-Type": "application/json",
  },
  withCredentials: true,
});

let isRefreshing = false;
let failedQueue: any[] = [];

const processQueue = (error: any, token: string | null = null) => {
  failedQueue.forEach(prom => {
    if (error) {
      prom.reject(error);
    } else {
      prom.resolve(token);
    }
  });
  failedQueue = [];
};

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;
    
    // Prevent infinite loop if /auth/refresh fails or if it's a login attempt
    if ((originalRequest.url === '/auth/refresh' || originalRequest.url?.includes('/auth/login')) && error.response?.status === 401) {
       let msg = error.response?.data?.detail || error.response?.data?.error?.message || "Invalid email or password";
       return Promise.reject(new Error(typeof msg === 'string' ? msg : JSON.stringify(msg)));
    }

    if (error.response?.status === 401 && !originalRequest._retry && !originalRequest.url?.includes('/auth/login')) {
      if (isRefreshing) {
        return new Promise(function(resolve, reject) {
          failedQueue.push({resolve, reject});
        }).then(() => {
          return api(originalRequest);
        }).catch(err => {
          return Promise.reject(err);
        });
      }

      originalRequest._retry = true;
      isRefreshing = true;

      try {
        await api.post('/auth/refresh');
        processQueue(null, 'refreshed');
        return api(originalRequest);
      } catch (err) {
        processQueue(err, null);
        import('../store/authStore').then(({ useAuthStore }) => {
          if (useAuthStore.getState().isAuthenticated) {
            useAuthStore.getState().logout(true); // pass true to indicate it's forced
          }
        });
        return Promise.reject(err);
      } finally {
        isRefreshing = false;
      }
    }

    // Normalize error so catching it is cleaner
    let detailObj = error.response?.data?.detail;
    let message =
      error.response?.data?.error?.message ||
      (typeof detailObj === 'object' && detailObj?.message ? detailObj.message : (typeof detailObj === 'string' ? detailObj : null)) ||
      error.message ||
      "An unexpected network error occurred";
      
    if (Array.isArray(message)) {
      // FastAPI validation error array
      message = message.map((m: any) => {
        const field = m.loc && m.loc.length > 1 ? m.loc[m.loc.length - 1] : '';
        return field ? `${field}: ${m.msg}` : m.msg;
      }).join(", ");
    } else if (typeof message === 'object') {
      message = JSON.stringify(message);
    }
    
    const customError: any = new Error(message);
    customError.response = error.response;
    return Promise.reject(customError);
  },
);

export default api;
