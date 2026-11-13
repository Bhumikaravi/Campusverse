import { createContext, useContext, useEffect, useState } from "react";
import { authApi } from "../services/endpoints";

const AuthContext = createContext(null);

// Set to false to use the live FastAPI + MongoDB backend
const DEMO_MODE = false;

export function AuthProvider({ children }) {
  const [user, setUser] = useState(() => {
    const saved = localStorage.getItem("cv-user");
    return saved ? JSON.parse(saved) : null;
  });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (DEMO_MODE) {
      setLoading(false);
      return;
    }
    const token = localStorage.getItem("cv-token");
    authApi
      .me()
      .then((res) => {
        const currentUser = res.data?.user || res.data;
        setUser(currentUser);
        localStorage.setItem("cv-user", JSON.stringify(currentUser));
      })
      .catch(() => {
        if (!token) {
          localStorage.removeItem("cv-user");
          setUser(null);
        }
      })
      .finally(() => setLoading(false));
  }, []);

  const login = async (usernameOrEmail, password) => {
    if (DEMO_MODE) {
      const cleanName = usernameOrEmail.includes("@")
        ? usernameOrEmail.split("@")[0]
        : usernameOrEmail;
      const fakeUser = {
        id: "demo-usr-1",
        name: cleanName || "Student",
        email: usernameOrEmail.includes("@") ? usernameOrEmail : `${cleanName}@campusverse.edu`,
        role: "admin",
      };
      localStorage.setItem("cv-token", "demo-token");
      localStorage.setItem("cv-user", JSON.stringify(fakeUser));
      setUser(fakeUser);
      return fakeUser;
    }

    const res = await authApi.login({ email: usernameOrEmail, password });
    const { token, user: loggedInUser } = res.data;
    if (token) localStorage.setItem("cv-token", token);
    if (loggedInUser) {
      localStorage.setItem("cv-user", JSON.stringify(loggedInUser));
      setUser(loggedInUser);
    }
    return loggedInUser;
  };

  const register = async (payload) => {
    if (DEMO_MODE) {
      const fakeUser = { id: "demo-usr-2", name: payload.name, email: payload.email, role: "student" };
      localStorage.setItem("cv-token", "demo-token");
      localStorage.setItem("cv-user", JSON.stringify(fakeUser));
      setUser(fakeUser);
      return fakeUser;
    }

    const res = await authApi.register(payload);
    const { token, user: newUser } = res.data;
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