import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import {
  getChatbot,
  getChatbotSettings,
  getChatbots,
} from "./api";

function InstallWidget() {
  const { chatbotId } = useParams();
  const navigate = useNavigate();

  const [chatbot, setChatbot] = useState(null);
  const [settings, setSettings] = useState(null);
  const [chatbots, setChatbots] = useState([]);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const [copied, setCopied] = useState(false);

  useEffect(() => {
    async function loadData() {
      try {
        setLoading(true);
        setError("");
        setChatbot(null);
        setSettings(null);
        setChatbots([]);

        if (chatbotId) {
          const chatbotData = await getChatbot(chatbotId);

          setChatbot(chatbotData);

          try {
            const settingsData =
              await getChatbotSettings(chatbotId);

            setSettings(settingsData);
          } catch {
            setSettings(null);
          }
        } else {
          const data = await getChatbots();
          setChatbots(Array.isArray(data) ? data : []);
        }
      } catch (err) {
        console.error(err);

        setError(
          err.message ||
            "Unable to load install widget data."
        );
      } finally {
        setLoading(false);
      }
    }

    loadData();
  }, [chatbotId]);


  if (loading) {
    return (
      <div className="widget-page">
        <div className="widget-loading">
          <div className="loading-spinner"></div>

          <h2>Loading widget...</h2>

          <p>
            Getting your chatbot installation details.
          </p>
        </div>
      </div>
    );
  }


  if (error) {
    return (
      <div className="widget-page">

        <div className="widget-error">

          <div className="state-icon">
            ⚠️
          </div>

          <h2>
            Unable to load widget
          </h2>

          <p>
            {error}
          </p>

          <button
            className="create-button"
            onClick={() =>
              navigate("/chatbots")
            }
          >
            Back to Chatbots
          </button>

        </div>

      </div>
    );
  }

  if (!chatbotId && !loading) {
    return (
      <div className="widget-page">

        <div className="widget-page-header">

          <div>
            <h1>Install Widget</h1>
            <p>
              Select a chatbot to install on your site.
            </p>
          </div>

        </div>

        {chatbots.length === 0 ? (
          <div className="widget-empty-state">
            <div className="state-icon">
              🤖
            </div>

            <h2>No chatbots available</h2>
            <p>
              Create a chatbot first, then install
              the widget from the Chatbots page.
            </p>

            <button
              className="create-button"
              onClick={() =>
                navigate("/chatbots")
              }
            >
              Go to Chatbots
            </button>
          </div>
        ) : (
          <div className="widget-list">
            {chatbots.map((item) => (
              <div
                key={item.id}
                className="widget-list-card"
              >
                <div>
                  <h3>{item.name}</h3>
                  <p>
                    {item.description ||
                      "KNOWA AI chatbot"}
                  </p>
                </div>

                <button
                  className="create-button"
                  onClick={() =>
                    navigate(
                      `/chatbots/${item.id}/install`
                    )
                  }
                >
                  Install Widget
                </button>
              </div>
            ))}
          </div>
        )}
      </div>
    );
  }

  if (!chatbot) {
    return null;
  }


  /*
   * IMPORTANT:
   *
   * This is the embed token returned by
   * your FastAPI backend.
   */

  const embedToken =
    chatbot.embed_token;


  /*
   * Widget script
   *
   * Change this URL later if your backend
   * exposes the widget script from another path.
   */

  const widgetScript =
    `http://localhost:8000/widget.js`;


  const embedCode =
`<script
  src="${widgetScript}"
  data-chatbot-id="${chatbot.id}"
  data-embed-token="${embedToken}"
  defer
></script>`;


  async function copyCode() {
    try {
      await navigator.clipboard.writeText(
        embedCode
      );

      setCopied(true);

      setTimeout(() => {
        setCopied(false);
      }, 2000);

    } catch (err) {
      console.error(
        "Failed to copy:",
        err
      );
    }
  }


  return (
    <div className="widget-page">

      {/* HEADER */}

      <div className="widget-page-header">

        <div>

          <button
            className="back-button"
            onClick={() =>
              navigate("/chatbots")
            }
          >
            ← Back to Chatbots
          </button>

          <h1>
            Install Widget
          </h1>

          <p>
            Add {chatbot.name} to any website
          </p>

        </div>

      </div>


      {/* MAIN GRID */}

      <div className="widget-grid">


        {/* LEFT SIDE */}

        <div className="widget-card">

          <div className="widget-card-header">

            <div className="widget-number">
              1
            </div>

            <div>

              <h2>
                Copy the embed code
              </h2>

              <p>
                Copy this JavaScript code
                and add it to your website.
              </p>

            </div>

          </div>


          <div className="code-container">

            <pre>
              <code>
                {embedCode}
              </code>
            </pre>

            <button
              className="copy-button"
              onClick={copyCode}
            >
              {copied
                ? "✓ Copied!"
                : "Copy Code"}
            </button>

          </div>


          <div className="instruction-box">

            <strong>
              Where should I paste this?
            </strong>

            <p>
              Paste the code just before the
              closing <code>&lt;/body&gt;</code>
              tag of your website.
            </p>

          </div>

        </div>


        {/* RIGHT SIDE */}

        <div className="widget-card">

          <div className="widget-card-header">

            <div className="widget-number">
              2
            </div>

            <div>

              <h2>
                Your chatbot
              </h2>

              <p>
                Widget configuration
              </p>

            </div>

          </div>


          <div className="chatbot-info">

            <div className="chatbot-preview-icon">
              🤖
            </div>

            <h3>
              {chatbot.name}
            </h3>

            <p>
              {chatbot.description ||
                "KNOWA AI chatbot"}
            </p>

            <div className="widget-status">
              <span></span>
              {chatbot.status}
            </div>

          </div>


          <div className="token-section">

            <label>
              Embed Token
            </label>

            <div className="token-box">
              {embedToken}
            </div>

          </div>

        </div>

      </div>


      {/* SETTINGS */}

      {settings && (
        <div className="widget-card settings-card">

          <h2>
            Current Widget Settings
          </h2>

          <div className="settings-grid">

            <div>
              <span>Theme</span>
              <strong>
                {settings.theme || "Default"}
              </strong>
            </div>

            <div>
              <span>Position</span>
              <strong>
                {settings.position || "Bottom Right"}
              </strong>
            </div>

            <div>
              <span>Primary Color</span>
              <strong>
                {settings.primary_color || "Default"}
              </strong>
            </div>

            <div>
              <span>Welcome Message</span>
              <strong>
                {settings.welcome_message ||
                  "Default"}
              </strong>
            </div>

          </div>

        </div>
      )}

    </div>
  );
}

export default InstallWidget;