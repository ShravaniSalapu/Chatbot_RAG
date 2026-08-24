import { useEffect, useState } from "react";
import { getAuditLogs } from "./api";
import "./App.css";

function Conversations() {
  const [conversations, setConversations] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    async function loadConversations() {
      try {
        setLoading(true);
        setError("");
        // Load audit logs filtered for chat-related actions
        const data = await getAuditLogs("chat", 50, 0);
        setConversations(Array.isArray(data) ? data : []);
      } catch (err) {
        console.error("Conversations loading error:", err);
        setError(err.message || "Unable to load conversations.");
      } finally {
        setLoading(false);
      }
    }

    loadConversations();
  }, []);

  const formatDate = (dateString) => {
    const date = new Date(dateString);
    return date.toLocaleString();
  };

  return (
    <div>
      <div className="topbar">
        <div>
          <h1>Conversations</h1>
          <p>View and manage chatbot conversations</p>
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
      ) : (
        <div className="content-card" style={{ marginTop: "20px" }}>
          <div className="card-header">
            <div>
              <h2>Recent Conversations</h2>
              <p>Latest chat interactions with your chatbots</p>
            </div>
          </div>

          {conversations.length === 0 ? (
            <div className="empty-state">
              <div className="empty-icon">💬</div>
              <h3>No conversations found</h3>
              <p>No chat conversations have been recorded yet.</p>
            </div>
          ) : (
            <div style={{ marginTop: "20px" }}>
              {conversations.map((conv) => (
                <div
                  key={conv.id}
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
                      {conv.action}
                    </div>
                    <div style={{ fontSize: "12px", color: "#64748b" }}>
                      {formatDate(conv.created_at)}
                    </div>
                  </div>
                  <div style={{ fontSize: "13px", color: "#64748b" }}>
                    {conv.resource_type && <span>{conv.resource_type}</span>}
                    {conv.resource_id && <span> ({conv.resource_id})</span>}
                  </div>
                  {conv.ip_address && (
                    <div style={{ fontSize: "12px", color: "#94a3b8" }}>
                      IP: {conv.ip_address}
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

export default Conversations;