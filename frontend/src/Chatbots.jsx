import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

import {
  getChatbots,
  createChatbot,
  deleteChatbot,
} from "./api";

function Chatbots() {
  const navigate = useNavigate();

  const [chatbots, setChatbots] = useState([]);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const [showCreateModal, setShowCreateModal] =
    useState(false);

  const [creating, setCreating] = useState(false);

  const [name, setName] = useState("");
  const [description, setDescription] =
    useState("");

  /* =========================================================
     LOAD CHATBOTS
  ========================================================= */

  async function loadChatbots() {
    try {
      setLoading(true);
      setError("");

      const data = await getChatbots();

      setChatbots(
        Array.isArray(data) ? data : []
      );
    } catch (err) {
      console.error(
        "Chatbot loading error:",
        err
      );

      setError(
        err.message ||
          "Unable to load chatbots."
      );
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadChatbots();
  }, []);

  /* =========================================================
     CREATE CHATBOT
  ========================================================= */

  async function handleCreateChatbot(e) {
    e.preventDefault();

    if (!name.trim()) {
      return;
    }

    try {
      setCreating(true);
      setError("");

      const newChatbot =
        await createChatbot(
          name.trim(),
          description.trim()
        );

      /*
       * Add the newly created chatbot
       * immediately to the list.
       */

      setChatbots((current) => [
        newChatbot,
        ...current,
      ]);

      /*
       * Clear form
       */

      setName("");
      setDescription("");

      /*
       * Close modal
       */

      setShowCreateModal(false);

    } catch (err) {
      console.error(
        "Create chatbot error:",
        err
      );

      setError(
        err.message ||
          "Unable to create chatbot."
      );
    } finally {
      setCreating(false);
    }
  }

  /* =========================================================
     DELETE CHATBOT
  ========================================================= */

  async function handleDeleteChatbot(
    chatbot
  ) {
    const confirmed = window.confirm(
      `Are you sure you want to delete "${chatbot.name}"?`
    );

    if (!confirmed) {
      return;
    }

    try {
      setError("");

      await deleteChatbot(chatbot.id);

      /*
       * Remove from UI after successful
       * backend deletion.
       */

      setChatbots((current) =>
        current.filter(
          (item) =>
            item.id !== chatbot.id
        )
      );

    } catch (err) {
      console.error(
        "Delete chatbot error:",
        err
      );

      setError(
        err.message ||
          "Unable to delete chatbot."
      );
    }
  }

  /* =========================================================
     OPEN MANAGE PAGE
  ========================================================= */

  function handleManage(chatbotId) {
    navigate(
      `/chatbots/${chatbotId}`
    );
  }

  /* =========================================================
     OPEN INSTALL WIDGET PAGE
  ========================================================= */

  function handleInstall(chatbotId) {
    navigate(
      `/chatbots/${chatbotId}/install`
    );
  }

  /* =========================================================
     FORMAT DATE
  ========================================================= */

  function formatDate(dateString) {
    if (!dateString) {
      return "—";
    }

    const date =
      new Date(dateString);

    if (Number.isNaN(date.getTime())) {
      return dateString;
    }

    return date.toLocaleDateString(
      "en-IN",
      {
        day: "numeric",
        month: "numeric",
        year: "numeric",
      }
    );
  }

  /* =========================================================
     LOADING STATE
  ========================================================= */

  if (loading) {
    return (
      <div className="chatbots-page">

        <div className="chatbots-page-header">

          <div>
            <h1>
              Chatbots
            </h1>

            <p>
              Create and manage your AI
              chatbots
            </p>
          </div>

        </div>

        <div className="chatbots-state">

          <div className="loading-spinner"></div>

          <h3>
            Loading chatbots...
          </h3>

          <p>
            Getting your chatbots from
            KNOWA AI.
          </p>

        </div>

      </div>
    );
  }

  /* =========================================================
     MAIN UI
  ========================================================= */

  return (
    <div className="chatbots-page">

      {/* =====================================================
          HEADER
      ===================================================== */}

      <div className="chatbots-page-header">

        <div>

          <h1>
            Chatbots
          </h1>

          <p>
            Create and manage your AI
            chatbots
          </p>

        </div>

        <button
          className="create-button"
          onClick={() =>
            setShowCreateModal(true)
          }
        >
          + Create Chatbot
        </button>

      </div>


      {/* =====================================================
          ERROR
      ===================================================== */}

      {error && (
        <div className="chatbots-error">

          <span>
            ⚠️
          </span>

          <p>
            {error}
          </p>

          <button
            onClick={loadChatbots}
          >
            Try Again
          </button>

        </div>
      )}


      {/* =====================================================
          EMPTY STATE
      ===================================================== */}

      {chatbots.length === 0 ? (

        <div className="chatbots-state">

          <div className="state-icon">
            🤖
          </div>

          <h3>
            No chatbots yet
          </h3>

          <p>
            Create your first KNOWA AI
            chatbot to get started.
          </p>

          <button
            className="create-button"
            onClick={() =>
              setShowCreateModal(true)
            }
          >
            + Create Chatbot
          </button>

        </div>

      ) : (

        /* ===================================================
           CHATBOT LIST
        =================================================== */

        <div className="chatbot-list">

          {chatbots.map((chatbot) => (

            <div
              className="chatbot-card"
              key={chatbot.id}
            >

              {/* =================================================
                  TOP
              ================================================= */}

              <div className="chatbot-card-top">

                <div className="chatbot-icon">
                  🤖
                </div>


                <div className="chatbot-main-info">

                  <h2>
                    {chatbot.name}
                  </h2>

                  <p>
                    {chatbot.description ||
                      "KNOWA AI chatbot"}
                  </p>

                </div>


                {/* STATUS */}

                <div
                  className={`status-badge ${
                    chatbot.status ===
                    "active"
                      ? "status-active"
                      : "status-inactive"
                  }`}
                >

                  <span></span>

                  {chatbot.status ||
                    "inactive"}

                </div>

              </div>


              {/* =================================================
                  DETAILS
              ================================================= */}

              <div className="chatbot-details">

                <div>

                  <span className="detail-label">
                    Created
                  </span>

                  <span className="detail-value">
                    {formatDate(
                      chatbot.created_at
                    )}
                  </span>

                </div>


                <div>

                  <span className="detail-label">
                    Embed Token
                  </span>

                  <span className="detail-value token-value">

                    {chatbot.embed_token
                      ? `${chatbot.embed_token.substring(
                          0,
                          8
                        )}...`
                      : "—"}

                  </span>

                </div>

              </div>


              {/* =================================================
                  ACTIONS
              ================================================= */}

              <div className="chatbot-card-actions">

                {/* MANAGE */}

                <button
                  className="outline-button"
                  onClick={() =>
                    handleManage(
                      chatbot.id
                    )
                  }
                >
                  Manage
                </button>


                {/* INSTALL WIDGET */}

                <button
                  className="create-button"
                  onClick={() =>
                    handleInstall(
                      chatbot.id
                    )
                  }
                >
                  Install Widget
                </button>


                {/* DELETE */}

                <button
                  className="delete-button"
                  onClick={() =>
                    handleDeleteChatbot(
                      chatbot
                    )
                  }
                >
                  Delete
                </button>

              </div>

            </div>

          ))}

        </div>
      )}


      {/* =====================================================
          CREATE CHATBOT MODAL
      ===================================================== */}

      {showCreateModal && (

        <div
          className="modal-overlay"
          onClick={() =>
            setShowCreateModal(false)
          }
        >

          <div
            className="create-modal"
            onClick={(e) =>
              e.stopPropagation()
            }
          >

            <div className="modal-header">

              <div>

                <h2>
                  Create Chatbot
                </h2>

                <p>
                  Create a new KNOWA AI
                  chatbot.
                </p>

              </div>

              <button
                className="modal-close"
                onClick={() =>
                  setShowCreateModal(false)
                }
              >
                ×
              </button>

            </div>


            {/* FORM */}

            <form
              onSubmit={
                handleCreateChatbot
              }
            >

              {/* NAME */}

              <div className="form-group">

                <label>
                  Chatbot Name
                </label>

                <input
                  type="text"
                  placeholder="Example: Customer Support"
                  value={name}
                  onChange={(e) =>
                    setName(
                      e.target.value
                    )
                  }
                  required
                />

              </div>


              {/* DESCRIPTION */}

              <div className="form-group">

                <label>
                  Description
                </label>

                <textarea
                  placeholder="Example: Chatbot for customer queries"
                  value={description}
                  onChange={(e) =>
                    setDescription(
                      e.target.value
                    )
                  }
                  rows="4"
                />

              </div>


              {/* BUTTONS */}

              <div className="modal-actions">

                <button
                  type="button"
                  className="outline-button"
                  onClick={() =>
                    setShowCreateModal(
                      false
                    )
                  }
                  disabled={creating}
                >
                  Cancel
                </button>

                <button
                  type="submit"
                  className="create-button"
                  disabled={creating}
                >
                  {creating
                    ? "Creating..."
                    : "Create Chatbot"}
                </button>

              </div>

            </form>

          </div>

        </div>

      )}

    </div>
  );
}

export default Chatbots;