import { useCallback, useEffect, useState, useRef } from "react";
import { useNavigate, useParams } from "react-router-dom";
import {
  getChatbot,
  uploadDocument,
  getUploadStatus,
  getChatbotDocuments,
  attachDocument,
  detachDocument,
} from "./api";

const SUPPORTED_FORMATS =
  ".pdf,.doc,.docx,.ppt,.pptx,.xls,.xlsx,.txt,.md,.png,.jpg,.jpeg,.gif";

function KnowledgeBase() {
  const { chatbotId } = useParams();
  const navigate = useNavigate();

  const [chatbot, setChatbot] = useState(null);
  const [documents, setDocuments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const [selectedFile, setSelectedFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState("");
  const [attachError, setAttachError] = useState("");
  const [statusMessage, setStatusMessage] = useState("");
  const [currentUpload, setCurrentUpload] = useState(null);
  const uploadIntervalRef = useRef(null);

  const loadData = useCallback(async () => {
    setLoading(true);
    setError("");
    setUploadError("");
    setAttachError("");
    setStatusMessage("");

    try {
      const [chatbotData, docsData] = await Promise.all([
        getChatbot(chatbotId),
        getChatbotDocuments(chatbotId),
      ]);

      setChatbot(chatbotData);
      setDocuments(Array.isArray(docsData) ? docsData : []);
    } catch (err) {
      console.error(err);
      setError(err?.message || "Unable to load documents.");
    } finally {
      setLoading(false);
    }
  }, [chatbotId]);

  useEffect(() => {
    if (!chatbotId) {
      setError("Chatbot ID is missing.");
      setLoading(false);
      return;
    }

    loadData();
  }, [chatbotId, loadData]);

  // Cleanup polling interval on unmount
  useEffect(() => {
    return () => {
      if (uploadIntervalRef.current) {
        clearInterval(uploadIntervalRef.current);
        uploadIntervalRef.current = null;
      }
    };
  }, []);

  function handleFileChange(event) {
    const file = event.target.files?.[0];
    if (file) {
      setSelectedFile(file);
      setUploadError("");
      setStatusMessage("");
    }
  }

  function handleDrop(event) {
    event.preventDefault();
    const file = event.dataTransfer.files?.[0];
    if (file) {
      setSelectedFile(file);
      setUploadError("");
      setStatusMessage("");
    }
  }

  function handleDragOver(event) {
    event.preventDefault();
  }

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
            setUploadError("Processing is taking longer than expected. You can continue waiting or refresh the status.");
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

  async function handleUpload() {
    if (!selectedFile) {
      setUploadError("Please choose a file to upload.");
      return;
    }

    setUploading(true);
    setUploadError("");
    setAttachError("");
    setStatusMessage("");
    setCurrentUpload(null);

    try {
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

      const status = await pollUploadStatus(documentId);

      try {
        await attachDocument(chatbotId, documentId);
        setStatusMessage(
          "Document processed and attached to this chatbot."
        );
        await loadData();
        setCurrentUpload(null);
      } catch (attachErr) {
        console.error(attachErr);
        setAttachError(
          attachErr?.message ||
            "Document uploaded but could not be attached to this chatbot."
        );
      }
    } catch (err) {
      console.error("Upload error:", err);
      setUploadError(err?.message || "Unable to upload this document.");
    } finally {
      setUploading(false);
      setSelectedFile(null);
      // Always cleanup interval
      if (uploadIntervalRef.current) {
        clearInterval(uploadIntervalRef.current);
        uploadIntervalRef.current = null;
      }
    }
  }

  async function handleRemove(documentId) {
    const confirmed = window.confirm(
      "Are you sure you want to remove this document from the chatbot?"
    );
    if (!confirmed) {
      return;
    }

    setError("");
    try {
      await detachDocument(chatbotId, documentId);
      await loadData();
    } catch (err) {
      console.error(err);
      setError(err?.message || "Unable to remove document.");
    }
  }

  if (loading) {
    return (
      <div className="knowledge-page">
        <div className="knowledge-loading">
          <div className="loading-spinner"></div>
          <h2>Loading knowledge base...</h2>
          <p>Fetching chatbot document state.</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="knowledge-page">
        <div className="knowledge-error">
          <div className="state-icon">⚠️</div>
          <h2>Unable to load documents.</h2>
          <p>{error}</p>
          <button
            className="create-button"
            onClick={() => loadData()}
          >
            Try Again
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="knowledge-page">
      <div className="knowledge-header">
        <div>
          <button
            className="back-button"
            onClick={() => navigate(-1)}
          >
            ← Back
          </button>

          <h1>Knowledge Base</h1>
          <p>
            Give {chatbot?.name || "this chatbot"} knowledge from uploaded documents.
          </p>
        </div>
      </div>

      <div className="knowledge-grid">
        <section className="knowledge-upload-card">
          <div className="knowledge-upload-top">
            <div className="knowledge-icon">📄</div>
            <div>
              <h2>Upload documents</h2>
              <p>
                Drag and drop files here, or choose documents to upload and attach to your chatbot.
              </p>
            </div>
          </div>

          <div
            className="knowledge-dropzone"
            onDrop={handleDrop}
            onDragOver={handleDragOver}
          >
            <p>
              {selectedFile
                ? selectedFile.name
                : "Drag files here or click to choose a file."}
            </p>
            <input
              id="knowledge-file-input"
              className="knowledge-file-input"
              type="file"
              accept={SUPPORTED_FORMATS}
              onChange={handleFileChange}
            />
          </div>

          <div className="knowledge-hint">
            Supported formats: PDF, DOCX, PPTX, XLSX, TXT, MD, PNG, JPG, JPEG, GIF.
          </div>

          <button
            className="create-button"
            onClick={handleUpload}
            disabled={uploading || !selectedFile}
          >
            {uploading ? "Uploading…" : "+ Upload Document"}
          </button>

          {uploadError && (
            <div className="knowledge-feedback knowledge-error-text">
              {uploadError}
            </div>
          )}

          {attachError && (
            <div className="knowledge-feedback knowledge-error-text">
              {attachError}
            </div>
          )}

          {statusMessage && (
            <div className="knowledge-feedback knowledge-success-text">
              {statusMessage}
            </div>
          )}

          {currentUpload && (
            <div className="knowledge-upload-status">
              <div className="knowledge-upload-status-title">
                Uploading {currentUpload.filename}
              </div>
              <div className="knowledge-upload-status-row">
                <span>Status</span>
                <strong>{currentUpload.status}</strong>
              </div>
              <div className="knowledge-upload-status-row">
                <span>Progress</span>
                <strong>{Math.round((currentUpload.progress ?? 0) * 100)}%</strong>
              </div>
              {currentUpload.error_message && (
                <div className="knowledge-feedback knowledge-error-text">
                  {currentUpload.error_message}
                </div>
              )}
            </div>
          )}
        </section>

        <section className="knowledge-document-list">
          <div className="knowledge-section-header">
            <div>
              <h2>Uploaded documents</h2>
              <p>
                These documents are attached to {chatbot?.name || "this chatbot"}.
              </p>
            </div>
          </div>

          {documents.length === 0 ? (
            <div className="knowledge-empty-state">
              <div className="state-icon">📚</div>
              <h2>No documents yet</h2>
              <p>Upload documents to give your KNOWA AI chatbot knowledge.</p>
              <button
                className="create-button"
                onClick={() => document.getElementById("knowledge-file-input")?.click()}
              >
                Upload Document
              </button>
            </div>
          ) : (
            <div className="knowledge-documents-grid">
              {documents.map((doc) => (
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
                        ✓ Processed
                      </span>
                      <span>
                        Attached {new Date(doc.created_at).toLocaleDateString()}
                      </span>
                    </div>
                  </div>
                  <button
                    className="knowledge-remove-button"
                    onClick={() => handleRemove(doc.document_id)}
                  >
                    Remove
                  </button>
                </div>
              ))}
            </div>
          )}
        </section>
      </div>
    </div>
  );
}

export default KnowledgeBase;
