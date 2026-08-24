import { useEffect, useState } from "react";
import { getAnalytics, getChatbots, getDocuments, getUsage } from "./api";
import "./App.css";

function Analytics() {
  const [analytics, setAnalytics] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    async function loadAnalytics() {
      try {
        setLoading(true);
        setError("");
        
        // Try to get analytics from backend, fall back to aggregating other data
        let analyticsData;
        try {
          analyticsData = await getAnalytics();
        } catch (e) {
          // If analytics endpoint doesn't exist, aggregate from other endpoints
          const [chatbots, documents, usage] = await Promise.all([
            getChatbots(),
            getDocuments(),
            getUsage(),
          ]);
          
          analyticsData = {
            total_chatbots: Array.isArray(chatbots) ? chatbots.length : 0,
            total_documents: Array.isArray(documents) ? documents.length : 0,
            total_conversations: usage?.chat_count || 0,
            total_messages: usage?.api_call_count || 0,
            active_chatbots: Array.isArray(chatbots) ? chatbots.filter(c => c.status === 'active').length : 0,
            processing_documents: Array.isArray(documents) ? documents.filter(d => d.status === 'processing').length : 0,
            storage_used: usage?.storage_bytes || 0,
          };
        }
        
        setAnalytics(analyticsData);
      } catch (err) {
        console.error("Analytics error:", err);
        setError(err.message || "Unable to load analytics data.");
      } finally {
        setLoading(false);
      }
    }

    loadAnalytics();
  }, []);

  const formatBytes = (bytes) => {
    if (bytes === 0) return "0 Bytes";
    const k = 1024;
    const sizes = ["Bytes", "KB", "MB", "GB"];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + " " + sizes[i];
  };

  return (
    <div>
      <div className="topbar">
        <div>
          <h1>Analytics</h1>
          <p>Monitor chatbot performance and usage patterns</p>
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
      ) : analytics ? (
        <>
          <section className="stats-grid">
            <div className="stat-card">
              <div className="stat-icon">🤖</div>
              <div>
                <p>Total Chatbots</p>
                <h2>{analytics.total_chatbots}</h2>
                <div style={{ fontSize: "11px", color: "#64748b", marginTop: "4px" }}>
                  {analytics.active_chatbots} active
                </div>
              </div>
            </div>
            <div className="stat-card">
              <div className="stat-icon">📄</div>
              <div>
                <p>Total Documents</p>
                <h2>{analytics.total_documents}</h2>
                <div style={{ fontSize: "11px", color: "#64748b", marginTop: "4px" }}>
                  {analytics.processing_documents} processing
                </div>
              </div>
            </div>
            <div className="stat-card">
              <div className="stat-icon">💬</div>
              <div>
                <p>Conversations</p>
                <h2>{analytics.total_conversations}</h2>
              </div>
            </div>
            <div className="stat-card">
              <div className="stat-icon">📊</div>
              <div>
                <p>Total Messages</p>
                <h2>{analytics.total_messages}</h2>
              </div>
            </div>
          </section>

          <section className="content-grid" style={{ marginTop: "20px" }}>
            <div className="content-card">
              <div className="card-header">
                <div>
                  <h2>Engagement Metrics</h2>
                  <p>User interaction statistics</p>
                </div>
              </div>
              <div style={{ marginTop: "20px" }}>
                <div style={{ marginBottom: "20px" }}>
                  <div style={{ fontSize: "14px", fontWeight: "600", color: "#111827", marginBottom: "8px" }}>
                    Average Messages per Conversation
                  </div>
                  <div style={{ fontSize: "24px", fontWeight: "700", color: "#6d28d9" }}>
                    {analytics.total_conversations > 0 
                      ? (analytics.total_messages / analytics.total_conversations).toFixed(1)
                      : "0"}
                  </div>
                </div>
                <div>
                  <div style={{ fontSize: "14px", fontWeight: "600", color: "#111827", marginBottom: "8px" }}>
                    Total Storage Used
                  </div>
                  <div style={{ fontSize: "24px", fontWeight: "700", color: "#6d28d9" }}>
                    {formatBytes(analytics.storage_used)}
                  </div>
                </div>
              </div>
            </div>

            <div className="content-card">
              <div className="card-header">
                <div>
                  <h2>Chatbot Performance</h2>
                  <p>Active vs inactive chatbots</p>
                </div>
              </div>
              <div style={{ marginTop: "20px" }}>
                <div style={{ marginBottom: "20px" }}>
                  <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "5px" }}>
                    <span style={{ fontSize: "13px", color: "#64748b" }}>Active Chatbots</span>
                    <span style={{ fontSize: "13px", fontWeight: "600" }}>
                      {analytics.active_chatbots}
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
                      width: analytics.total_chatbots > 0 
                        ? `${(analytics.active_chatbots / analytics.total_chatbots) * 100}%`
                        : "0%",
                      background: "#22c55e",
                      borderRadius: "4px",
                      transition: "width 0.3s ease"
                    }}></div>
                  </div>
                </div>
                <div>
                  <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "5px" }}>
                    <span style={{ fontSize: "13px", color: "#64748b" }}>Inactive Chatbots</span>
                    <span style={{ fontSize: "13px", fontWeight: "600" }}>
                      {analytics.total_chatbots - analytics.active_chatbots}
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
                      width: analytics.total_chatbots > 0 
                        ? `${((analytics.total_chatbots - analytics.active_chatbots) / analytics.total_chatbots) * 100}%`
                        : "0%",
                      background: "#ef4444",
                      borderRadius: "4px",
                      transition: "width 0.3s ease"
                    }}></div>
                  </div>
                </div>
              </div>
            </div>
          </section>
        </>
      ) : null}
    </div>
  );
}

export default Analytics;