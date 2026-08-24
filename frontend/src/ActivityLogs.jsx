import { useEffect, useState } from "react";
import { getAuditLogs } from "./api";
import "./App.css";

function ActivityLogs() {
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [filter, setFilter] = useState("");

  useEffect(() => {
    async function loadLogs() {
      try {
        setLoading(true);
        setError("");
        const data = await getAuditLogs(filter || null, 50, 0);
        setLogs(Array.isArray(data) ? data : []);
      } catch (err) {
        console.error("Activity logs error:", err);
        setError(err.message || "Unable to load activity logs.");
      } finally {
        setLoading(false);
      }
    }

    loadLogs();
  }, [filter]);

  const formatDate = (dateString) => {
    const date = new Date(dateString);
    return date.toLocaleString();
  };

  return (
    <div>
      <div className="topbar">
        <div>
          <h1>Activity Logs</h1>
          <p>View system activity and audit trail</p>
        </div>
        <select
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
          style={{
            padding: "8px 12px",
            borderRadius: "8px",
            border: "1px solid #e5e7eb",
            fontSize: "13px",
          }}
        >
          <option value="">All Actions</option>
          <option value="login">Login</option>
          <option value="register">Register</option>
          <option value="create">Create</option>
          <option value="update">Update</option>
          <option value="delete">Delete</option>
        </select>
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
      ) : (
        <div className="content-card" style={{ marginTop: "20px" }}>
          <div className="card-header">
            <div>
              <h2>Recent Activity</h2>
              <p>Latest actions performed on the platform</p>
            </div>
          </div>

          {logs.length === 0 ? (
            <div className="empty-state">
              <div className="empty-icon">📋</div>
              <h3>No activity found</h3>
              <p>No activity logs match your current filter.</p>
            </div>
          ) : (
            <div style={{ marginTop: "20px" }}>
              {logs.map((log) => (
                <div
                  key={log.id}
                  style={{
                    padding: "15px",
                    borderBottom: "1px solid #e5e7eb",
                    display: "flex",
                    flexDirection: "column",
                    gap: "8px",
                  }}
                >
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                    <div style={{ fontWeight: "600", color: "#111827", textTransform: "capitalize" }}>
                      {log.action}
                    </div>
                    <div style={{ fontSize: "12px", color: "#64748b" }}>
                      {formatDate(log.created_at)}
                    </div>
                  </div>
                  <div style={{ fontSize: "13px", color: "#64748b" }}>
                    {log.resource_type && <span>{log.resource_type}</span>}
                    {log.resource_id && <span> ({log.resource_id})</span>}
                  </div>
                  {log.ip_address && (
                    <div style={{ fontSize: "12px", color: "#94a3b8" }}>
                      IP: {log.ip_address}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default ActivityLogs;