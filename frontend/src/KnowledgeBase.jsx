import { useCallback, useEffect, useState, useRef } from "react";
import {
  getDocuments,
  uploadDocument,
  getUploadStatus,
  deleteDocument,
} from "./api";

const SUPPORTED_FORMATS =
  ".pdf,.doc,.docx,.ppt,.pptx,.xls,.xlsx,.txt,.md,.png,.jpg,.jpeg,.gif";

function KnowledgeBase() {
  const [documents, setDocuments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const [showUploadModal, setShowUploadModal] = useState(false);
  const [selectedFile, setSelectedFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState("");
  const [statusMessage, setStatusMessage] = useState("");
  const [currentUpload, setCurrentUpload] = useState(null);
  const uploadIntervalRef = useRef(null);

  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [documentToDelete, setDocumentToDelete] = useState(null);

  const loadDocuments = useCallback(async () => {
    setLoading(true);
    setError("");

    try {
      const docs = await getDocuments();
      setDocuments(Array.isArray(docs) ? docs : []);
    } catch (err) {
      console.error(err);
      setError(err?.message || "Unable to load documents.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadDocuments();
  }, [loadDocuments]);

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

      await pollUploadStatus(documentId);

      setStatusMessage("Document uploaded and processed successfully.");
      await loadDocuments();
      setCurrentUpload(null);
      setShowUploadModal(false);
      setSelectedFile(null);
    } catch (err) {
      console.error("Upload error:", err);
      setUploadError(err?.message || "Unable to upload this document.");
    } finally {
      setUploading(false);
      // Always cleanup interval
      if (uploadIntervalRef.current) {
        clearInterval(uploadIntervalRef.current);
        uploadIntervalRef.current = null;
      }
    }
  }

  function handleDeleteClick(document) {
    setDocumentToDelete(document);
    setShowDeleteModal(true);
  }

  async function handleDeleteConfirm() {
    if (!documentToDelete) return;

    try {
      await deleteDocument(documentToDelete.document_id);
      setStatusMessage("Document deleted successfully.");
      await loadDocuments();
      setShowDeleteModal(false);
      setDocumentToDelete(null);
    } catch (err) {
      console.error(err);
      setError(err?.message || "Unable to delete document.");
    }
  }

  function handleDeleteCancel() {
    setShowDeleteModal(false);
    setDocumentToDelete(null);
  }

  function formatDate(dateString) {
    if (!dateString) return "Unknown";
    return new Date(dateString).toLocaleDateString();
  }

  function getStatusBadge(status) {
    switch (status) {
      case "completed":
      case "ready":
        return <span className="status-badge status-success">Ready</span>;
      case "processing":
        return <span className="status-badge status-processing">Processing</span>;
      case "failed":
        return <span className="status-badge status-error">Failed</span>;
      default:
        return <span className="status-badge">{status}</span>;
    }
  }

  if (loading) {
    return (
      <div className="knowledge-base-page">
        <div className="page-loading">
          <div className="loading-spinner"></div>
          <h2>Loading documents...</h2>
        </div>
      </div>
    );
  }

  return (
    <div className="knowledge-base-page">
      <header className="topbar">
        <div>
          <h1>Knowledge Base</h1>
          <p>Manage your uploaded documents and chatbot knowledge</p>
        </div>
        <button
          className="create-button"
          onClick={() => setShowUploadModal(true)}
        >
          + Upload Document
        </button>
      </header>

      {error && (
        <div className="error-message">
          {error}
        </div>
      )}

      {statusMessage && (
        <div className="success-message">
          ✓ {statusMessage}
        </div>
      )}

      {documents.length === 0 ? (
        <div className="empty-documents">
          <div className="empty-icon">📚</div>
          <h2>No documents yet</h2>
          <p>Upload your first document to build your KNOWA AI knowledge base.</p>
          <button
            className="create-button"
            onClick={() => setShowUploadModal(true)}
          >
            + Upload Document
          </button>
        </div>
      ) : (
        <div className="document-list">
          {documents.map((doc) => (
            <div className="document-card" key={doc.document_id}>
              <div className="document-icon">📄</div>
              <div className="document-info">
                <div className="document-name">{doc.filename}</div>
                <div className="document-meta">
                  <span>ID: {doc.document_id.slice(0, 8)}...</span>
                  <span>•</span>
                  <span>{formatDate(doc.created_at)}</span>
                  <span>•</span>
                  {getStatusBadge(doc.status)}
                </div>
                <div className="document-details">
                  <span>Chunks: {doc.chunks_created || 0}</span>
                  {doc.tables_extracted > 0 && <span>• Tables: {doc.tables_extracted}</span>}
                  {doc.images_extracted > 0 && <span>• Images: {doc.images_extracted}</span>}
                </div>
                {doc.error_message && (
                  <div className="document-error">{doc.error_message}</div>
                )}
              </div>
              <div className="document-actions">
                <button
                  className="delete-button"
                  onClick={() => handleDeleteClick(doc)}
                >
                  Delete
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Upload Modal */}
      {showUploadModal && (
        <div className="modal-overlay">
          <div className="upload-modal">
            <div className="modal-header">
              <h2>Upload Document</h2>
              <button
                className="close-button"
                onClick={() => {
                  setShowUploadModal(false);
                  setSelectedFile(null);
                  setUploadError("");
                  setStatusMessage("");
                  setCurrentUpload(null);
                }}
              >
                ✕
              </button>
            </div>

            <div className="modal-body">
              <div
                className="upload-dropzone"
                onDrop={handleDrop}
                onDragOver={handleDragOver}
                onClick={() => document.getElementById("file-input")?.click()}
              >
                <p>
                  {selectedFile
                    ? selectedFile.name
                    : "Drag files here or click to choose a file."}
                </p>
                <input
                  id="file-input"
                  type="file"
                  accept={SUPPORTED_FORMATS}
                  onChange={handleFileChange}
                  style={{ display: "none" }}
                />
              </div>

              <div className="upload-hint">
                Supported formats: PDF, DOCX, PPTX, XLSX, TXT, MD, PNG, JPG, JPEG, GIF
              </div>

              {uploadError && (
                <div className="error-message">
                  {uploadError}
                </div>
              )}

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
                    <div className="error-message">
                      {currentUpload.error_message}
                    </div>
                  )}
                </div>
              )}
            </div>

            <div className="modal-footer">
              <button
                className="outline-button"
                onClick={() => {
                  setShowUploadModal(false);
                  setSelectedFile(null);
                  setUploadError("");
                  setStatusMessage("");
                  setCurrentUpload(null);
                }}
                disabled={uploading}
              >
                Cancel
              </button>
              <button
                className="create-button"
                onClick={handleUpload}
                disabled={uploading || !selectedFile}
              >
                {uploading ? "Uploading..." : "Upload"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Delete Confirmation Modal */}
      {showDeleteModal && documentToDelete && (
        <div className="modal-overlay">
          <div className="upload-modal">
            <div className="modal-header">
              <h2>Delete Document</h2>
              <button
                className="close-button"
                onClick={handleDeleteCancel}
              >
                ✕
              </button>
            </div>

            <div className="modal-body">
              <p>Are you sure you want to delete "{documentToDelete.filename}"?</p>
              <p className="warning-text">This action cannot be undone.</p>
            </div>

            <div className="modal-footer">
              <button
                className="outline-button"
                onClick={handleDeleteCancel}
              >
                Cancel
              </button>
              <button
                className="delete-button"
                onClick={handleDeleteConfirm}
              >
                Delete
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default KnowledgeBase;
