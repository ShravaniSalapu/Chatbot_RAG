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
import AdminDashboard from "./AdminDashboard";
import Users from "./Users";
import ActivityLogs from "./ActivityLogs";
import Usage from "./Usage";
import Analytics from "./Analytics";
import Profile from "./Profile";
import Conversations from "./Conversations";
import Appearance from "./Appearance";
import Settings from "./Settings";

import { AuthProvider, useAuth } from "./AuthContext";
import { getChatbots, getDocuments, getUsage } from "./api";


/* ============================================================
   DASHBOARD
   ============================================================ */

function Dashboard() {
  const [stats, setStats] = useState({
    chatbots: 0,
    documents: 0,
    conversations: 0,
    totalMessages: 0,
  });

  const [loadingStats, setLoadingStats] = useState(true);
  const [statsError, setStatsError] = useState("");

  const { role } = useAuth();

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
          chatbots: Array.isArray(chatbots)
            ? chatbots.length
            : 0,

          documents: Array.isArray(documents)
            ? documents.length
            : 0,

          conversations: usage?.chat_count ?? 0,

          totalMessages: usage?.api_call_count ?? 0,
        });

      } catch (err) {
        console.error(
          "Dashboard stats error:",
          err
        );

        setStatsError(
          err?.message ||
            "Unable to load dashboard statistics."
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
        title={
          role === "admin"
            ? "Admin Dashboard"
            : "Dashboard"
        }

        subtitle={
          role === "admin"
            ? "Welcome back to KNOWA AI Admin"
            : "Welcome back to KNOWA AI"
        }

        action="+ Create Chatbot"
      />

      <section className="stats-grid">

        <StatCard
          icon="🤖"
          title="Total Chatbots"
          value={
            loadingStats
              ? "…"
              : stats.chatbots
          }
        />

        <StatCard
          icon="📄"
          title="Total Documents"
          value={
            loadingStats
              ? "…"
              : stats.documents
          }
        />

        <StatCard
          icon="💬"
          title="Conversations"
          value={
            loadingStats
              ? "…"
              : stats.conversations
          }
        />

        <StatCard
          icon="📈"
          title="Total Messages"
          value={
            loadingStats
              ? "…"
              : stats.totalMessages
          }
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


/* ============================================================
   PLACEHOLDER
   ============================================================ */

function PlaceholderPage({
  title,
  description,
}) {
  return (
    <div>

      <PageHeader
        title={title}
        subtitle={description}
      />

      <div className="page-placeholder">

        <div className="placeholder-icon">
          ✨
        </div>

        <h2>{title}</h2>

        <p>
          This section will be connected to your KNOWA AI backend.
        </p>

      </div>

    </div>
  );
}


/* ============================================================
   PROTECTED ROUTE
   ============================================================ */

function ProtectedRoute({ children }) {
  const {
    isAuthenticated,
    loading,
  } = useAuth();

  if (loading) {
    return (
      <div
        style={{
          minHeight: "100vh",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          background: "#f6f7fb",
        }}
      >
        <div className="loading-spinner"></div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return (
      <Navigate
        to="/login"
        replace
      />
    );
  }

  return children;
}


/* ============================================================
   ADMIN ROUTE
   ============================================================ */

function AdminRoute({ children }) {
  const {
    isAuthenticated,
    role,
    loading,
  } = useAuth();

  if (loading) {
    return (
      <div
        style={{
          minHeight: "100vh",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          background: "#f6f7fb",
        }}
      >
        <div className="loading-spinner"></div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return (
      <Navigate
        to="/login"
        replace
      />
    );
  }

  if (role !== "admin") {
    return (
      <Navigate
        to="/dashboard"
        replace
      />
    );
  }

  return children;
}


/* ============================================================
   PAGE HEADER
   ============================================================ */

function PageHeader({
  title,
  subtitle,
  action,
}) {
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


/* ============================================================
   STAT CARD
   ============================================================ */

function StatCard({
  icon,
  title,
  value,
}) {
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


/* ============================================================
   CONTENT CARD
   ============================================================ */

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


/* ============================================================
   LAYOUT
   ============================================================ */

function Layout() {

  const navigate = useNavigate();
  const location = useLocation();

  const {
    user,
    role,
    logout,
    isAuthenticated,
  } = useAuth();


  /* ==========================================================
     LOGOUT
     ========================================================== */

  const handleLogout = () => {

    logout();

    navigate(
      "/login",
      {
        replace: true,
      }
    );

  };


  /* ==========================================================
     ADMIN SIDEBAR
     ========================================================== */

  const adminNavigationItems = [

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

    {
      path: "/profile",
      icon: "👤",
      label: "Profile",
    },

  ];


  /* ==========================================================
     NORMAL USER SIDEBAR
     ========================================================== */

  const userNavigationItems = [

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
      path: "/install-widget",
      icon: "🔗",
      label: "Install Widget",
    },

    {
      path: "/profile",
      icon: "👤",
      label: "Profile",
    },

  ];


  /* ==========================================================
     SELECT SIDEBAR BASED ON ROLE
     ========================================================== */

  const navigationItems =
    role === "admin"
      ? adminNavigationItems
      : userNavigationItems;


  /* ==========================================================
     LOGIN REDIRECT
     ========================================================== */

  useEffect(() => {

    if (
      isAuthenticated &&
      (
        location.pathname === "/login" ||
        location.pathname === "/signup"
      )
    ) {

      navigate(
        "/dashboard",
        {
          replace: true,
        }
      );

    }

  }, [
    isAuthenticated,
    location.pathname,
    navigate,
  ]);


  /* ==========================================================
     ACTIVE SIDEBAR ITEM
     ========================================================== */

  function isNavItemActive(item) {

    if (
      item.path === "/install-widget"
    ) {

      return (
        location.pathname ===
          "/install-widget" ||

        /^\/chatbots\/[^/]+\/install$/.test(
          location.pathname
        )
      );

    }


    if (
      item.path === "/chatbots"
    ) {

      return (
        location.pathname.startsWith(
          "/chatbots"
        ) &&

        !location.pathname.endsWith(
          "/install"
        )
      );

    }


    return (
      location.pathname ===
      item.path
    );

  }


  return (

    <div className="app">


      {/* ======================================================
          SIDEBAR
          ====================================================== */}

      <aside className="sidebar">

        <div className="brand">

          <KnowaLogo />

        </div>


        <nav className="sidebar-nav">

          {navigationItems.map(
            (item) => (

              <NavLink
                key={item.path}
                to={item.path}
                className={() =>
                  `nav-item ${
                    isNavItemActive(item)
                      ? "active"
                      : ""
                  }`
                }
              >

                <span className="nav-icon">
                  {item.icon}
                </span>

                <span className="nav-label">
                  {item.label}
                </span>

              </NavLink>

            )
          )}

        </nav>


        {/* ====================================================
            USER INFORMATION
            ==================================================== */}

        <div className="sidebar-bottom">

          <div className="user-card">

            <div className="user-avatar">

              {
                user?.full_name
                  ?.charAt(0)
                  .toUpperCase()

                ||

                user?.email
                  ?.charAt(0)
                  .toUpperCase()

                ||

                "U"
              }

            </div>


            <div>

              <div className="user-name">

                {
                  user?.full_name ||
                  user?.email ||
                  "User"
                }

              </div>


              <div className="user-role">

                {
                  role
                    ? role
                        .charAt(0)
                        .toUpperCase() +
                      role.slice(1)
                    : "User"
                }

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


      {/* ======================================================
          MAIN CONTENT
          ====================================================== */}

      <main className="main-content">

        <Routes>


          {/* ==================================================
              DASHBOARD
              ================================================== */}

          <Route
            path="/"
            element={
              <Navigate
                to="/dashboard"
                replace
              />
            }
          />


          <Route
            path="/dashboard"
            element={
              <Dashboard />
            }
          />


          {/* ==================================================
              CHATBOTS
              ================================================== */}

          <Route
            path="/chatbots"
            element={
              <Chatbots />
            }
          />

          <Route
            path="/chatbots/:chatbotId"
            element={
              <ManageChatbot />
            }
          />

          <Route
            path="/chatbots/:chatbotId/knowledge"
            element={
              <ChatbotKnowledge />
            }
          />

          <Route
            path="/chatbots/:chatbotId/install"
            element={
              <InstallWidget />
            }
          />


          {/* ==================================================
              KNOWLEDGE BASE
              ================================================== */}

          <Route
            path="/knowledge-base"
            element={
              <KnowledgeBase />
            }
          />


          {/* ==================================================
              CONVERSATIONS
              ================================================== */}

          <Route
            path="/conversations"
            element={
              <Conversations />
            }
          />


          {/* ==================================================
              INSTALL WIDGET
              ================================================== */}

          <Route
            path="/install-widget"
            element={
              <InstallWidget />
            }
          />


          {/* ==================================================
              ADMIN ONLY
              ================================================== */}

          <Route
            path="/analytics"
            element={
              <AdminRoute>
                <Analytics />
              </AdminRoute>
            }
          />


          <Route
            path="/appearance"
            element={
              <AdminRoute>
                <Appearance />
              </AdminRoute>
            }
          />


          <Route
            path="/settings"
            element={
              <AdminRoute>
                <Settings />
              </AdminRoute>
            }
          />


          {/* ==================================================
              ADMIN DASHBOARD
              ================================================== */}

          <Route
            path="/admin/dashboard"
            element={
              <AdminRoute>
                <AdminDashboard />
              </AdminRoute>
            }
          />


          {/* ==================================================
              ADMIN USERS
              ================================================== */}

          <Route
            path="/admin/users"
            element={
              <AdminRoute>
                <Users />
              </AdminRoute>
            }
          />


          {/* ==================================================
              ADMIN ACTIVITY
              ================================================== */}

          <Route
            path="/admin/activity"
            element={
              <AdminRoute>
                <ActivityLogs />
              </AdminRoute>
            }
          />


          {/* ==================================================
              ADMIN USAGE
              ================================================== */}

          <Route
            path="/admin/usage"
            element={
              <AdminRoute>
                <Usage />
              </AdminRoute>
            }
          />


          {/* ==================================================
              PROFILE
              ================================================== */}

          <Route
            path="/profile"
            element={
              <Profile />
            }
          />


          {/* ==================================================
              UNKNOWN ROUTE
              ================================================== */}

          <Route
            path="*"
            element={
              <Navigate
                to="/dashboard"
                replace
              />
            }
          />

        </Routes>

      </main>

    </div>

  );
}


/* ============================================================
   APP
   ============================================================ */

function App() {

  return (

    <BrowserRouter>

      <AuthProvider>

        <Routes>


          {/* ==================================================
              PUBLIC
              ================================================== */}

          <Route
            path="/login"
            element={
              <Login />
            }
          />

          <Route
            path="/signup"
            element={
              <Signup />
            }
          />


          {/* ==================================================
              PROTECTED APPLICATION
              ================================================== */}

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