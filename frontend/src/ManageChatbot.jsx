import { useEffect, useState, useRef } from "react";
import { useNavigate, useParams } from "react-router-dom";

import {
  getChatbot,
  updateChatbot,
  getChatbotSettings,
  updateChatbotSettings,
  getChatbotDocuments,
  getDocuments,
  attachDocument,
  detachDocument,
  uploadDocument,
  getUploadStatus,
} from "./api";

const SUPPORTED_FORMATS =
  ".pdf,.doc,.docx,.ppt,.pptx,.xls,.xlsx,.txt,.md,.png,.jpg,.jpeg,.gif";


function ManageChatbot() {
  const { chatbotId } = useParams();
  const navigate = useNavigate();

  const [chatbot, setChatbot] = useState(null);

  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [status, setStatus] = useState("active");

  const [settings, setSettings] = useState({
    primary_color: "#6d28d9",
    secondary_color: "#8b5cf6",
    logo_url: "",
    avatar_url: "",
    welcome_message: "Hi! How can I help you today?",
    placeholder: "Ask me anything...",
    position: "bottom-right",
    theme: "light",
    border_radius: "12px",
    widget_width: "380px",
    widget_height: "600px",
  });

  const [activeTab, setActiveTab] = useState("general");

  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  // Knowledge Base state
  const [chatbotDocuments, setChatbotDocuments] = useState([]);
  const [allDocuments, setAllDocuments] = useState([]);
  const [showAttachModal, setShowAttachModal] = useState(false);
  const [loadingDocuments, setLoadingDocuments] = useState(false);
  const [attachError, setAttachError] = useState("");

  // Upload new document state
  const [showUploadSection, setShowUploadSection] = useState(false);
  const [selectedFile, setSelectedFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState("");
  const [uploadStatus, setUploadStatus] = useState("");
  const [currentUpload, setCurrentUpload] = useState(null);
  const uploadIntervalRef = useRef(null);


  /* =====================================================
     LOAD CHATBOT
  ===================================================== */

  useEffect(() => {
    loadChatbot();
  }, [chatbotId]);


  async function loadChatbot() {
    try {
      setLoading(true);
      setError("");

      const chatbotData = await getChatbot(chatbotId);

      setChatbot(chatbotData);

      setName(chatbotData.name || "");
      setDescription(chatbotData.description || "");
      setStatus(chatbotData.status || "active");


      try {
        const settingsData =
          await getChatbotSettings(chatbotId);

        setSettings((previous) => ({
          ...previous,
          ...settingsData,
        }));
      } catch (settingsError) {
        console.warn(
          "Could not load chatbot settings:",
          settingsError
        );
      }

    } catch (err) {
      console.error(err);

      setError(
        err.message ||
          "Unable to load chatbot."
      );

    } finally {
      setLoading(false);
    }
  }


  /* =====================================================
     SAVE GENERAL CHATBOT INFORMATION
  ===================================================== */

  async function handleSaveGeneral(event) {
    event.preventDefault();

    try {
      setSaving(true);
      setMessage("");
      setError("");

      const updated = await updateChatbot(
        chatbotId,
        name,
        description,
        status
      );

      setChatbot(updated);

      setMessage("Chatbot details saved successfully.");

    } catch (err) {
      console.error(err);

      setError(
        err.message ||
          "Failed to save chatbot."
      );

    } finally {
      setSaving(false);
    }
  }


  /* =====================================================
     SETTINGS INPUT
  ===================================================== */

  function handleSettingChange(field, value) {
    setSettings((previous) => ({
      ...previous,
      [field]: value,
    }));
  }


  /* =====================================================
     SAVE APPEARANCE
  ===================================================== */

  async function handleSaveAppearance(event) {
    event.preventDefault();

    try {
      setSaving(true);
      setMessage("");
      setError("");

      await updateChatbotSettings(
        chatbotId,
        settings
      );

      setMessage(
        "Chatbot appearance saved successfully."
      );

    } catch (err) {
      console.error(err);

      setError(
        err.message ||
          "Failed to save appearance."
      );

    } finally {
      setSaving(false);
    }
  }


  /* =====================================================
     KNOWLEDGE BASE FUNCTIONS
  ===================================================== */

  async function loadChatbotDocuments() {
    try {
      setLoadingDocuments(true);
      setAttachError("");

      const [chatbotDocs, allDocs] = await Promise.all([
        getChatbotDocuments(chatbotId),
        getDocuments(),
      ]);

      setChatbotDocuments(Array.isArray(chatbotDocs) ? chatbotDocs : []);
      setAllDocuments(Array.isArray(allDocs) ? allDocs : []);
    } catch (err) {
      console.error(err);
      setAttachError(err?.message || "Unable to load documents.");
    } finally {
      setLoadingDocuments(false);
    }
  }

  async function handleAttachDocument(documentId) {
    try {
      setAttachError("");
      await attachDocument(chatbotId, documentId);
      setMessage("Document attached successfully.");
      await loadChatbotDocuments();
      setShowAttachModal(false);
    } catch (err) {
      console.error(err);
      setAttachError(err?.message || "Unable to attach document.");
    }
  }

  async function handleDetachDocument(documentId) {
    const confirmed = window.confirm(
      "Are you sure you want to remove this document from the chatbot?"
    );
    if (!confirmed) return;

    try {
      setAttachError("");
      await detachDocument(chatbotId, documentId);
      setMessage("Document removed successfully.");
      await loadChatbotDocuments();
    } catch (err) {
      console.error(err);
      setAttachError(err?.message || "Unable to remove document.");
    }
  }

  // Load documents when knowledge tab is activated
  useEffect(() => {
    if (activeTab === "knowledge" && chatbotId) {
      loadChatbotDocuments();
    }
  }, [activeTab, chatbotId]);


  /* =====================================================
     UPLOAD NEW DOCUMENT FUNCTIONS
  ===================================================== */

  function handleFileChange(event) {
    const file = event.target.files?.[0];
    if (file) {
      setSelectedFile(file);
      setUploadError("");
    }
  }

  function handleDrop(event) {
    event.preventDefault();
    const file = event.dataTransfer.files?.[0];
    if (file) {
      setSelectedFile(file);
      setUploadError("");
    }
  }

  function handleDragOver(event) {
    event.preventDefault();
  }

  // Cleanup polling interval on unmount
  useEffect(() => {
    return () => {
      if (uploadIntervalRef.current) {
        clearInterval(uploadIntervalRef.current);
        uploadIntervalRef.current = null;
      }
    };
  }, []);

  async function pollUploadStatus(documentId) {
    const intervalMs = 2000; // Poll every 2 seconds
    const maxTimeMs = 5 * 60 * 1000; // 5 minutes max
    let startTime = Date.now();

    // Clear any existing interval
    if (uploadIntervalRef.current) {
      clearInterval(uploadIntervalRef.current);
    }

    return new Promise((resolve, reject) => {
      const tick = async () => {
        try {
          const elapsed = Date.now() - startTime;

          if (elapsed >= maxTimeMs) {
            clearInterval(uploadIntervalRef.current);
            uploadIntervalRef.current = null;
            setUploadStatus("Processing is taking longer than expected. You can continue waiting or refresh the status.");
            reject(new Error("Processing timeout - you can continue waiting"));
            return;
          }

          const status = await getUploadStatus(documentId);
          console.log("Upload status response:", status);

          const statusValue = status.status || status.processing_status || "processing";
          const progressValue = status.progress !== undefined ? status.progress : null;

          setCurrentUpload({
            document_id: documentId,
            filename: status.filename || status.document_id,
            status: statusValue,
            progress: progressValue,
            error_message: status.error_message || "",
          });

          // Terminal states
          if (statusValue === "completed" || statusValue === "ready") {
            clearInterval(uploadIntervalRef.current);
            uploadIntervalRef.current = null;
            setCurrentUpload((prev) => ({
              ...prev,
              status: "completed",
              progress: 1,
            }));
            resolve(status);
            return;
          }

          if (statusValue === "failed" || statusValue === "error") {
            clearInterval(uploadIntervalRef.current);
            uploadIntervalRef.current = null;
            const errMsg = status.error_message || `Document processing ${statusValue}`;
            setUploadError(errMsg);
            reject(new Error(errMsg));
            return;
          }

          // Continue polling for processing state
        } catch (err) {
          clearInterval(uploadIntervalRef.current);
          uploadIntervalRef.current = null;
          const message = err?.message || "Unable to retrieve upload status.";
          setUploadError(message);
          reject(err);
        }
      };

      // Start polling
      uploadIntervalRef.current = setInterval(tick, intervalMs);
      tick(); // First check immediately
    });
  }

  async function handleUploadAndAttach() {
    if (!selectedFile) {
      setUploadError("Please choose a file to upload.");
      return;
    }

    setUploading(true);
    setUploadError("");
    setUploadStatus("Uploading document...");
    setCurrentUpload(null);

    try {
      // Upload the document
      const response = await uploadDocument(selectedFile);
      console.log("Upload response:", response);
      const documentId = response.document_id;

      setCurrentUpload({
        document_id: documentId,
        filename: response.filename,
        status: response.processing_status || "processing",
        progress: 0,
        error_message: "",
      });

      setUploadStatus("Processing document...");

      // Poll for processing completion
      await pollUploadStatus(documentId);

      setUploadStatus("✓ Document processed successfully");

      // Automatically attach to the current chatbot
      setUploadStatus("Attaching to chatbot...");
      try {
        await attachDocument(chatbotId, documentId);
        setMessage("Document uploaded and attached successfully.");
        await loadChatbotDocuments();
        setShowAttachModal(false);
        setShowUploadSection(false);
        setSelectedFile(null);
        setCurrentUpload(null);
        setUploadStatus("");
      } catch (attachErr) {
        console.error(attachErr);
        setUploadError(
          attachErr?.message ||
            "Document uploaded, but could not be attached to this chatbot."
        );
      }
    } catch (err) {
      console.error("Upload error:", err);
      setUploadError(err?.message || "Failed to upload document.");
    } finally {
      setUploading(false);
      // Always cleanup interval
      if (uploadIntervalRef.current) {
        clearInterval(uploadIntervalRef.current);
        uploadIntervalRef.current = null;
      }
    }
  }


  /* =====================================================
     LOADING
  ===================================================== */

  if (loading) {
    return (
      <div className="manage-state">

        <div className="loading-spinner"></div>

        <h3>Loading chatbot...</h3>

        <p>
          Please wait while KNOWA AI loads your chatbot.
        </p>

      </div>
    );
  }


  /* =====================================================
     ERROR
  ===================================================== */

  if (error && !chatbot) {
    return (
      <div className="manage-state error-state">

        <div className="state-icon">
          ⚠️
        </div>

        <h3>Unable to load chatbot</h3>

        <p>{error}</p>

        <button
          className="create-button"
          onClick={() => navigate("/chatbots")}
        >
          Back to Chatbots
        </button>

      </div>
    );
  }


  return (
    <div className="manage-page">


      {/* =================================================
          HEADER
      ================================================= */}

      <div className="manage-header">

        <div>

          <button
            className="back-button"
            onClick={() => navigate("/chatbots")}
          >
            ← Back to Chatbots
          </button>

          <h1>
            {chatbot?.name || "Manage Chatbot"}
          </h1>

          <p>
            Customize and manage your KNOWA AI chatbot
          </p>

        </div>

        <div className="manage-header-actions">

          <span
            className={
              status === "active"
                ? "status-badge status-active"
                : "status-badge status-inactive"
            }
          >
            <span></span>

            {status}
          </span>

        </div>

      </div>


      {/* =================================================
          SUCCESS / ERROR MESSAGE
      ================================================= */}

      {message && (
        <div className="success-message">
          ✓ {message}
        </div>
      )}

      {error && (
        <div className="manage-error">
          {error}
        </div>
      )}


      {/* =================================================
          TABS
      ================================================= */}

      <div className="manage-tabs">

        <button
          className={
            activeTab === "general"
              ? "manage-tab active"
              : "manage-tab"
          }
          onClick={() => {
            setActiveTab("general");
            setMessage("");
            setError("");
          }}
        >
          General
        </button>


        <button
          className={
            activeTab === "knowledge"
              ? "manage-tab active"
              : "manage-tab"
          }
          onClick={() => {
            setActiveTab("knowledge");
            setMessage("");
            setError("");
          }}
        >
          Knowledge Base
        </button>


        <button
          className={
            activeTab === "appearance"
              ? "manage-tab active"
              : "manage-tab"
          }
          onClick={() => {
            setActiveTab("appearance");
            setMessage("");
            setError("");
          }}
        >
          Appearance
        </button>


        <button
          className={
            activeTab === "widget"
              ? "manage-tab active"
              : "manage-tab"
          }
          onClick={() => {
            setActiveTab("widget");
            setMessage("");
            setError("");
          }}
        >
          Widget
        </button>


        <button
          className={
            activeTab === "embed"
              ? "manage-tab active"
              : "manage-tab"
          }
          onClick={() => {
            setActiveTab("embed");
            setMessage("");
            setError("");
          }}
        >
          Install
        </button>

      </div>


      {/* =================================================
          GENERAL TAB
      ================================================= */}

      {activeTab === "general" && (

        <form
          className="manage-card"
          onSubmit={handleSaveGeneral}
        >

          <div className="manage-card-header">

            <div>
              <h2>General Information</h2>

              <p>
                Manage your chatbot name,
                description and status.
              </p>
            </div>

          </div>


          <div className="form-grid">


            <div className="form-group">

              <label>
                Chatbot Name
              </label>

              <input
                type="text"
                value={name}
                onChange={(event) =>
                  setName(event.target.value)
                }
                placeholder="Enter chatbot name"
                required
              />

            </div>


            <div className="form-group">

              <label>
                Status
              </label>

              <select
                value={status}
                onChange={(event) =>
                  setStatus(event.target.value)
                }
              >
                <option value="active">
                  Active
                </option>

                <option value="inactive">
                  Inactive
                </option>

              </select>

            </div>


            <div className="form-group full-width">

              <label>
                Description
              </label>

              <textarea
                value={description}
                onChange={(event) =>
                  setDescription(event.target.value)
                }
                placeholder="Describe what this chatbot is used for..."
                rows="5"
              />

            </div>


            <div className="form-group full-width">

              <label>
                Embed Token
              </label>

              <div className="token-input">

                <input
                  value={
                    chatbot?.embed_token || ""
                  }
                  readOnly
                />

                <button
                  type="button"
                  className="copy-button"
                  onClick={() => {
                    navigator.clipboard.writeText(
                      chatbot?.embed_token || ""
                    );

                    setMessage(
                      "Embed token copied."
                    );
                  }}
                >
                  Copy
                </button>

              </div>

              <small>
                This token identifies your chatbot
                when using the KNOWA AI widget.
              </small>

            </div>

          </div>


          <div className="form-actions">

            <button
              type="submit"
              className="create-button"
              disabled={saving}
            >
              {saving
                ? "Saving..."
                : "Save Changes"}
            </button>

          </div>

        </form>
      )}


      {/* =================================================
          KNOWLEDGE BASE TAB
      ================================================= */}

      {activeTab === "knowledge" && (
        <div className="manage-card">
          <div className="manage-card-header">
            <div>
              <h2>Knowledge Base</h2>
              <p>Documents connected to this chatbot</p>
            </div>
            <button
              className="create-button"
              onClick={() => setShowAttachModal(true)}
            >
              + Add Document
            </button>
          </div>

          {attachError && (
            <div className="manage-error">
              {attachError}
            </div>
          )}

          {loadingDocuments ? (
            <div className="manage-state">
              <div className="loading-spinner"></div>
              <h3>Loading documents...</h3>
            </div>
          ) : chatbotDocuments.length === 0 ? (
            <div className="knowledge-empty-state">
              <div className="state-icon">📚</div>
              <h2>No documents attached</h2>
              <p>Attach documents from your knowledge base to give this chatbot knowledge.</p>
              <button
                className="create-button"
                onClick={() => setShowAttachModal(true)}
              >
                + Add Document
              </button>
            </div>
          ) : (
            <div className="knowledge-documents-grid">
              {chatbotDocuments.map((doc) => (
                <div
                  className="knowledge-document-card"
                  key={doc.id}
                >
                  <div className="knowledge-document-icon">📄</div>
                  <div className="knowledge-document-info">
                    <div className="knowledge-document-name">
                      {doc.filename}
                    </div>
                    <div className="knowledge-document-meta">
                      <span className="knowledge-document-status">
                        ✓ Attached
                      </span>
                      <span>
                        {new Date(doc.created_at).toLocaleDateString()}
                      </span>
                    </div>
                  </div>
                  <button
                    className="knowledge-remove-button"
                    onClick={() => handleDetachDocument(doc.document_id)}
                  >
                    Remove
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>
      )}


      {/* =================================================
          APPEARANCE TAB
      ================================================= */}

      {activeTab === "appearance" && (

        <form
          className="manage-card"
          onSubmit={handleSaveAppearance}
        >

          <div className="manage-card-header">

            <div>
              <h2>Appearance</h2>

              <p>
                Customize the look and feel
                of your KNOWA AI chatbot.
              </p>
            </div>

          </div>


          <div className="form-grid">


            <div className="form-group">

              <label>
                Primary Color
              </label>

              <div className="color-input">

                <input
                  type="color"
                  value={
                    settings.primary_color
                  }
                  onChange={(event) =>
                    handleSettingChange(
                      "primary_color",
                      event.target.value
                    )
                  }
                />

                <input
                  type="text"
                  value={
                    settings.primary_color
                  }
                  onChange={(event) =>
                    handleSettingChange(
                      "primary_color",
                      event.target.value
                    )
                  }
                />

              </div>

            </div>


            <div className="form-group">

              <label>
                Secondary Color
              </label>

              <div className="color-input">

                <input
                  type="color"
                  value={
                    settings.secondary_color
                  }
                  onChange={(event) =>
                    handleSettingChange(
                      "secondary_color",
                      event.target.value
                    )
                  }
                />

                <input
                  type="text"
                  value={
                    settings.secondary_color
                  }
                  onChange={(event) =>
                    handleSettingChange(
                      "secondary_color",
                      event.target.value
                    )
                  }
                />

              </div>

            </div>


            <div className="form-group">

              <label>
                Logo URL
              </label>

              <input
                type="text"
                value={
                  settings.logo_url
                }
                onChange={(event) =>
                  handleSettingChange(
                    "logo_url",
                    event.target.value
                  )
                }
                placeholder="https://example.com/logo.png"
              />

            </div>


            <div className="form-group">

              <label>
                Avatar URL
              </label>

              <input
                type="text"
                value={
                  settings.avatar_url
                }
                onChange={(event) =>
                  handleSettingChange(
                    "avatar_url",
                    event.target.value
                  )
                }
                placeholder="https://example.com/avatar.png"
              />

            </div>


            <div className="form-group full-width">

              <label>
                Welcome Message
              </label>

              <textarea
                rows="3"
                value={
                  settings.welcome_message
                }
                onChange={(event) =>
                  handleSettingChange(
                    "welcome_message",
                    event.target.value
                  )
                }
                placeholder="Hi! How can I help you?"
              />

            </div>


            <div className="form-group full-width">

              <label>
                Input Placeholder
              </label>

              <input
                type="text"
                value={
                  settings.placeholder
                }
                onChange={(event) =>
                  handleSettingChange(
                    "placeholder",
                    event.target.value
                  )
                }
                placeholder="Ask me anything..."
              />

            </div>

          </div>


          <div className="form-actions">

            <button
              type="submit"
              className="create-button"
              disabled={saving}
            >
              {saving
                ? "Saving..."
                : "Save Appearance"}
            </button>

          </div>

        </form>
      )}


      {/* =================================================
          WIDGET TAB
      ================================================= */}

      {activeTab === "widget" && (

        <form
          className="manage-card"
          onSubmit={handleSaveAppearance}
        >

          <div className="manage-card-header">

            <div>
              <h2>Widget Settings</h2>

              <p>
                Control how the chatbot appears
                on your website.
              </p>
            </div>

          </div>


          <div className="form-grid">


            <div className="form-group">

              <label>
                Theme
              </label>

              <select
                value={settings.theme}
                onChange={(event) =>
                  handleSettingChange(
                    "theme",
                    event.target.value
                  )
                }
              >
                <option value="light">
                  Light
                </option>

                <option value="dark">
                  Dark
                </option>

                <option value="auto">
                  Auto
                </option>

              </select>

            </div>


            <div className="form-group">

              <label>
                Position
              </label>

              <select
                value={settings.position}
                onChange={(event) =>
                  handleSettingChange(
                    "position",
                    event.target.value
                  )
                }
              >

                <option value="bottom-right">
                  Bottom Right
                </option>

                <option value="bottom-left">
                  Bottom Left
                </option>

                <option value="top-right">
                  Top Right
                </option>

                <option value="top-left">
                  Top Left
                </option>

              </select>

            </div>


            <div className="form-group">

              <label>
                Border Radius
              </label>

              <input
                type="text"
                value={
                  settings.border_radius
                }
                onChange={(event) =>
                  handleSettingChange(
                    "border_radius",
                    event.target.value
                  )
                }
                placeholder="12px"
              />

            </div>


            <div className="form-group">

              <label>
                Widget Width
              </label>

              <input
                type="text"
                value={
                  settings.widget_width
                }
                onChange={(event) =>
                  handleSettingChange(
                    "widget_width",
                    event.target.value
                  )
                }
                placeholder="380px"
              />

            </div>


            <div className="form-group">

              <label>
                Widget Height
              </label>

              <input
                type="text"
                value={
                  settings.widget_height
                }
                onChange={(event) =>
                  handleSettingChange(
                    "widget_height",
                    event.target.value
                  )
                }
                placeholder="600px"
              />

            </div>

          </div>


          <div className="widget-preview">

            <div className="preview-label">
              Live Preview
            </div>

            <div
              className="preview-chat"
              style={{
                borderRadius:
                  settings.border_radius,
              }}
            >

              <div
                className="preview-header"
                style={{
                  background:
                    settings.primary_color,
                }}
              >

                {/* <div className="preview-avatar">

                  {settings.avatar_url ? (
                    <img
                      src={
                        settings.avatar_url
                      }
                      alt="Bot"
                    />
                  ) : (
                    "S"
                  )}

                </div> */}
                <div className="preview-avatar">

                  {settings.logo_url || settings.avatar_url ? (
                   <img
                    src={
                      settings.logo_url ||
                      settings.avatar_url
                    }
                    alt="Bot"
                  />
                ) : (
                  "S"
                )}

                </div>

                <div>
                  <strong>
                    {chatbot?.name ||
                      "KNOWA AI"}
                  </strong>

                  <small>
                    Online
                  </small>
                </div>

              </div>


              <div className="preview-body">

                <div className="preview-message">
                  {
                    settings.welcome_message
                  }
                </div>

              </div>


              <div className="preview-input">
                {
                  settings.placeholder
                }
              </div>

            </div>

          </div>


          <div className="form-actions">

            <button
              type="submit"
              className="create-button"
              disabled={saving}
            >
              {saving
                ? "Saving..."
                : "Save Widget Settings"}
            </button>

          </div>

        </form>
      )}


      {/* =================================================
          INSTALL TAB
      ================================================= */}

      {activeTab === "embed" && (

        <div className="manage-card">

          <div className="manage-card-header">

            <div>
              <h2>
                Install KNOWA AI Widget
              </h2>

              <p>
                Add this chatbot to any website
                using one JavaScript snippet.
              </p>
            </div>

          </div>


          <div className="install-section">

            <div className="install-step">

              <div className="step-number">
                1
              </div>

              <div>
                <h3>
                  Copy the script
                </h3>

                <p>
                  Add the following script before
                  the closing
                  <code>&lt;/body&gt;</code> tag.
                </p>
              </div>

            </div>


            <div className="code-box">

              <code>
{`<script
  src="http://localhost:8000/api/v1/widget/${chatbot?.embed_token}.js"
  async>
</script>`}
              </code>

              <button
                className="copy-code-button"
                onClick={() => {

                  const script =
`<script
  src="http://localhost:8000/api/v1/widget/${chatbot?.embed_token}.js"
  async>
</script>`;

                  navigator.clipboard.writeText(
                    script
                  );

                  setMessage(
                    "Widget script copied."
                  );

                }}
              >
                Copy Script
              </button>

            </div>


            <div className="install-step">

              <div className="step-number">
                2
              </div>

              <div>

                <h3>
                  Add it to your website
                </h3>

                <p>
                  Paste the script into your
                  website's HTML.
                </p>

              </div>

            </div>


            <div className="install-note">

              <strong>
                💡 KNOWA AI
              </strong>

              <span>
                Your chatbot will automatically
                appear on the website after the
                script loads.
              </span>

            </div>

          </div>

        </div>
      )}

      {/* Attach Document Modal */}
      {showAttachModal && (
        <div className="modal-overlay">
          <div className="upload-modal attach-modal">
            <div className="modal-header">
              <h2>Add Document to Chatbot</h2>
              <button
                className="close-button"
                onClick={() => {
                  setShowAttachModal(false);
                  setAttachError("");
                  setShowUploadSection(false);
                  setSelectedFile(null);
                  setUploadError("");
                  setCurrentUpload(null);
                  setUploadStatus("");
                }}
              >
                ✕
              </button>
            </div>

            <div className="modal-body">
              {attachError && (
                <div className="manage-error">
                  {attachError}
                </div>
              )}

              {!showUploadSection ? (
                <>
                  <h3 className="attach-section-title">Existing Documents</h3>

                  {allDocuments.length === 0 ? (
                    <div className="knowledge-empty-state">
                      <div className="state-icon">📚</div>
                      <h2>No documents available</h2>
                      <p>Upload documents to your knowledge base first.</p>
                      <button
                        className="outline-button"
                        onClick={() => {
                          setShowAttachModal(false);
                          navigate("/knowledge-base");
                        }}
                      >
                        Go to Knowledge Base
                      </button>
                    </div>
                  ) : (
                    <div className="document-list">
                      {allDocuments.map((doc) => {
                        const isAttached = chatbotDocuments.some(
                          (attached) => attached.document_id === doc.document_id
                        );

                        return (
                          <div
                            className="document-card"
                            key={doc.document_id}
                          >
                            <div className="document-icon">📄</div>
                            <div className="document-info">
                              <div className="document-name">
                                {doc.filename}
                              </div>
                              <div className="document-meta">
                                <span>
                                  {new Date(doc.created_at).toLocaleDateString()}
                                </span>
                                <span>•</span>
                                <span>
                                  {doc.status === "completed" || doc.status === "ready"
                                    ? "Ready"
                                    : doc.status}
                                </span>
                              </div>
                            </div>
                            {isAttached ? (
                              <button
                                className="outline-button"
                                disabled
                              >
                                Already Attached
                              </button>
                            ) : (
                              <button
                                className="create-button"
                                onClick={() =>
                                  handleAttachDocument(doc.document_id)
                                }
                              >
                                Attach
                              </button>
                            )}
                          </div>
                        );
                      })}
                    </div>
                  )}

                  <div className="attach-divider">
                    <span>OR</span>
                  </div>

                  <button
                    className="create-button upload-new-button"
                    onClick={() => setShowUploadSection(true)}
                  >
                    + Upload New Document
                  </button>
                </>
              ) : (
                <>
                  <h3 className="attach-section-title">Upload New Document</h3>

                  {uploadError && (
                    <div className="manage-error">
                      {uploadError}
                    </div>
                  )}

                  {uploadStatus && (
                    <div className="upload-status-message">
                      {uploadStatus}
                    </div>
                  )}

                  <div
                    className="upload-dropzone"
                    onDrop={handleDrop}
                    onDragOver={handleDragOver}
                    onClick={() => document.getElementById("chatbot-file-input")?.click()}
                  >
                    <p>
                      {selectedFile
                        ? selectedFile.name
                        : "Drag files here or click to choose a file."}
                    </p>
                    <input
                      id="chatbot-file-input"
                      type="file"
                      accept={SUPPORTED_FORMATS}
                      onChange={handleFileChange}
                      style={{ display: "none" }}
                    />
                  </div>

                  <div className="upload-hint">
                    Supported formats: PDF, DOCX, PPTX, XLSX, TXT, MD, PNG, JPG, JPEG, GIF
                  </div>

                  {currentUpload && (
                    <div className="upload-progress">
                      <div className="upload-progress-title">
                        Uploading {currentUpload.filename}
                      </div>
                      <div className="upload-progress-row">
                        <span>Status:</span>
                        <strong>{currentUpload.status}</strong>
                      </div>
                      <div className="upload-progress-row">
                        <span>Progress:</span>
                        <strong>{Math.round((currentUpload.progress ?? 0) * 100)}%</strong>
                      </div>
                      {currentUpload.error_message && (
                        <div className="manage-error">
                          {currentUpload.error_message}
                        </div>
                      )}
                    </div>
                  )}

                  <div className="modal-footer">
                    <button
                      className="outline-button"
                      onClick={() => {
                        setShowUploadSection(false);
                        setSelectedFile(null);
                        setUploadError("");
                        setCurrentUpload(null);
                        setUploadStatus("");
                      }}
                      disabled={uploading}
                    >
                      Back
                    </button>
                    <button
                      className="create-button"
                      onClick={handleUploadAndAttach}
                      disabled={uploading || !selectedFile}
                    >
                      {uploading ? "Uploading..." : "Upload & Attach"}
                    </button>
                  </div>
                </>
              )}
            </div>

            {!showUploadSection && (
              <div className="modal-footer">
                <button
                  className="outline-button"
                  onClick={() => {
                    setShowAttachModal(false);
                    setAttachError("");
                  }}
                >
                  Cancel
                </button>
              </div>
            )}
          </div>
        </div>
      )}

    </div>
  );
}


export default ManageChatbot;