import { useEffect, useState } from "react";
import {
  BrowserRouter,
  Routes,
  Route,
  NavLink,
  Navigate,
  useNavigate,
  useLocation,
} from "react-router-dom";

import KnowaLogo from "./KnowaLogo";
import Chatbots from "./Chatbots";
import Login from "./Login";
import Signup from "./Signup";
import InstallWidget from "./InstallWidget";
import ManageChatbot from "./ManageChatbot";
import KnowledgeBase from "./KnowledgeBase";
import ChatbotKnowledge from "./ChatbotKnowledge";
import { AuthProvider, useAuth } from "./AuthContext";
import { getChatbots, getDocuments, getUsage } from "./api";

function Dashboard() {
  const [stats, setStats] = useState({
    chatbots: 0,
    documents: 0,
    conversations: 0,
    totalMessages: 0,
  });
  const [loadingStats, setLoadingStats] = useState(true);
  const [statsError, setStatsError] = useState("");

  useEffect(() => {
    async function loadStats() {
      try {
        setLoadingStats(true);
        setStatsError("");

        const [chatbots, documents, usage] = await Promise.all([
          getChatbots(),
          getDocuments(),
          getUsage(),
        ]);

        setStats({
          chatbots: Array.isArray(chatbots) ? chatbots.length : 0,
          documents: Array.isArray(documents) ? documents.length : 0,
          conversations: usage?.chat_count ?? 0,
          totalMessages: usage?.api_call_count ?? 0,
        });
      } catch (err) {
        console.error("Dashboard stats error:", err);
        setStatsError(
          err?.message || "Unable to load dashboard statistics."
        );
      } finally {
        setLoadingStats(false);
      }
    }

    loadStats();
  }, []);

  return (
    <div>
      <PageHeader
        title="Dashboard"
        subtitle="Welcome back to KNOWA AI"
        action="+ Create Chatbot"
      />

      <section className="stats-grid">
        <StatCard
          icon="🤖"
          title="Total Chatbots"
          value={loadingStats ? "…" : stats.chatbots}
        />
        <StatCard
          icon="📄"
          title="Total Documents"
          value={loadingStats ? "…" : stats.documents}
        />
        <StatCard
          icon="💬"
          title="Conversations"
          value={loadingStats ? "…" : stats.conversations}
        />
        <StatCard
          icon="📈"
          title="Total Messages"
          value={loadingStats ? "…" : stats.totalMessages}
        />
      </section>

      {statsError && (
        <div className="dashboard-error">
          {statsError}
        </div>
      )}

      <section className="content-grid">
        <ContentCard
          title="My Chatbots"
          subtitle="Manage your AI chatbots"
          icon="🤖"
          emptyTitle="No chatbots yet"
          emptyText="Create your first KNOWA AI chatbot to get started."
          button="+ Create Chatbot"
        />

        <ContentCard
          title="Knowledge Base"
          subtitle="Your uploaded documents"
          icon="📚"
          emptyTitle="No documents yet"
          emptyText="Upload documents to give your chatbot knowledge."
          button="Upload Document"
        />
      </section>
    </div>
  );
}

function PlaceholderPage({ title, description }) {
  return (
    <div>
      <PageHeader
        title={title}
        subtitle={description}
      />

      <div className="page-placeholder">
        <div className="placeholder-icon">✨</div>

        <h2>{title}</h2>

        <p>
          This section will be connected to your KNOWA AI backend.
        </p>
      </div>
    </div>
  );
}

