import { useEffect, useState } from "react";
import { useAuth } from "./AuthContext";
import { getUsage, getAdminUsage } from "./api";
import "./App.css";

function Usage() {
  const { role } = useAuth();
  const [usage, setUsage] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    async function loadUsage() {
      try {
        setLoading(true);
        setError("");
        // Use admin usage endpoint for admins, regular usage for users
        const data = role === "admin" ? await getAdminUsage() : await getUsage();
        setUsage(data);
      } catch (err) {
        console.error("Usage error:", err);
        setError(err.message || "Unable to load usage data.");
      } finally {
        setLoading(false);
      }
    }

    loadUsage();
  }, [role]);

  const formatBytes = (bytes) => {
    if (bytes === 0) return "0 Bytes";
    const k = 1024;
    const sizes = ["Bytes", "KB", "MB", "GB"];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + " " + sizes[i];
  };

  const getPercentage = (used, max) => {
    if (!max || max === 0) return 0;
    return Math.round((used / max) * 100);
  };

  return (
    <div>
      <div className="topbar">
        <div>
          <h1>Usage & Plans</h1>
          <p>Monitor your resource consumption and plan limits</p>
        </div>
      </div>

      {error && (
        <div className="dashboard-error" style={{ marginBottom: "20px" }}>
          {error}
        </div>
      )}

      {loading ? (
        <div style={{ textAlign: "center", padding: "40px" }}>
          <div className="loading-spinner"></div>
        </div>
      ) : usage ? (
        <>
          <section className="stats-grid">
            <div className="stat-card">
              <div className="stat-icon">📄</div>
              <div>
                <p>Documents</p>
                <h2>{usage.document_count}</h2>
                <div style={{ fontSize: "11px", color: "#64748b", marginTop: "4px" }}>
                  {usage.limits?.max_documents && `of ${usage.limits.max_documents} allowed`}
                </div>
              </div>
            </div>
            <div className="stat-card">
              <div className="stat-icon">💾</div>
              <div>
                <p>Storage</p>
                <h2>{formatBytes(usage.storage_bytes)}</h2>
                <div style={{ fontSize: "11px", color: "#64748b", marginTop: "4px" }}>
                  {usage.limits?.max_storage_bytes && `of ${formatBytes(usage.limits.max_storage_bytes)} allowed`}
                </div>
              </div>
            </div>
            <div className="stat-card">
              <div className="stat-icon">💬</div>
              <div>
                <p>Chat Calls</p>
                <h2>{usage.chat_count}</h2>
                <div style={{ fontSize: "11px", color: "#64748b", marginTop: "4px" }}>
                  {usage.limits?.max_chat_calls_per_month && `of ${usage.limits.max_chat_calls_per_month}/month`}
                </div>
              </div>
            </div>
            <div className="stat-card">
              <div className="stat-icon">🔍</div>
              <div>
                <p>Search Calls</p>
                <h2>{usage.search_count}</h2>
                <div style={{ fontSize: "11px", color: "#64748b", marginTop: "4px" }}>
                  {usage.limits?.max_search_calls_per_month && `of ${usage.limits.max_search_calls_per_month}/month`}
                </div>
              </div>
            </div>
          </section>

          <div className="content-card" style={{ marginTop: "20px" }}>
            <div className="card-header">
              <div>
                <h2>Plan Details</h2>
                <p>Your current plan and limits</p>
              </div>
            </div>

            <div style={{ marginTop: "20px" }}>
              <div style={{ marginBottom: "20px" }}>
                <div style={{ fontSize: "14px", fontWeight: "600", color: "#111827", marginBottom: "8px" }}>
                  Current Plan: <span style={{ color: "#6d28d9", textTransform: "capitalize" }}>{usage.plan}</span>
                </div>
                <div style={{ fontSize: "13px", color: "#64748b" }}>
                  Period started: {new Date(usage.period_start).toLocaleDateString()}
                </div>
              </div>

              {usage.limits && (
                <div>
                  <h3 style={{ fontSize: "16px", marginBottom: "15px" }}>Plan Limits</h3>
                  
                  {usage.limits.max_documents && (
                    <div style={{ marginBottom: "15px" }}>
                      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "5px" }}>
                        <span style={{ fontSize: "13px", color: "#64748b" }}>Documents</span>
                        <span style={{ fontSize: "13px", fontWeight: "600" }}>
                          {usage.document_count} / {usage.limits.max_documents}
                        </span>
                      </div>
                      <div style={{ 
                        height: "8px", 
                        background: "#e5e7eb", 
                        borderRadius: "4px",
                        overflow: "hidden"
                      }}>
                        <div style={{ 
                          height: "100%", 
                          width: `${getPercentage(usage.document_count, usage.limits.max_documents)}%`,
                          background: getPercentage(usage.document_count, usage.limits.max_documents) > 90 ? "#ef4444" : "#6d28d9",
                          borderRadius: "4px",
                          transition: "width 0.3s ease"
                        }}></div>
                      </div>
                    </div>
                  )}

                  {usage.limits.max_storage_bytes && (
                    <div style={{ marginBottom: "15px" }}>
                      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "5px" }}>
                        <span style={{ fontSize: "13px", color: "#64748b" }}>Storage</span>
                        <span style={{ fontSize: "13px", fontWeight: "600" }}>
                          {formatBytes(usage.storage_bytes)} / {formatBytes(usage.limits.max_storage_bytes)}
                        </span>
                      </div>
                      <div style={{ 
                        height: "8px", 
                        background: "#e5e7eb", 
                        borderRadius: "4px",
                        overflow: "hidden"
                      }}>
                        <div style={{ 
                          height: "100%", 
                          width: `${getPercentage(usage.storage_bytes, usage.limits.max_storage_bytes)}%`,
                          background: getPercentage(usage.storage_bytes, usage.limits.max_storage_bytes) > 90 ? "#ef4444" : "#6d28d9",
                          borderRadius: "4px",
                          transition: "width 0.3s ease"
                        }}></div>
                      </div>
                    </div>
                  )}

                  {usage.limits.max_chat_calls_per_month && (
                    <div style={{ marginBottom: "15px" }}>
                      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "5px" }}>
                        <span style={{ fontSize: "13px", color: "#64748b" }}>Chat Calls</span>
                        <span style={{ fontSize: "13px", fontWeight: "600" }}>
                          {usage.chat_count} / {usage.limits.max_chat_calls_per_month}
                        </span>
                      </div>
                      <div style={{ 
                        height: "8px", 
                        background: "#e5e7eb", 
                        borderRadius: "4px",
                        overflow: "hidden"
                      }}>
                        <div style={{ 
                          height: "100%", 
                          width: `${getPercentage(usage.chat_count, usage.limits.max_chat_calls_per_month)}%`,
                          background: getPercentage(usage.chat_count, usage.limits.max_chat_calls_per_month) > 90 ? "#ef4444" : "#6d28d9",
                          borderRadius: "4px",
                          transition: "width 0.3s ease"
                        }}></div>
                      </div>
                    </div>
                  )}

                  {usage.limits.max_search_calls_per_month && (
                    <div>
                      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "5px" }}>
                        <span style={{ fontSize: "13px", color: "#64748b" }}>Search Calls</span>
                        <span style={{ fontSize: "13px", fontWeight: "600" }}>
                          {usage.search_count} / {usage.limits.max_search_calls_per_month}
                        </span>
                      </div>
                      <div style={{ 
                        height: "8px", 
                        background: "#e5e7eb", 
                        borderRadius: "4px",
                        overflow: "hidden"
                      }}>
                        <div style={{ 
                          height: "100%", 
                          width: `${getPercentage(usage.search_count, usage.limits.max_search_calls_per_month)}%`,
                          background: getPercentage(usage.search_count, usage.limits.max_search_calls_per_month) > 90 ? "#ef4444" : "#6d28d9",
                          borderRadius: "4px",
                          transition: "width 0.3s ease"
                        }}></div>
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        </>
      ) : null}
    </div>
  );
}

export default Usage;