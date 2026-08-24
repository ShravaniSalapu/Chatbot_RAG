import { useEffect, useState } from "react";
import { useAuth } from "./AuthContext";
import { getCurrentUser } from "./api";
import "./App.css";

function Settings() {
  const { user, refreshUser } = useAuth();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  const [notifications, setNotifications] = useState({
    emailAlerts: true,
    chatNotifications: true,
    weeklyReports: false,
  });

  const [preferences, setPreferences] = useState({
    language: "en",
    timezone: "UTC",
    dateFormat: "MM/DD/YYYY",
  });

  async function handleSaveSettings(e) {
    e.preventDefault();
    setError("");
    setSuccess("");

    try {
      setLoading(true);
      // In a real implementation, you would save these to the backend
      // For now, we'll just simulate a successful save
      await new Promise(resolve => setTimeout(resolve, 500));
      setSuccess("Settings saved successfully!");
      setTimeout(() => setSuccess(""), 3000);
    } catch (err) {
      console.error("Settings save error:", err);
      setError(err.message || "Unable to save settings.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div>
      <div className="topbar">
        <div>
          <h1>Settings</h1>
          <p>Manage your KNOWA AI application settings</p>
        </div>
      </div>

      {error && (
        <div className="dashboard-error" style={{ marginBottom: "20px" }}>
          {error}
        </div>
      )}

      {success && (
        <div className="success-message" style={{ marginBottom: "20px" }}>
          {success}
        </div>
      )}

      <div className="content-grid">
        <div className="content-card">
          <div className="card-header">
            <div>
              <h2>Notification Settings</h2>
              <p>Configure how you receive notifications</p>
            </div>
          </div>

          <form onSubmit={handleSaveSettings} style={{ marginTop: "20px" }}>
            <div className="form-group" style={{ marginBottom: "15px" }}>
              <label>
                <input
                  type="checkbox"
                  checked={notifications.emailAlerts}
                  onChange={(e) => setNotifications({
                    ...notifications,
                    emailAlerts: e.target.checked
                  })}
                  style={{ marginRight: "8px" }}
                />
                Email Alerts
              </label>
              <p style={{ fontSize: "12px", color: "#64748b", marginTop: "4px" }}>
                Receive email notifications for important events
              </p>
            </div>

            <div className="form-group" style={{ marginBottom: "15px" }}>
              <label>
                <input
                  type="checkbox"
                  checked={notifications.chatNotifications}
                  onChange={(e) => setNotifications({
                    ...notifications,
                    chatNotifications: e.target.checked
                  })}
                  style={{ marginRight: "8px" }}
                />
                Chat Notifications
              </label>
              <p style={{ fontSize: "12px", color: "#64748b", marginTop: "4px" }}>
                Get notified when users interact with your chatbots
              </p>
            </div>

            <div className="form-group" style={{ marginBottom: "15px" }}>
              <label>
                <input
                  type="checkbox"
                  checked={notifications.weeklyReports}
                  onChange={(e) => setNotifications({
                    ...notifications,
                    weeklyReports: e.target.checked
                  })}
                  style={{ marginRight: "8px" }}
                />
                Weekly Reports
              </label>
              <p style={{ fontSize: "12px", color: "#64748b", marginTop: "4px" }}>
                Receive weekly usage and performance reports
              </p>
            </div>

            <button
              type="submit"
              className="create-button"
              disabled={loading}
            >
              {loading ? "Saving..." : "Save Notification Settings"}
            </button>
          </form>
        </div>

        <div className="content-card">
          <div className="card-header">
            <div>
              <h2>Preferences</h2>
              <p>Customize your application preferences</p>
            </div>
          </div>

          <form onSubmit={handleSaveSettings} style={{ marginTop: "20px" }}>
            <div className="form-group" style={{ marginBottom: "15px" }}>
              <label>Language</label>
              <select
                value={preferences.language}
                onChange={(e) => setPreferences({
                  ...preferences,
                  language: e.target.value
                })}
                style={{
                  width: "100%",
                  padding: "8px 12px",
                  borderRadius: "8px",
                  border: "1px solid #e5e7eb",
                  fontSize: "14px",
                }}
              >
                <option value="en">English</option>
                <option value="es">Spanish</option>
                <option value="fr">French</option>
                <option value="de">German</option>
              </select>
            </div>

            <div className="form-group" style={{ marginBottom: "15px" }}>
              <label>Timezone</label>
              <select
                value={preferences.timezone}
                onChange={(e) => setPreferences({
                  ...preferences,
                  timezone: e.target.value
                })}
                style={{
                  width: "100%",
                  padding: "8px 12px",
                  borderRadius: "8px",
                  border: "1px solid #e5e7eb",
                  fontSize: "14px",
                }}
              >
                <option value="UTC">UTC</option>
                <option value="America/New_York">Eastern Time</option>
                <option value="America/Chicago">Central Time</option>
                <option value="America/Denver">Mountain Time</option>
                <option value="America/Los_Angeles">Pacific Time</option>
              </select>
            </div>

            <div className="form-group" style={{ marginBottom: "15px" }}>
              <label>Date Format</label>
              <select
                value={preferences.dateFormat}
                onChange={(e) => setPreferences({
                  ...preferences,
                  dateFormat: e.target.value
                })}
                style={{
                  width: "100%",
                  padding: "8px 12px",
                  borderRadius: "8px",
                  border: "1px solid #e5e7eb",
                  fontSize: "14px",
                }}
              >
                <option value="MM/DD/YYYY">MM/DD/YYYY</option>
                <option value="DD/MM/YYYY">DD/MM/YYYY</option>
                <option value="YYYY-MM-DD">YYYY-MM-DD</option>
              </select>
            </div>

            <button
              type="submit"
              className="create-button"
              disabled={loading}
            >
              {loading ? "Saving..." : "Save Preferences"}
            </button>
          </form>
        </div>
      </div>

      <div className="content-card" style={{ marginTop: "20px" }}>
        <div className="card-header">
          <div>
            <h2>Account Information</h2>
            <p>Your current account details</p>
          </div>
        </div>

        <div style={{ marginTop: "20px" }}>
          <div style={{ marginBottom: "15px" }}>
            <div style={{ fontSize: "14px", fontWeight: "600", color: "#111827", marginBottom: "8px" }}>
              Email
            </div>
            <div style={{ fontSize: "13px", color: "#64748b" }}>
              {user?.email || "N/A"}
            </div>
          </div>

          <div style={{ marginBottom: "15px" }}>
            <div style={{ fontSize: "14px", fontWeight: "600", color: "#111827", marginBottom: "8px" }}>
              Name
            </div>
            <div style={{ fontSize: "13px", color: "#64748b" }}>
              {user?.full_name || "N/A"}
            </div>
          </div>

          <div style={{ marginBottom: "15px" }}>
            <div style={{ fontSize: "14px", fontWeight: "600", color: "#111827", marginBottom: "8px" }}>
              Role
            </div>
            <div style={{ fontSize: "13px", color: "#64748b" }}>
              {user?.role ? user.role.charAt(0).toUpperCase() + user.role.slice(1) : "User"}
            </div>
          </div>

          <div>
            <div style={{ fontSize: "14px", fontWeight: "600", color: "#111827", marginBottom: "8px" }}>
              Tenant ID
            </div>
            <div style={{ fontSize: "13px", color: "#64748b" }}>
              {user?.tenant_id || "N/A"}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default Settings;