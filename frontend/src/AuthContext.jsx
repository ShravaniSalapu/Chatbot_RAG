import { createContext, useContext, useState, useEffect } from "react";
import { getAccessToken, getStoredUser, logoutUser, getCurrentUser } from "./api";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [role, setRole] = useState(null);
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadAuth() {
      try {
        const token = getAccessToken();
        if (!token) {
          setLoading(false);
          return;
        }

        const storedUser = getStoredUser();
        if (storedUser) {
          setUser(storedUser);
          setRole(storedUser.role);
          setIsAuthenticated(true);
          setLoading(false);
          return;
        }

        setLoading(false);
      } catch (error) {
        console.error("Auth check failed:", error);
        setLoading(false);
      }
    }

    loadAuth();
  }, []);

  const login = async (email, password) => {
    const { loginUser } = await import("./api");
    const data = await loginUser(email, password);
    const storedUser = getStoredUser();
    setUser(storedUser);
    setRole(storedUser.role);
    setIsAuthenticated(true);
    return data;
  };

  const logout = () => {
    logoutUser();
    setUser(null);
    setRole(null);
    setIsAuthenticated(false);
  };

  const refreshUser = async () => {
    try {
      const currentUser = await getCurrentUser();
      const updatedUser = {
        user_id: currentUser.id,
        tenant_id: currentUser.tenant_id,
        email: currentUser.email,
        full_name: currentUser.full_name,
        role: currentUser.role,
      };
      setUser(updatedUser);
      setRole(currentUser.role);
      localStorage.setItem("user", JSON.stringify(updatedUser));
    } catch (error) {
      console.error("Failed to refresh user:", error);
      logout();
    }
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        role,
        isAuthenticated,
        loading,
        login,
        logout,
        refreshUser,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}