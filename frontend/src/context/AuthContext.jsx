import { createContext, useContext, useEffect, useState } from "react";
import { authApi } from "../services/endpoints";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(() => {
    try {
      const saved = localStorage.getItem("cv-user");
      return saved ? JSON.parse(saved) : null;
    } catch {
      return null;
    }
  });
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const token = localStorage.getItem("cv-token");
    if (!token) {
      setLoading(false);
      return;
    }

    setLoading(true);
    authApi
      .me()
      .then((res) => {
        const currentUser = res.data?.user || res.data;
        if (currentUser) {
          setUser(currentUser);
          localStorage.setItem("cv-user", JSON.stringify(currentUser));
        }
      })
      .catch(() => {
        localStorage.removeItem("cv-token");
        localStorage.removeItem("cv-user");
        setUser(null);
      })
      .finally(() => setLoading(false));
  }, []);

  const login = async (usernameOrEmail, password) => {
    const res = await authApi.login({ email: usernameOrEmail, password });
    const { token, user: loggedInUser } = res.data || {};
    if (token) localStorage.setItem("cv-token", token);
    if (loggedInUser) {
      localStorage.setItem("cv-user", JSON.stringify(loggedInUser));
      setUser(loggedInUser);
    }
    return loggedInUser;
  };

  const register = async (payload) => {
    const res = await authApi.register(payload);
    const { token, user: newUser } = res.data || {};
    if (token) localStorage.setItem("cv-token", token);
    if (newUser) {
      localStorage.setItem("cv-user", JSON.stringify(newUser));
      setUser(newUser);
    }
    return newUser;
  };

  const logout = async () => {
    try {
      await authApi.logout();
    } catch {
      // Ignore network errors on logout
    } finally {
      localStorage.removeItem("cv-token");
      localStorage.removeItem("cv-user");
      setUser(null);
    }
  };

  const isAdmin = user?.role === "admin" || user?.role === "moderator";
  const isModerator = user?.role === "moderator";

  return (
    <AuthContext.Provider
      value={{
        user,
        loading,
        login,
        register,
        logout,
        isAdmin,
        isModerator,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export const useAuth = () => useContext(AuthContext);
