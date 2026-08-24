import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

import {
  getAdminStats,
  getAdminUsage,
  getRecentActivity,
} from "./api";

import "./App.css";


function AdminDashboard() {

  const navigate = useNavigate();

  const [stats, setStats] = useState({
    users: 0,
    chatbots: 0,
    documents: 0,
    conversations: 0,
    messages: 0,
    storage_used: 0,
  });

  const [recentActivity, setRecentActivity] =
    useState([]);

  const [loading, setLoading] =
    useState(true);

  const [error, setError] =
    useState("");


  useEffect(() => {

    async function loadStats() {

      try {

        setLoading(true);
        setError("");

        const [
          adminStats,
          usage,
          activity,
        ] = await Promise.all([
          getAdminStats(),
          getAdminUsage(),
          getRecentActivity(),
        ]);


        setStats({
          users:
            adminStats?.users ?? 0,

          chatbots:
            adminStats?.chatbots ?? 0,

          documents:
            adminStats?.documents ?? 0,

          conversations:
            adminStats?.conversations ??
            usage?.chat_count ??
            0,

          messages:
            adminStats?.messages ??
            usage?.api_call_count ??
            0,

          storage_used:
            adminStats?.storage_used ??
            usage?.storage_bytes ??
            0,
        });


        setRecentActivity(
          Array.isArray(activity)
            ? activity
            : []
        );

      } catch (err) {

        console.error(
          "Admin dashboard error:",
          err
        );

        setError(
          err.message ||
          "Unable to load admin statistics."
        );

      } finally {

        setLoading(false);

      }
    }


    loadStats();

  }, []);


  function formatBytes(bytes) {

    if (!bytes) {
      return "0 Bytes";
    }

    const k = 1024;

    const sizes = [
      "Bytes",
      "KB",
      "MB",
      "GB",
    ];

    const i = Math.floor(
      Math.log(bytes) /
      Math.log(k)
    );

    return (
      Math.round(
        (bytes /
          Math.pow(k, i)) *
          100
      ) / 100
    ) +
      " " +
      sizes[i];
  }


  return (

    <div>

      <div className="topbar">

        <div>

          <h1>
            Admin Dashboard
          </h1>

          <p>
            Overview of your KNOWA AI
            organization
          </p>

        </div>

      </div>


      {error && (

        <div
          className="dashboard-error"
          style={{
            marginBottom: "20px",
          }}
        >
          {error}
        </div>

      )}


      {loading ? (

        <div
          style={{
            textAlign: "center",
            padding: "40px",
          }}
        >
          <div className="loading-spinner"></div>
        </div>

      ) : (

        <>

          {/* =================================================
              STATISTICS
          ================================================= */}

          <section className="stats-grid">

            <div className="stat-card">

              <div className="stat-icon">
                👥
              </div>

              <div>
                <p>
                  Total Users
                </p>

                <h2>
                  {stats.users}
                </h2>
              </div>

            </div>


            <div className="stat-card">

              <div className="stat-icon">
                🤖
              </div>

              <div>
                <p>
                  Total Chatbots
                </p>

                <h2>
                  {stats.chatbots}
                </h2>
              </div>

            </div>


            <div className="stat-card">

              <div className="stat-icon">
                📄
              </div>

              <div>
                <p>
                  Total Documents
                </p>

                <h2>
                  {stats.documents}
                </h2>
              </div>

            </div>


            <div className="stat-card">

              <div className="stat-icon">
                💬
              </div>

              <div>
                <p>
                  Conversations
                </p>

                <h2>
                  {stats.conversations}
                </h2>
              </div>

            </div>


            <div className="stat-card">

              <div className="stat-icon">
                📊
              </div>

              <div>
                <p>
                  Total Messages
                </p>

                <h2>
                  {stats.messages}
                </h2>
              </div>

            </div>


            <div className="stat-card">

              <div className="stat-icon">
                💾
              </div>

              <div>
                <p>
                  Storage Used
                </p>

                <h2>
                  {formatBytes(
                    stats.storage_used
                  )}
                </h2>
              </div>

            </div>

          </section>


          {/* =================================================
              QUICK ACTIONS + ACTIVITY
          ================================================= */}

          <section className="content-grid">

            <div className="content-card">

              <div className="card-header">

                <div>

                  <h2>
                    Quick Actions
                  </h2>

                  <p>
                    Common administrative
                    tasks
                  </p>

                </div>

              </div>


              <div
                style={{
                  display: "flex",
                  flexDirection: "column",
                  gap: "10px",
                  marginTop: "20px",
                }}
              >

                <button
                  className="create-button"
                  style={{
                    width: "100%",
                  }}
                  onClick={() =>
                    navigate(
                      "/admin/users"
                    )
                  }
                >
                  View All Users
                </button>


                <button
                  className="create-button"
                  style={{
                    width: "100%",
                  }}
                  onClick={() =>
                    navigate(
                      "/chatbots"
                    )
                  }
                >
                  Manage Chatbots
                </button>


                <button
                  className="create-button"
                  style={{
                    width: "100%",
                  }}
                  onClick={() =>
                    navigate(
                      "/admin/activity"
                    )
                  }
                >
                  Review Activity Logs
                </button>


                <button
                  className="outline-button"
                  style={{
                    width: "100%",
                  }}
                  onClick={() =>
                    navigate(
                      "/admin/usage"
                    )
                  }
                >
                  View Usage
                </button>

              </div>

            </div>


            {/* =================================================
                RECENT ACTIVITY
            ================================================= */}

            <div className="content-card">

              <div className="card-header">

                <div>

                  <h2>
                    Recent Activity
                  </h2>

                  <p>
                    Latest system actions
                  </p>

                </div>

                <button
                  className="outline-button"
                  onClick={() =>
                    navigate(
                      "/admin/activity"
                    )
                  }
                >
                  View All
                </button>

              </div>


              <div
                style={{
                  marginTop: "20px",
                }}
              >

                {recentActivity.length === 0 ? (

                  <div
                    style={{
                      fontSize: "13px",
                      color: "#64748b",
                    }}
                  >
                    No recent activity
                  </div>

                ) : (

                  recentActivity
                    .slice(0, 5)
                    .map(
                      (activity) => (

                        <div
                          key={
                            activity.id
                          }
                          style={{
                            padding: "10px",
                            borderBottom:
                              "1px solid #e5e7eb",
                            fontSize: "13px",
                          }}
                        >

                          <div
                            style={{
                              fontWeight: "600",
                              color:
                                "#111827",
                              textTransform:
                                "capitalize",
                            }}
                          >
                            {activity.action}
                          </div>

                          <div
                            style={{
                              fontSize: "12px",
                              color:
                                "#64748b",
                            }}
                          >
                            {activity.created_at
                              ? new Date(
                                  activity.created_at
                                ).toLocaleString()
                              : ""}
                          </div>

                        </div>

                      )
                    )

                )}

              </div>

            </div>

          </section>

        </>

      )}

    </div>
  );
}


export default AdminDashboard;