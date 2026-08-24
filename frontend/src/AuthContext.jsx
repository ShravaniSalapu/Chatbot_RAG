import {
  createContext,
  useContext,
  useState,
  useEffect,
} from "react";

import {
  getAccessToken,
  getStoredUser,
  logoutUser,
  getCurrentUser,
} from "./api";

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
          setRole(storedUser.role || "user");
          setIsAuthenticated(true);
          setLoading(false);
          return;
        }

        // Token exists but user data is missing.
        // Fetch the current user from backend.
        try {
          const currentUser = await getCurrentUser();

          const userData = {
            user_id: currentUser.id,
            tenant_id: currentUser.tenant_id,
            email: currentUser.email,
            full_name: currentUser.full_name,
            role: currentUser.role || "user",
          };

          localStorage.setItem(
            "user",
            JSON.stringify(userData)
          );

          setUser(userData);
          setRole(userData.role);
          setIsAuthenticated(true);
        } catch (error) {
          console.error(
            "Failed to restore authenticated user:",
            error
          );

          logoutUser();
          setUser(null);
          setRole(null);
          setIsAuthenticated(false);
        }

        setLoading(false);
      } catch (error) {
        console.error(
          "Auth check failed:",
          error
        );

        setUser(null);
        setRole(null);
        setIsAuthenticated(false);
        setLoading(false);
      }
    }

    loadAuth();
  }, []);

  const login = async (email, password) => {
    const { loginUser } = await import("./api");

    const data = await loginUser(
      email,
      password
    );

    const userData = {
      user_id: data.user_id,
      tenant_id: data.tenant_id,
      email: data.email,
      role: data.role || "user",
    };

    try {
      const currentUser =
        await getCurrentUser();

      userData.full_name =
        currentUser.full_name;

      userData.role =
        currentUser.role || data.role || "user";

      userData.user_id =
        currentUser.id || data.user_id;

      userData.tenant_id =
        currentUser.tenant_id ||
        data.tenant_id;

    } catch (error) {
      console.error(
        "Failed to fetch full user data:",
        error
      );

      userData.full_name =
        data.email?.split("@")[0] || "User";
    }

    localStorage.setItem(
      "user",
      JSON.stringify(userData)
    );

    setUser(userData);
    setRole(userData.role);
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
      const currentUser =
        await getCurrentUser();

      const updatedUser = {
        user_id: currentUser.id,
        tenant_id: currentUser.tenant_id,
        email: currentUser.email,
        full_name: currentUser.full_name,
        role: currentUser.role || "user",
      };

      setUser(updatedUser);
      setRole(updatedUser.role);

      localStorage.setItem(
        "user",
        JSON.stringify(updatedUser)
      );

      return updatedUser;
    } catch (error) {
      console.error(
        "Failed to refresh user:",
        error
      );

      logout();

      return null;
    }
  };

  const isAdmin =
    isAuthenticated &&
    role === "admin";

  const isUser =
    isAuthenticated &&
    role === "user";

  return (
    <AuthContext.Provider
      value={{
        user,
        role,
        isAdmin,
        isUser,
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
  const context =
    useContext(AuthContext);

  if (!context) {
    throw new Error(
      "useAuth must be used within an AuthProvider"
    );
  }

  return context;
}