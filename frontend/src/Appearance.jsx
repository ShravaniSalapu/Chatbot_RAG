import { useEffect, useState } from "react";
import { getChatbots, getChatbotSettings, updateChatbotSettings } from "./api";
import "./App.css";

function Appearance() {
  const [chatbots, setChatbots] = useState([]);
  const [selectedChatbot, setSelectedChatbot] = useState(null);
  const [settings, setSettings] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  useEffect(() => {
    async function loadChatbots() {
      try {
        setLoading(true);
        setError("");
        const data = await getChatbots();
        setChatbots(Array.isArray(data) ? data : []);
        if (Array.isArray(data) && data.length > 0) {
          setSelectedChatbot(data[0].id);
          await loadChatbotSettings(data[0].id);
        }
      } catch (err) {
        console.error("Chatbots loading error:", err);
        setError(err.message || "Unable to load chatbots.");
      } finally {
        setLoading(false);
      }
    }

    loadChatbots();
  }, []);

  async function loadChatbotSettings(chatbotId) {
    try {
      setError("");
      const data = await getChatbotSettings(chatbotId);
      setSettings(data || {});
    } catch (err) {
      console.error("Settings loading error:", err);
      setError(err.message || "Unable to load chatbot settings.");
    }
  }

  async function handleSaveSettings(e) {
    e.preventDefault();
    if (!selectedChatbot || !settings) return;

    try {
      setSaving(true);
      setError("");
      await updateChatbotSettings(selectedChatbot, settings);
      setSuccess("Appearance settings saved successfully!");
      setTimeout(() => setSuccess(""), 3000);
    } catch (err) {
      console.error("Settings save error:", err);
      setError(err.message || "Unable to save settings.");
    } finally {
      setSaving(false);
    }
  }

  function handleSettingChange(key, value) {
    setSettings(prev => ({
      ...prev,
      [key]: value
    }));
  }

  if (loading) {
    return (
      <div>
        <div className="topbar">
          <div>
            <h1>Appearance</h1>
            <p>Customize your chatbot appearance</p>
          </div>
        </div>
        <div style={{ textAlign: "center", padding: "40px" }}>
          <div className="loading-spinner"></div>
        </div>
      </div>
    );
  }

  return (
    <div>
      <div className="topbar">
        <div>
          <h1>Appearance</h1>
          <p>Customize your chatbot appearance</p>
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

      {chatbots.length === 0 ? (
        <div className="empty-state">
          <div className="empty-icon">🤖</div>
          <h3>No chatbots found</h3>
          <p>Create a chatbot first to customize its appearance.</p>
        </div>
      ) : (
        <div className="content-card" style={{ marginTop: "20px" }}>
          <div className="card-header">
            <div>
              <h2>Chatbot Appearance</h2>
              <p>Customize the look and feel of your chatbot widget</p>
            </div>
          </div>

          <div style={{ marginTop: "20px" }}>
            <div className="form-group" style={{ marginBottom: "15px" }}>
              <label>Select Chatbot</label>
              <select
                value={selectedChatbot || ""}
                onChange={(e) => {
                  setSelectedChatbot(e.target.value);
                  loadChatbotSettings(e.target.value);
                }}
                style={{
                  width: "100%",
                  padding: "8px 12px",
                  borderRadius: "8px",
                  border: "1px solid #e5e7eb",
                  fontSize: "14px",
                }}
              >
                {chatbots.map(chatbot => (
                  <option key={chatbot.id} value={chatbot.id}>
                    {chatbot.name}
                  </option>
                ))}
              </select>
            </div>

            {settings && (
              <form onSubmit={handleSaveSettings}>
                <div className="form-group" style={{ marginBottom: "15px" }}>
                  <label>Primary Color</label>
                  <input
                    type="color"
                    value={settings.primary_color || "#6d28d9"}
                    onChange={(e) => handleSettingChange("primary_color", e.target.value)}
                    style={{
                      width: "100%",
                      height: "40px",
                      padding: "4px",
                      borderRadius: "8px",
                      border: "1px solid #e5e7eb",
                    }}
                  />
                </div>

                <div className="form-group" style={{ marginBottom: "15px" }}>
                  <label>Widget Title</label>
                  <input
                    type="text"
                    value={settings.widget_title || "KNOWA AI Assistant"}
                    onChange={(e) => handleSettingChange("widget_title", e.target.value)}
                    placeholder="Widget title"
                  />
                </div>

                <div className="form-group" style={{ marginBottom: "15px" }}>
                  <label>Welcome Message</label>
                  <textarea
                    value={settings.welcome_message || "Hello! How can I help you today?"}
                    onChange={(e) => handleSettingChange("welcome_message", e.target.value)}
                    placeholder="Welcome message"
                    rows="3"
                  />
                </div>

                <div className="form-group" style={{ marginBottom: "15px" }}>
                  <label>
                    <input
                      type="checkbox"
                      checked={settings.show_avatar !== false}
                      onChange={(e) => handleSettingChange("show_avatar", e.target.checked)}
                      style={{ marginRight: "8px" }}
                    />
                    Show Avatar
                  </label>
                </div>

                <div className="form-group" style={{ marginBottom: "15px" }}>
                  <label>Position</label>
                  <select
                    value={settings.position || "bottom-right"}
                    onChange={(e) => handleSettingChange("position", e.target.value)}
                    style={{
                      width: "100%",
                      padding: "8px 12px",
                      borderRadius: "8px",
                      border: "1px solid #e5e7eb",
                      fontSize: "14px",
                    }}
                  >
                    <option value="bottom-right">Bottom Right</option>
                    <option value="bottom-left">Bottom Left</option>
                    <option value="top-right">Top Right</option>
                    <option value="top-left">Top Left</option>
                  </select>
                </div>

                <button
                  type="submit"
                  className="create-button"
                  disabled={saving}
                >
                  {saving ? "Saving..." : "Save Changes"}
                </button>
              </form>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

export default Appearance;