function ProtectedRoute({ children }) {
  const { isAuthenticated, loading } = useAuth();

  if (loading) {
    return (
      <div style={{
        minHeight: "100vh",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        background: "#f6f7fb"
      }}>
        <div className="loading-spinner"></div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  return children;
}

function AdminRoute({ children }) {
  const { isAuthenticated, role, loading } = useAuth();

  if (loading) {
    return (
      <div style={{
        minHeight: "100vh",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        background: "#f6f7fb"
      }}>
        <div className="loading-spinner"></div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  if (role !== "admin") {
    return <Navigate to="/dashboard" replace />;
  }

  return children;
}

function PageHeader({ title, subtitle, action }) {
  return (
    <header className="topbar">
      <div>
        <h1>{title}</h1>
        <p>{subtitle}</p>
      </div>

      {action && (
        <button className="create-button">
          {action}
        </button>
      )}
    </header>
  );
}

function StatCard({ icon, title, value }) {
  return (
    <div className="stat-card">
      <div className="stat-icon">
        {icon}
      </div>

      <div>
        <p>{title}</p>
        <h2>{value}</h2>
      </div>
    </div>
  );
}

function ContentCard({
  title,
  subtitle,
  icon,
  emptyTitle,
  emptyText,
  button,
}) {
  return (
    <div className="content-card">
      <div className="card-header">
        <div>
          <h2>{title}</h2>
          <p>{subtitle}</p>
        </div>

        <button className="outline-button">
          View All
        </button>
      </div>

      <div className="empty-state">
        <div className="empty-icon">
          {icon}
        </div>

        <h3>{emptyTitle}</h3>

        <p>{emptyText}</p>

        <button className="create-button">
          {button}
        </button>
      </div>
    </div>
  );
}

function Layout() {
  const navigate = useNavigate();
  const location = useLocation();
  const { user, role, logout, isAuthenticated } = useAuth();

  const handleLogout = () => {
    logout();
    navigate("/login", { replace: true });
  };

  const navigationItems = [
    {
      path: "/dashboard",
      icon: "⌂",
      label: "Dashboard",
    },
    {
      path: "/chatbots",
      icon: "🤖",
      label: "Chatbots",
    },
    {
      path: "/knowledge-base",
      icon: "📚",
      label: "Knowledge Base",
    },
    {
      path: "/conversations",
      icon: "💬",
      label: "Conversations",
    },
    {
      path: "/analytics",
      icon: "📊",
      label: "Analytics",
    },
    {
      path: "/appearance",
      icon: "🎨",
      label: "Appearance",
    },
    {
      path: "/settings",
      icon: "⚙️",
      label: "Settings",
    },
    {
      path: "/install-widget",
      icon: "🔗",
      label: "Install Widget",
    },
  ];

  const adminNavigationItems = [
    {
      path: "/admin/dashboard",
      icon: "👑",
      label: "Admin Dashboard",
    },
    {
      path: "/admin/users",
      icon: "👥",
      label: "Users",
    },
    {
      path: "/admin/activity",
      icon: "📋",
      label: "Activity Logs",
    },
    {
      path: "/admin/usage",
      icon: "📈",
      label: "Usage",
    },
  ];

  const allNavigationItems = role === "admin"
    ? [...navigationItems, ...adminNavigationItems]
    : navigationItems;

  // Redirect authenticated users from login/signup to dashboard
  useEffect(() => {
    if (isAuthenticated && (location.pathname === "/login" || location.pathname === "/signup")) {
      navigate("/dashboard", { replace: true });
    }
  }, [isAuthenticated, location.pathname, navigate]);

  function isNavItemActive(item) {
    if (item.path === "/install-widget") {
      return (
        location.pathname === "/install-widget" ||
        /^\/chatbots\/[^/]+\/install$/.test(
          location.pathname
        )
      );
    }

    if (item.path === "/chatbots") {
      return location.pathname.startsWith("/chatbots") &&
        !location.pathname.endsWith("/install");
    }

    return location.pathname === item.path;
  }

  return (
    <div className="app">

      {/* Sidebar */}
      <aside className="sidebar">

        <div className="brand">
          <KnowaLogo />
        </div>

        <nav className="sidebar-nav">

          {allNavigationItems.map((item) => (
            <NavLink
              key={item.path}
              to={item.path}
              className={() =>
                `nav-item ${isNavItemActive(item) ? "active" : ""}`
              }
            >
              <span className="nav-icon">
                {item.icon}
              </span>

              <span className="nav-label">
                {item.label}
              </span>
            </NavLink>
          ))}

        </nav>

        <div className="sidebar-bottom">

          <div className="user-card">

            <div className="user-avatar">
              {user?.full_name?.charAt(0).toUpperCase() || user?.email?.charAt(0).toUpperCase() || "U"}
            </div>

            <div>
              <div className="user-name">
                {user?.full_name || user?.email || "User"}
              </div>

              <div className="user-role">
                {role ? role.charAt(0).toUpperCase() + role.slice(1) : "User"}
              </div>
            </div>

            <button
              onClick={handleLogout}
              style={{
                marginLeft: "auto",
                border: "none",
                background: "none",
                cursor: "pointer",
                fontSize: "16px",
                color: "#64748b",
                padding: "4px",
                borderRadius: "4px",
              }}
              title="Logout"
            >
              🚪
            </button>

          </div>

        </div>

      </aside>

      {/* Main */}
      <main className="main-content">

        <Routes>

          <Route
            path="/"
            element={<Dashboard />}
          />

          <Route
            path="/dashboard"
            element={<Dashboard />}
          />

         <Route
            path="/chatbots"
            element={<Chatbots />}
          />
          <Route
            path="/chatbots/:chatbotId/knowledge"
            element={<ChatbotKnowledge />}
          />
          <Route
            path="/chatbots/:chatbotId"
            element={<ManageChatbot />}
          />
          <Route
            path="/knowledge-base"
            element={<KnowledgeBase />}
          />

          <Route
            path="/conversations"
            element={
              <PlaceholderPage
                title="Conversations"
                description="View and manage chatbot conversations"
              />
            }
          />

          <Route
            path="/analytics"
            element={
              <PlaceholderPage
                title="Analytics"
                description="Monitor chatbot performance"
              />
            }
          />

          <Route
            path="/appearance"
            element={
              <PlaceholderPage
                title="Appearance"
                description="Customize your chatbot appearance"
              />
            }
          />

          <Route
            path="/settings"
            element={
              <PlaceholderPage
                title="Settings"
                description="Manage your KNOWA AI settings"
              />
            }
          />

          <Route
            path="/install-widget"
            element={<InstallWidget />}
          />

          <Route
            path="/chatbots/:chatbotId/install"
            element={<InstallWidget />}
          />

          {/* Admin Routes */}
          <Route
            path="/admin/dashboard"
            element={
              <AdminRoute>
                <PlaceholderPage
                  title="Admin Dashboard"
                  description="Admin overview and management"
                />
              </AdminRoute>
            }
          />
          <Route
            path="/admin/users"
            element={
              <AdminRoute>
                <PlaceholderPage
                  title="Users"
                  description="Manage platform users"
                />
              </AdminRoute>
            }
          />
          <Route
            path="/admin/activity"
            element={
              <AdminRoute>
                <PlaceholderPage
                  title="Activity Logs"
                  description="View system activity and audit logs"
                />
              </AdminRoute>
            }
          />
          <Route
            path="/admin/usage"
            element={
              <AdminRoute>
                <PlaceholderPage
                  title="Usage"
                  description="Monitor platform usage statistics"
                />
              </AdminRoute>
            }
          />

        </Routes>

      </main>

    </div>
  );
}


function App() {

  return (

    <BrowserRouter>

      <AuthProvider>

        <Routes>

          {/* Public Routes */}

          <Route
            path="/login"
            element={<Login />}
          />

          <Route
            path="/signup"
            element={<Signup />}
          />


          {/* Protected Application */}

          <Route
            path="/*"
            element={
              <ProtectedRoute>
                <Layout />
              </ProtectedRoute>
            }
          />

        </Routes>

      </AuthProvider>

    </BrowserRouter>

  );
}

export default App;